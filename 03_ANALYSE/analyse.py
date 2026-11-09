"""Five models, four tests and two diagnostics for the Group 9 project."""
from pathlib import Path
import json,shutil
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import main as prepare

ROOT=Path(__file__).resolve().parent
# Cleaning audits and regression results are kept together.
(ROOT/'resultats').mkdir(exist_ok=True)
(ROOT/'figures').mkdir(exist_ok=True)
prepare()
d=pd.read_csv(ROOT/'data/analysis_restaurants.csv')
d['east10']=d.x_km/10;d['north10']=d.y_km/10
d['log_reviews']=np.log1p(d.ratings.fillna(0))
d.to_csv(ROOT/'data/Dataset_final_G09.csv',index=False,encoding='utf-8-sig')
base='log_price ~ competition_2km'
geo=' + east10 + north10 + I(east10 ** 2) + I(north10 ** 2) + east10:north10'
menu=' + diameter_filled + diameter_missing + diameter_known_share + small_share + large_share'
formulas={'M1':base,'M2':base+geo,'M3':base+geo+' + chain','M4':base+geo+' + chain'+menu,'M5':base+geo+' + chain'+menu+' + competition_2km:chain'}
models={k:smf.ols(f,d).fit(cov_type='HC3',use_t=True) for k,f in formulas.items()}
rows=[];coef=[]
ix=np.random.default_rng(20261108).permutation(len(d));train=d.iloc[ix[:477]];test=d.iloc[ix[477:]]
for name,m in models.items():
 assert m.nobs==597 and np.linalg.matrix_rank(m.model.exog)==len(m.params)
 mt=smf.ols(formulas[name],train).fit();pred=np.exp(mt.predict(test))*np.exp(mt.resid).mean()
 rows.append(dict(model=name,n=int(m.nobs),coef=float(m.params.competition_2km),se=float(m.bse.competition_2km),adjusted_R2=float(m.rsquared_adj),RMSE_usd=float(np.sqrt(np.mean((test.average_pizza_price-pred)**2)))))
 for t in m.params.index:
  lo,hi=m.conf_int().loc[t];coef.append(dict(model=name,term=t,coef=float(m.params[t]),se=float(m.bse[t]),p=float(m.pvalues[t]),low=float(lo),high=float(hi)))
pd.DataFrame(rows).to_csv(ROOT/'resultats/modeles.csv',index=False)
pd.DataFrame(coef).to_csv(ROOT/'resultats/coefficients.csv',index=False)
m=models['M4'];added=[t for t in m.params.index if t not in models['M1'].params.index]
t=m.t_test('competition_2km=0')
tests=[dict(id='T1',model='M4',null='Competition coefficient = 0',statistic='t',value=float(np.asarray(t.tvalue).item()),p=float(t.pvalue))]
for tid,name,terms,label in [('T2','M4',added,'All 11 controls = 0'),('T3','M4',[t for t in m.params.index if t!='Intercept'],'All 12 slopes = 0'),('T4','M5',['competition_2km:chain'],'Chain slope difference = 0')]:
 f=models[name].f_test(', '.join(t+'=0' for t in terms));tests.append(dict(id=tid,model=name,null=label,statistic='F',value=float(f.fvalue),p=float(f.pvalue)))
pd.DataFrame(tests).to_csv(ROOT/'resultats/tests.csv',index=False)
groups=[]
for label,expr in [('Other or unclassified','competition_2km=0'),('Identified chain','competition_2km + competition_2km:chain=0')]:
 t=models['M5'].t_test(expr);lo,hi=t.conf_int()[0];b=float(np.asarray(t.effect).item())
 groups.append(dict(group=label,percent=float(100*np.expm1(b)),low=float(100*np.expm1(lo)),high=float(100*np.expm1(hi)),p=float(t.pvalue)))
pd.DataFrame(groups).to_csv(ROOT/'resultats/interaction.csv',index=False)
bp=het_breuschpagan(m.resid,m.model.exog)
reset_data=d.assign(fitted2=m.fittedvalues**2,fitted3=m.fittedvalues**3)
reset=smf.ols(formulas['M4']+' + fitted2 + fitted3',reset_data).fit(cov_type='HC3',use_t=True).f_test('fitted2=0,fitted3=0')
diagnostics={'BP_stat':float(bp[0]),'BP_p':float(bp[1]),'RESET_F':float(reset.fvalue),'RESET_p':float(reset.pvalue)}
# A single stricter sample checks the major price-comparability limitation.
sub=d[d.diameter_known_share>=.5];ms=smf.ols(formulas['M4'],sub).fit(cov_type='HC3',use_t=True)
lo,hi=ms.conf_int().loc['competition_2km']
size_check=dict(n=len(sub),percent=float(100*np.expm1(ms.params.competition_2km)),low=float(100*np.expm1(lo)),high=float(100*np.expm1(hi)),p=float(ms.pvalues.competition_2km))
lo,hi=m.conf_int().loc['competition_2km']
r={'models':rows,'tests':tests,'groups':groups,'diagnostics':diagnostics,'size_check':size_check,'formulas':formulas,'main':{'percent':float(100*np.expm1(m.params.competition_2km)),'low':float(100*np.expm1(lo)),'high':float(100*np.expm1(hi)),'p':float(m.pvalues.competition_2km)},'mean_price':float(d.average_pizza_price.mean()),'mean_competition':float(d.competition_2km.mean()),'known_size_share':float(d.diameter_known_share.mean())}
(ROOT/'resultats/resultats.json').write_text(json.dumps(r,indent=2))
fig,ax=plt.subplots(figsize=(7,3.1));ax.scatter(d.competition_2km,d.average_pizza_price,s=13,alpha=.4,color='#235E7B');ax.set(xlabel='Other pizza sites within 2 km',ylabel='Mean whole-pizza price (USD)');fig.tight_layout();fig.savefig(ROOT/'figures/prix_et_concurrence.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(6.5,2.8));ax.bar([r['model'] for r in rows[:4]],[100*r['adjusted_R2'] for r in rows[:4]],color=['#235E7B']*3+['#007F83']);ax.set(ylabel='Adjusted R squared (%)',ylim=(0,27));fig.tight_layout();fig.savefig(ROOT/'figures/ajustement.png',dpi=180);plt.close(fig)
print('Done: 597 listings; 5 models; 4 tests; 2 diagnostics.')
