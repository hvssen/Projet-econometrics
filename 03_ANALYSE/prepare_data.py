"""Construct observed local pizza competition from the unchanged public files."""
from pathlib import Path
import html
import json
import re
import hashlib
import zipfile
import urllib.request
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CENTER = (29.7604, -95.3698)
EARTH_KM = 6371.0088
ARCHIVE_URL = 'https://www.kaggle.com/api/v1/datasets/download/ahmedshahriarsakib/uber-eats-usa-restaurants-menus'


def distances(a, b):
    a, b = np.radians(np.asarray(a, float)), np.radians(np.asarray(b, float))
    delta = a[:, None, :] - b[None, :, :]
    h = np.sin(delta[:, :, 0] / 2) ** 2 + np.cos(a[:, None, 0]) * np.cos(b[None, :, 0]) * np.sin(delta[:, :, 1] / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def clean_text(value):
    return re.sub(r'\s+', ' ', html.unescape(str(value)).lower().replace('’', "'")).strip()


# Explicit name-based groups. This is not a legal franchise-status variable.
BRANDS = {
    'Papa Johns': r'^papa john', 'Pizza Hut': r'^pizza hut',
    'MOD Pizza': r'^mod pizza', 'Marcos': r'^marco.?s pizza',
    'Little Caesars': r'^little caesars', 'Cicis': r'^cicis',
    'Papa Murphys': r'^papa murphy', 'Jets': r'^jet.?s pizza',
    'Blaze': r'^blaze pizza', 'Grimaldis': r'^grimaldi',
    'Chuck E Cheese': r'^chuck e', 'Pasquallys': r'^pasqually',
    'Mellow Mushroom': r'^mellow mushroom', 'Pizza Patron': r'^pizza patr[oó]n',
    'Gattis': r'^(?:mr\.? )?gatti', 'DoubleDaves': r'^doubledave',
    'California Pizza Kitchen': r'^california pizza kitchen',
    'BJs': r'^bj.?s restaurant', 'Panera': r'^panera',
    '1000 Degrees': r'^1000 degrees', 'Pizza Inn': r'^pizza inn',
    'Hungry Howies': r'^hungry howie', 'Rosatis': r'^rosati',
    'Old Chicago': r'^old chicago', 'Buca Di Beppo': r'^buca di beppo',
    'Johnny Carinos': r'^johnny carino', 'Peperonis': r'^pepperoni.?s',
    'Russos': r'^russo', 'Pinks': r'^pink.?s pizza',
    'Village Pizza': r'^village pizza', 'Center Court': r'^center court pizza',
    'Zalat': r'^zalat', 'Crust Pizza': r'^crust pizza',
    '7 Eleven': r'^7-eleven', 'Stripes': r'^stripes',
}


def brand_name(name):
    name = clean_text(name)
    for label, pattern in BRANDS.items():
        if re.search(pattern, name):
            return label
    return 'Other or unclassified'


def main():
    for folder in ['data', 'resultats', 'figures']:
        (ROOT / folder).mkdir(exist_ok=True)
    restaurants_path = ROOT / 'data/restaurants_US_raw.csv'
    menu_path = ROOT / 'data/menus_region_raw.csv'
    if not restaurants_path.exists() or not menu_path.exists():
        archive = ROOT / 'data/source_archive.zip'
        if not archive.exists():
            urllib.request.urlretrieve(ARCHIVE_URL, archive)
        with zipfile.ZipFile(archive) as z:
            if not restaurants_path.exists():
                restaurants_path.write_bytes(z.read('restaurants.csv'))
            if not menu_path.exists():
                all_r = pd.read_csv(restaurants_path)
                valid = all_r.dropna(subset=['lat', 'lng'])
                radius = distances(valid[['lat','lng']], [CENTER])[:, 0]
                ids = set(valid.loc[radius <= 55, 'id'])
                pieces = []
                for chunk in pd.read_csv(z.open('restaurant-menus.csv'), chunksize=200000):
                    pieces.append(chunk.loc[chunk.restaurant_id.isin(ids)])
                regional_menus = pd.concat(pieces, ignore_index=True)
                supplier_ids = set(regional_menus.loc[
                    regional_menus.category.str.contains('pizza',case=False,na=False),'restaurant_id'])
                supplier_ids.update(valid.loc[valid.category.str.contains('pizza',case=False,na=False)
                                              & valid.id.isin(ids),'id'])
                regional_menus.loc[regional_menus.restaurant_id.isin(supplier_ids)].to_csv(menu_path,index=False)
    all_r = pd.read_csv(restaurants_path)
    r = all_r.copy()
    r = r.dropna(subset=['id', 'lat', 'lng'])
    r['distance_center'] = distances(r[['lat','lng']], [CENTER])[:, 0]
    r = r.loc[r.distance_center <= 55].copy()
    menus = pd.read_csv(menu_path)
    menu_pizza_ids = set(menus.loc[menus.category.str.contains('pizza',case=False,na=False),'restaurant_id'])
    r = r.loc[r.category.str.contains('pizza',case=False,na=False) | r.id.isin(menu_pizza_ids)].copy()
    # Deduplicate repeated identical names at identical locations, retaining the smallest source ID.
    r['name_key'] = r.name.map(clean_text)
    r['site'] = r.lat.round(4).astype(str) + '_' + r.lng.round(4).astype(str)
    repeated = r.duplicated(['name_key','site'], keep=False)
    r.loc[repeated].to_csv(ROOT/'resultats/duplicate_listing_audit.csv', index=False)
    r = r.sort_values('id').drop_duplicates(['name_key','site'])
    assert r.id.is_unique
    r['brand'] = r.name.map(brand_name)
    r['chain'] = (r.brand != 'Other or unclassified').astype(int)
    r['convenience'] = r.name_key.str.contains(r'^7-eleven|^stripes|^pj fresh', regex=True).astype(int)
    r['site_listings'] = r.groupby('site').id.transform('size')
    r['x_km'] = np.radians(r.lng-CENTER[1])*EARTH_KM*np.cos(np.radians(CENTER[0]))
    r['y_km'] = np.radians(r.lat-CENTER[0])*EARTH_KM
    r['quadrant'] = np.select([(r.x_km>=0)&(r.y_km>=0), (r.x_km<0)&(r.y_km>=0),
                              (r.x_km<0)&(r.y_km<0)], ['NE','NW','SW'], default='SE')
    r['grid10'] = np.floor(r.x_km/10).astype(int).astype(str)+'_'+np.floor(r.y_km/10).astype(int).astype(str)
    r['zip_clean'] = r.zip_code.astype(str).str.extract(r'(\d{5})', expand=False).fillna('Unknown')
    d = distances(r[['lat','lng']], r[['lat','lng']])
    other_site = r.site.to_numpy()[:,None] != r.site.to_numpy()[None,:]
    other_id = r.id.to_numpy()[:,None] != r.id.to_numpy()[None,:]
    for radius in [1,2,3,5]:
        r[f'competition_{radius}km'] = [r.loc[(d[i]<=radius)&other_site[i], 'site'].nunique() for i in range(len(r))]
    r['competition_listings_2km'] = ((d<=2)&other_id).sum(axis=1)
    recognized_same_brand = (r.brand.to_numpy()[:,None] == r.brand.to_numpy()[None,:]) & (r.chain.to_numpy()[:,None]==1)
    r['competition_otherbrand_2km'] = [r.loc[(d[i]<=2)&other_site[i]&(~recognized_same_brand[i]),'site'].nunique() for i in range(len(r))]
    r['competition_nonconvenience_2km'] = [r.loc[(d[i]<=2)&other_site[i]&(r.convenience.to_numpy()==0),'site'].nunique() for i in range(len(r))]
    r.to_csv(ROOT/'data/competitor_universe.csv',index=False)
    r[['id','name','brand','chain','site','site_listings']].to_csv(ROOT/'resultats/brand_and_site_audit.csv',index=False)
    menus = menus.loc[menus.restaurant_id.isin(r.id)].copy()
    menus['name_clean'] = menus.name.map(clean_text)
    menus['category_clean'] = menus.category.map(clean_text)
    menus['description_clean'] = menus.description.fillna('').map(clean_text)
    menus['price_usd'] = pd.to_numeric(menus.price.astype(str).str.extract(r'^\s*([0-9]+(?:\.[0-9]+)?)\s+USD\s*$', expand=False), errors='coerce')
    menus['pizza_category'] = menus.category_clean.str.contains('pizza',regex=False)
    text = menus.category_clean+' '+menus.name_clean
    exclusion = (r'\bslices?\b|\bcombos?\b|\bfeasts?\b|\bbundles?\b|\bparty\b|\bpackages?\b|'
                 r'\bmeals?\b|\bkits?\b|\bd\.?i\.?y\.?\b|\bmake at home\b|\bfamily special\b|'
                 r'\bbowls?\b|\bcrustless\b|\bbaking required\b|\btake.{0,3}bake\b|'
                 r'\bcalzones?\b|\bstromboli\b|\bpizzarolls?\b|\bpizza rolls?\b|\bpizza pocket\b|'
                 r'\btoppings?\b|\bextras?\b|\bsauces?\b|\bdrinks?\b|\badd.on\b|\bflatbread\b')
    menus['excluded_product'] = text.str.contains(exclusion,regex=True)
    # Pizza categories occasionally contain salads, wings or sides. Name-based exclusions are additional.
    menus['excluded_product'] |= menus.name_clean.str.contains(r'\bsalad\b|\bfries\b|\bgarlic bread\b|\bwings\b|\bcookie\b',regex=True)
    menus['excluded_product'] |= menus.description_clean.str.contains(
        r'\b(?:two|three|four|2|3|4)\s+(?:\w+\s+)?pizzas?\b|\bdough balls\b',regex=True)
    size_text = menus.name_clean+' '+menus.category_clean
    size = size_text.str.extract(r'\b(\d{1,2}(?:\.\d+)?)\s*(?:["″”]|\x27\x27|inches?\b|inch\b)',expand=False)
    menus['diameter'] = pd.to_numeric(size,errors='coerce')
    menus['giant_size'] = menus.diameter.gt(18)
    menus['rectangular'] = size_text.str.contains(r'\d+\s*["\x27″]*\s*[x×]\s*\d+',regex=True)
    menus['size_eligible'] = menus.diameter.isna() | menus.diameter.between(8,18)
    menus['eligible'] = menus.pizza_category & (~menus.excluded_product) & menus.price_usd.gt(0) & menus.size_eligible & (~menus.rectangular)
    menus['small_label'] = text.str.contains(r'\bsmall\b|\bpersonal\b|\bmini\b',regex=True)
    menus['large_label'] = text.str.contains(r'\blarge\b|\bx-large\b|\bxl\b',regex=True)
    # A product repeated in featured sections is one offer when its name, price and size are identical.
    menus['duplicate_offer'] = False
    eligible_indices = menus.index[menus.eligible]
    menus.loc[eligible_indices, 'duplicate_offer'] = menus.loc[eligible_indices].duplicated(
        ['restaurant_id','name_clean','price_usd','diameter'],keep='first')
    selected = menus.loc[menus.eligible & ~menus.duplicate_offer].copy()
    prices = selected.groupby('restaurant_id').agg(
        average_pizza_price=('price_usd','mean'), median_pizza_price=('price_usd','median'),
        n_pizzas=('price_usd','size'), min_price=('price_usd','min'), max_price=('price_usd','max'),
        diameter_mean=('diameter','mean'), diameter_known_share=('diameter',lambda a:a.notna().mean()),
        small_share=('small_label','mean'), large_share=('large_label','mean'))
    zero = menus.loc[menus.pizza_category].groupby('restaurant_id').price_usd.apply(lambda s:s.eq(0).mean())
    prices['zero_price_share'] = zero
    focal = r.loc[r.distance_center<=50].merge(prices,left_on='id',right_index=True,how='left',validate='one_to_one')
    focal['has_price'] = focal.average_pizza_price.notna().astype(int)
    focal['diameter_missing'] = focal.diameter_mean.isna().astype(int)
    focal['diameter_filled'] = focal.diameter_mean.fillna(12)-12
    focal['score_missing'] = focal.score.isna().astype(int)
    focal['score_filled'] = focal.score.fillna(4.5)-4.5
    focal['log_price'] = np.log(focal.average_pizza_price)
    focal['log_n_pizzas'] = np.log1p(focal.n_pizzas)
    focal.to_csv(ROOT/'data/focal_restaurants_all.csv',index=False)
    analysis = focal.loc[focal.has_price==1].copy()
    assert analysis.id.is_unique and analysis.average_pizza_price.gt(0).all()
    analysis.to_csv(ROOT/'data/analysis_restaurants.csv',index=False)
    menus.loc[menus.pizza_category].to_csv(ROOT/'data/menu_cleaning_audit.csv',index=False)
    selected.to_csv(ROOT/'data/eligible_pizza_items.csv',index=False)
    selected.sort_values('price_usd',ascending=False).head(60).merge(r[['id','name']],left_on='restaurant_id',right_on='id',suffixes=('_item','_restaurant')).to_csv(ROOT/'resultats/high_price_item_audit.csv',index=False)
    flow = pd.DataFrame([
        ['US restaurant records',len(all_r)],['Pizza-category or pizza-menu listings within 55 km',len(r)],
        ['Distinct observed pizza sites within 55 km',r.site.nunique()],
        ['Focal listings within 50 km before price filtering',len(focal)],
        ['Focal listings with eligible positive pizza price',len(analysis)],
        ['Eligible unique pizza offers in 55 km area',len(selected)]],columns=['stage','n'])
    flow.to_csv(ROOT/'resultats/sample_flow.csv',index=False)
    pd.DataFrame([['Regional menu rows',len(menus)],['Pizza-category menu rows',int(menus.pizza_category.sum())],
                  ['Positive-price pizza-category rows',int((menus.pizza_category&menus.price_usd.gt(0)).sum())],
                  ['Eligible rows before duplicate removal',int(menus.eligible.sum())],
                  ['Eligible unique offers',len(selected)]],columns=['stage','n']).to_csv(ROOT/'resultats/menu_flow.csv',index=False)
    print(flow.to_string(index=False));print(analysis[['average_pizza_price','competition_2km','n_pizzas']].describe().round(2).to_string())
    print('Chain groups',analysis.chain.value_counts().to_dict())
    return analysis


if __name__=='__main__':
    main()
