# Group 9 — Local Competition and Pizza Prices

This simplified version replaces the previous documents. The research question, data, and main results remain unchanged. It presents four successive models and one interaction extension.

This document allows you to quickly identify the relevant files, the approach followed, and the main results of the study.

## Documents used

| Purpose | File |
|---|---|
| Report to consult | `01_RAPPORT/Rapport_G09_Concurrence_Pizzas.pdf`: 4 pages, in English |
| Presentation support | `02_PRESENTATION/Presentation_G09.pptx`: notes in French, approximately 15 minutes |
| Viewing the slides without PowerPoint | The PDF with the same name, in the same folder |
| Final dataset | `03_ANALYSE/data/Dataset_final_G09.csv`: 597 rows and 50 columns |
| Variable description | `03_ANALYSE/data/Dictionnaire_attributs_G09.csv` |
| Regression code | `03_ANALYSE/analyse.py` |
| Data cleaning and neighbor count | `03_ANALYSE/prepare_data.py` |

The project includes a report and a slide deck. The CSV files in the `resultats` folder contain the calculations used to produce them and are not separate documents to submit. The report provides the methodological justifications, while the slide deck supports the oral presentation.

## Research question and data

The study examines whether restaurants surrounded by more competitors offer lower-priced pizzas. A negative relationship would be plausible because customers have more alternatives in such areas.

The sample contains 597 Uber Eats listings located within a 50 km radius of downtown Houston. A listing does not necessarily correspond to a distinct physical restaurant: the sample represents 552 sites.

For each listing, the average price of the selected whole-pizza offers is calculated. Other sites selling pizzas within a 2 km radius are then counted. Competitors without a price or rating are still included in this count. The site of the restaurant being studied is excluded entirely.

The analysis begins by comparing price and competition, then adds location, identified-chain status, and menu characteristics. Price is expressed in logarithmic form to make the relationship easier to interpret as a percentage.

In M4, one additional competitor is associated with approximately **+0.59%** in adjusted price. The expected negative sign is therefore not found. This result does not show that opening a new restaurant causes prices to rise: an area with strong demand may attract both more restaurants and higher prices.

## Rationale for each model

| Model | Added variables | Objective |
|---|---|---|
| M1 | Competition alone, with an intercept | Provide a simple starting point |
| M2 | Location | Account for price differences between areas |
| M3 | Identified-chain indicator | Account for observable differences between groups of chains |
| M4 | Menu characteristics | Compare offers that are more similar in size and composition |
| M5 | M4 + competition × chain | Determine whether the competition-price relationship differs between groups |

Models M1 to M4 form the core of the analysis. M5 is the only extension. To avoid a gap in the numbering, the former M6 interaction was renamed M5. The former reputation, curvature, and quadrant models are not part of this version.

Location is represented by two coordinates, their squares, and their product. This specification allows prices to vary flexibly according to location without claiming to measure every characteristic of each neighborhood.

The menu variables include the mean known diameter, an indicator showing that no diameter is known, the share of known diameters, and the shares of offers carrying the small and large labels. These labels are not converted into invented centimeter values.

The average price does not become perfectly comparable through these variables because many sizes remain unknown. The average share of known sizes is 21.2% per listing.

## Main results

The menu variables substantially improve the fit: adjusted R² increases from approximately 2.2% in M3 to 22.6% in M4. The competition coefficient remains close to its initial value.

The internal prediction error in dollars decreases from $4.62 in M1 to $3.91 in M4. This result is based on a single split of 477 training observations and 120 test observations; it does not guarantee similar performance in another city.

In M5, the estimated comparisons are +0.70% for other or unclassified listings and +0.30% for identified chains. The difference is not established: p = 0.450. Unclassified listings should therefore not automatically be treated as independent restaurants.

## Statistical tests

| Test | Question | Conclusion at the nominal 5% level |
|---|---|---|
| T1, M4 | Is the competition coefficient equal to zero? | Rejection: positive association, p = 0.0129 |
| T2, M4 | Are all 11 control coefficients equal to zero? | Rejection: the controls collectively add information |
| T3, M4 | Are all 12 non-intercept coefficients equal to zero? | Rejection: the model has overall explanatory content |
| T4, M5 | Is the slope identical in both groups? | No rejection: difference not established, p = 0.450 |

T1 is a two-sided t-test. The other tests are Wald F-tests with HC3 standard errors. HC3 accounts for error variance that may differ between observations; this correction does not, however, address all dependencies between neighboring restaurants.

A small p-value does not mean that the effect is large or that the relationship is causal. Similarly, failing to reject a hypothesis does not prove that it is true. Each test is discussed in the report.

## Model checks

The Breusch–Pagan test indicates that the constant-variance assumption is not appropriate under its independence reference. This result motivates the use of HC3 standard errors.

The RESET test rejects the tested M4 specification, with p = 0.0058. M4 explains the data better than M1, but some relationships or variables are probably still represented inadequately. The test does not provide a list of variables to add.

A check directly related to the size issue is also retained: requiring at least half of the diameters to be known leaves 111 listings. The estimated association is approximately +0.40%, but the confidence interval includes zero. This limitation should be stated explicitly.

## Sources and calculation files

Source: Ahmed Shahriar Sakib, *Uber Eats USA Restaurants and Menus*, Kaggle: https://www.kaggle.com/datasets/ahmedshahriarsakib/uber-eats-usa-restaurants-menus

The source files are dated November 22, 2023; individual collection dates are not certified. The restaurant file comes from the provided project. The offers come from the retained raw regional extract of the same dataset, not from the former averages calculated across all dishes. Reproduction begins with these two available files; it does not establish that the extract fully covers the national file.

| Item | Calculation file in `03_ANALYSE/resultats` |
|---|---|
| Coefficients, adjusted R², and prediction error | `modeles.csv` |
| All coefficients and their intervals | `coefficients.csv` |
| Four T1–T4 tests | `tests.csv` |
| Slopes for the two groups in M5 | `interaction.csv` |
| Diagnostics, size check, and formulas | `resultats.json` |
| Sample construction steps | `sample_flow.csv`, `menu_flow.csv` |

The duplicate, chain-name, and high-price control files are used to verify the cleaning process. The `prix_et_concurrence.png` and `ajustement.png` figures show price dispersion and the progression of adjusted R².


## Reproduction

Python 3.12 is recommended, together with a LaTeX installation including `pdflatex`:

```bash
python -m pip install -r requirements.txt
python reproduire.py
```

This command reruns the cleaning process, the five models, and the tables, then compiles the PDF. The PowerPoint is edited separately; if you modify the results, you will therefore need to update the slides as well.

The `04_LATEX/Rapport.tex` source can be imported directly into Overleaf: the tables are already populated, and no external figure is required for compilation. The `% BEGIN ...` sections are regenerated by the script; the other paragraphs can be edited.

You will need to add the actual names and contributions if required by the submission instructions. No contribution has been invented.
