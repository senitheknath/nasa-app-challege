> Historical correction record. The global Crop Finder upgrade is documented in [UPGRADE_VERIFICATION.md](UPGRADE_VERIFICATION.md) and [GLOBAL_SCREENING.md](GLOBAL_SCREENING.md).

# AgroShift AI scientific correction

8 November 2026. The audit used the actual AgroShift working tree, including the uncommitted model, data, and wizard changes. Commit `3ec4548` preserves that starting point on the correction branch. The original suite passed all 61 checks before correction.

## Confirmed defects and their disposition

| What the code did | Correction | Where to inspect |
|---|---|---|
| The overview, wizard and chat used a 60/40 blend of a rule score and a transformed synthetic classifier score. The global rule score used 35/35/30 temperature/water/soil weights. | All farm-facing comparisons now use the regional interval assessment. The crop explorer groups those exact sequences by first crop. Unassessed traits widen the interval. | `app.py`, `agroshift/decision.py`, `agroshift/assistant.py` |
| The live wizard and station collector could substitute generated weather. The dashboard displayed “Live NASA” even before retrieval. The overview could use the Anuradhapura snapshot for another location. | The client checks request, response coordinates, source endpoint, dates, units and payload digest. Exact cached or archived evidence can serve during an outage. No match leaves the location unavailable. Source mode follows the loaded dataset. | `agroshift/power.py`, `scripts/collect_global_data.py` |
| The wizard translated irrigation categories into 250/450 mm, inserted a rainfall fraction, loam, good drainage or pH 6.5, and confirmed the pilot from country alone. | The form accepts independent measurements, quantity basis, assumptions, unknowns and explicit regional confirmation. Fictional benchmark inputs retain a demonstration label in the export. | `app.py`, `Farm` |
| Global rules added frost, heat, dry-spell, water, yield, seed and crop-calendar cutoffs without traceable parameter-level evidence. The atlas emitted another crop and a fixed score. | Unsupported traits are unknown. The regional pack identifies evidence for each scored trait. The simulation grid has no crop ranking. | `data/crops.json`, `agroshift/global_atlas.py` |
| Maize inherited the 18–27 °C figure from a finger millet paragraph. The mung bean example could exclude other cultivars. | Maize temperature remains unassessed. A short window blocks the documented MI 6 example only when the farmer selects MI 6. For unspecified mung bean cultivars it prompts review. | `data/crops.json`, `agroshift/decision.py` |
| Harvest and input quantities were calculated from generic rates and farm area. Some UI paths substituted literal fallback yields and seed amounts. | The farm workflow withholds quantitative harvest and input forecasts. Area remains part of the profile. | Crop advisor, chosen-rotation report and assistant |
| Missing weather could become invented radiation, humidity and extrema. A radiation proxy was labelled FAO-56 ET₀, and partly observed periods could become complete sums. | Missing weather stays missing. Historical Hargreaves ET₀ uses latitude, day of year and daily temperatures. Partial periods have no ET₀ total. Daily threshold counts state the actual thresholds. | `agroshift/climate.py` |
| The educational time-series code evaluated temperature predictions after fitting the full series and mixed arbitrary forecasts. | Rainfall backtesting compares an expanding mean and exponential smoothing. Model selection precedes testing and each prediction uses only earlier seasons. Only held-out rainfall errors appear in the studio. | `agroshift/ml_engine.py` |
| Unlisted countries received hash-generated coordinates. The atlas reported a fixed number of observations regardless of available raw evidence. | Countries without a known preset require a map point, town or manual coordinates. The collection manifest is rebuilt from checked raw records. | `agroshift/global_atlas.py`, `data/global_nasa_stations_summary.csv` |
| Assistant wording asserted unmeasured effective rainfall and frost screening. Optional Gemini text was rendered directly. | Local explanations use the calculated evidence. Optional Gemini selects from known topic IDs. The application supplies the text and rejects unfamiliar IDs and free-form output. | `agroshift/assistant.py` |

The legacy collector contained a synthetic fallback. Its existence alone cannot establish which old rows were simulated. The current manifest can be reproduced from the bundled raw archives. A SHA-256 digest detects corruption relative to the saved record. It is not a digital signature from NASA.

## Dataset and label register

| Resource | Origin and purpose | Permitted interpretation |
|---|---|---|
| NASA POWER daily responses, local cache, `data/demo_power.json`, `data/stations/*.json.gz` | Official POWER Daily API, AG community, LST. Raw environmental observations/reanalysis and provenance. | Historical environmental indicators. Each archive has query, date, units, source products and digest. |
| `data/global_nasa_stations_summary.csv` | Derived collection log with a raw evidence path and digest for each available row. | Verified environmental coverage. A site is a requested grid point. |
| `data/crops.json` | Sri Lanka DOA, RRDI and indicative FAO ET ranges. | Regional reference screening. No field outcome labels. |
| Farm form and benchmark profiles | Farmer reports or clearly labelled fictional profiles. | User inputs and assumptions. Scenarios alter a copy of the observations or farm settings. |
| `data/global_crop_dataset.csv` and the model bundle | The historical generator starts with a crop class, then samples traits conditioned on that class. The continuous target combines thermal, water and pH terms, interactions and random noise. | Synthetic educational examples. The 8,400/1,800/1,800 split uses shuffled rows from one generator. Test metrics measure recovery of the generator's labels. |
| `agroshift/educational_traits.py` | Historical class-generator settings, including ten crop names and unsupported thresholds. | Educational generator parameters only. They are excluded from the agricultural reference pack. |
| Global grid and weather simulation | Seeded or deterministic formulae. Country index is navigation metadata. | Educational simulation in the studio. The assessment and report boundaries reject simulated weather. |
| Historical rainfall backtest | Verified seasons for the selected point. The target is observed seasonal rain in mm. | Descriptive hindcast errors for that series. No crop target or production forecast. |
| FAOSTAT crop statistics | Published country-year harvested area, yield and production. | Useful for regional context. Aggregates cannot identify how alternative crops would have performed in the same field. [FAO data catalogue](https://data.fao.org/catalog/iso/d24a448b-3b62-4c09-8c1d-4a39bb599876) |
| Sri Lankan paddy statistics | District/season crop-cutting estimates for rice. | Potential independent comparison for area-level rice yield research. Coverage does not supply labelled outcomes for alternative pulse rotations on the same field. [Department of Census and Statistics](https://www.statistics.gov.lk/Agriculture/StaticalInformation/PaddyStatistics) |

No independently labelled farm-suitability training set was identified in the checkout or these two candidate sources. Future model development needs plot/season identifiers, rotation and cultivar histories, planting dates, measured soil and irrigation, management and independently observed outcomes, including failures. Reserve whole farms, regions and later seasons for evaluation. Compare against simple baselines and examine calibration before exposing probability estimates.

## Decision method

1. Validate the saved farm, match the observation coordinates, and check regional capability. Level 1 provides global NASA analysis. Level 2 adds reference screening for farmer-confirmed Sri Lankan lowland dry/intermediate settings. The coarse bounding box is a guard, not a zone map. Level 3 requires independent regional field validation. No current location qualifies.
2. Align daily values on the complete requested calendar. Complete daily precipitation is required for totals. Temperature means require 90% coverage. Cross-year windows use the following calendar year. A dry day has less than 1 mm rain. A missing day interrupts a known run. The engine requires ten usable historical seasons per slot as an engineering coverage rule. [NASA Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) · [Climdex indices](https://www.climdex.org/learn/indices/)
3. Generate the selected baseline and the Cartesian product of allowed crops for two slots. Persistent waterlogging blocks drainage-dependent species. A window shorter than a documented regional minimum or a selected cultivar example triggers an explicit constraint. Unknown durations require local calendar review.
4. Score each criterion using the table below. The two future slots have equal importance. Unknown contributions span the full 0–1 interval.

| Criterion | Input and normalization | Interpretation |
|---|---|---|
| Temperature | Fraction of usable historical seasonal mean temperatures inside the cited preferred range, °C | Descriptive overlap. Stage-specific heat damage remains unassessed. |
| Water | Median complete seasonal rain in mm × explicit usable fraction + explicitly supplied net irrigation in mm. For maize and groundnut, divide by the upper/lower FAO ET bounds and cap each at one. | Conditional screening under a simplified water budget. Water timing, runoff and soil storage remain unresolved. Rice total supply and pulse ET are unassessed. |
| Soil | Average the known/unknown drainage and pH contributions. A measured pH inside a cited preferred range scores one, outside scores zero for that preference. | Preferred pH is a soft criterion. Texture, water-holding capacity and nutrient notes are recorded independently. |
| Diversification | Mean of different-family transitions from current crop through both slots. Unknown current crop widens the first transition. | Preference for botanical diversity. Nitrogen gain, disease reduction and yield benefit are unquantified. |

Four equal initial priorities express a neutral interface starting point. Normalize the user's nonnegative priorities to sum to one. Multiply by the component bounds, sum and scale to 100 points. Sort feasible sequences by lower bound. IDs resolve display ties. Display blocked sequences separately by status. A leader with an overlapping competitor has unresolved ordering. The sensitivity table moves one slider at a time by up to ten points. The water criterion incorporates rainfall once. Humidity, ET₀, solar energy and dry-spell charts supply context without adding correlated score terms. The additive structure and equal slot weights remain modelling assumptions. [MCDA guidance](https://analysisfunction.civilservice.gov.uk/policy-store/an-introductory-guide-to-mcda/)

The Hargreaves diagnostic uses FAO-56 equations 21–25 and 52 with extraterrestrial radiation converted to equivalent water depth. It needs local calibration. VPD is an approximation from temperature extrema and mean relative humidity. GDD₁₀ sums positive daily mean temperature above 10 °C as a descriptive index. The app derives no species threshold from these diagnostics. [FAO-56 meteorological equations](https://www.fao.org/4/x0490e/x0490e07.htm) · [FAO-56 ET₀ equations](https://www.fao.org/4/x0490e/x0490e08.htm)

## Agricultural references checked

| Crop | Retained numerical evidence and scope |
|---|---|
| Rice | 450–700 mm indicative seasonal ET. Paddy establishment, ponding and seepage add water needs. [FAO Table 14](https://www.fao.org/4/s2022e/s2022e07.htm) · [RRDI land preparation](https://doa.gov.lk/rrdi_watermanagement_landpreparation/) |
| Mung bean | Preferred 25–32 °C in local guidance. MI 6 harvest example 55–65 days. Cultivar and final picking date matter. [DOA mung bean, Sinhala](https://doa.gov.lk/field-crops-mungbean-si/) |
| Cowpea | 20–30 °C, preferred pH 6–7, harvest example 75–90 days, sensitivity to waterlogging. [DOA Kilinochchi, cowpea](https://doa.gov.lk/fcrdi-rardckilinochchi-crops/) |
| Maize | 500–800 mm indicative ET and local drainage guidance. Preferred temperature is unknown in this pack. [FAO Table 14](https://www.fao.org/4/s2022e/s2022e07.htm) · [DOA Kilinochchi, maize](https://doa.gov.lk/fcrdi-rardckilinochchi-crops/) |
| Groundnut | 500–700 mm indicative ET, well-drained soil, regional preferred pH 6.5–7.0. [FAO Table 14](https://www.fao.org/4/s2022e/s2022e07.htm) · [DOA Kilinochchi, groundnut](https://doa.gov.lk/fcrdi-rardckilinochchi-crops/) |

Frost limits, lethal heat, stage-specific dry-spell limits, required GDD, solar thresholds, expected farm yield and quantified legume credits remain unassessed. The JSON pack records missing fields and per-trait citations. The next scientific step is cultivar- and zone-specific review with local agronomists, followed by independent field evaluation.
