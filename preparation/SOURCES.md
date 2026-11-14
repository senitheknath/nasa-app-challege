> **8 November audit amendment.** The 18–27 °C passage previously associated with maize is about finger millet. The current maize temperature is unknown. See [the checked trait register](../docs/SCIENTIFIC_AUDIT.md). The following is the historical preparation record.

# Source register

Checked 4 November 2026, using the user's Asia/Colombo date. Entries distinguish
official primary material, local-organizer material, and unresolved checks.
Search-index text is not proof that the entire live page has been inspected.
The notes are paraphrases; use the original resources for complete guidance.

## Competition

| ID | Resource | Evidence and limit |
|---|---|---|
| C01 | [Official event homepage](https://www.spaceappschallenge.org/) | Official indexed page confirms 14–15 November 2026 and open registration. Direct fetch failed. |
| C02 | [Official Field Shift challenge](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) | Official indexed summary confirms NASA observations + local soil + crop characteristics + farmer priorities for rotation decisions. Full live page could not be retrieved. |
| C03 | [Official resources](https://www.spaceappschallenge.org/resources/) and [participant FAQ](https://www.spaceappschallenge.org/resources/participant-faqs/) | Repeated fetch errors; browser attempt timed out; WSL reported certificate verification failure. Current rules not fully verified. TLS verification was not disabled. |
| C04 | [Official legal page](https://www.spaceappschallenge.org/legal/) | The correct terms link was discovered through NASA's repository; inspect current 2026 terms before relying on reuse permissions. |
| C05 | [NASA spaceapps README](https://github.com/nasa/spaceapps/blob/main/README.md) | Read through GitHub connector. Identifies 2026 registration and links to official terms. Does not itself explain pre-event work or AI rules. |
| C06 | [HackAthlone challenge reproduction](https://hackathlone.com/challenges/adapting-farms-with-nasa-data) | Local organizer's reproduction, not an independently verified full NASA page. Suggested datasets include POWER, SMAP, ECOSTRESS, GPM, Landsat, MODIS, GRACE/FO and elevation. Three strategies including the existing one are phrased as a suggestion. Says resources arrive 13 November. |
| C07 | [HackAthlone preparation advice, 3 November 2026](https://hackathlone.com/blogs/hackathon-tech-stack) | Organizer says prepare tools now and build during the event; submission guide expected 13 November. Supports a conservative preparation boundary, not a substitute for global terms. |
| C08 | [Universal Event 2026](https://www.spaceappschallenge.org/2026/local-events/universal-event/) | Direct retrieval failed. Registered event, team owner, applicable timezone, solo eligibility and exact submission deadline still need confirmation. |
| C09 | [2026 Participant Terms & Conditions (Indexed)](https://www.spaceappschallenge.org/legal/) | Indexed summary confirms non-NASA "Solution Materials" must be freely/publicly available or OSI open-source licensed with citations and license documentation; original content defaults to Apache-2.0. Added `LICENSE` (Apache-2.0). |
| C10 | [2026 Participant FAQ — AI / Super Intelligence (SI) Rules (Indexed)](https://www.spaceappschallenge.org/resources/participant-faqs/) | Indexed summary confirms AI/SI tools are permitted and do not penalize judging when disclosed via the mandatory submission question ("Did you utilize any Artificial Intelligence tools and software in preparing your solution? If yes, which ones and how did you use them?"). |

Do not rely on the staging-web-v2 participant page: the retrieved text contains
2023 dates despite a 2026 page timestamp. Do not infer current rules from 2025
Universal Event pages or third-party project READMEs. No official 2026 rubric
weights, video limit, AI disclosure wording, or submission field lengths have
been verified. Do not call 23:59 on 15 November a confirmed Colombo deadline.

## NASA data

| ID | Resource | Use |
|---|---|---|
| D01 | [POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Point JSON requests, time standards and parameter limits. Daily default is LST; specify explicitly. |
| D02 | [POWER meteorological sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/) | MERRA-2/GEOS-IT origins; source grids and latency; IMERG daily UTC aliases. |
| D03 | [POWER services](https://power.larc.nasa.gov/docs/services/) | Standard meteorology 0.5° × 0.625°, solar approximately 1° × 1°; avoid redundant fine-grid requests. |
| D04 | [POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/) | Meteorology begins 1981; solar begins 1984 with source changes including CERES from 2001. Do not treat every monthly field as a monthly sum. |
| D05 | [POWER parameter dictionary](https://power.larc.nasa.gov/parameters/) | Parameter metadata landing page. Actual units for our six parameters were also verified from live responses. |
| D06 | [POWER methodology](https://power.larc.nasa.gov/docs/methodology/) | New higher-resolution sources include IMERG and SMAP L4; runtime availability and exact aliases need separate testing. |
| D07 | [SMAP SPL3SMP_E v6](https://nsidc.org/data/spl3smp_e/versions/6) | Daily product since 31 March 2015, 9 km grid, HDF5. |
| D08 | [SMAP L3 v6 user guide](https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf) | Approximately top 5 cm; ~36 km native radiometer footprint interpolated onto 9 km grid. Read retrieval and surface flags; masks cover water, frozen soil and other interference. |
| D09 | [SMAP SPL4SMGP v8](https://nsidc.org/data/spl4smgp/versions/8) | Three-hourly 9 km surface/root-zone model-assimilation product. Page warns of a May–July 2026 geolocation issue and reprocessing. Recheck status and version before use. |
| D10 | [MOD13Q1 specification](https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13Q1) and [MODIS vegetation guide](https://landweb.modaps.eosdis.nasa.gov/data/userguide/MODISC6VIUserguide.pdf) | 250 m, 16-day vegetation indices; scaling, fill values and QA. |
| D11 | [MOD13Q1 collection archive](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MOD13Q1) | Collection 6.1 archive includes 2000 onwards; downloads use Earthdata authentication. |
| D12 | [NASA MOD13 visualization metadata](https://git.earthdata.nasa.gov/projects/VISLABS/repos/metadata-mapping/browse/umm/visualization/v0.11.0-sample/tiles/modaps/MOG13Q1_LQD_NDVI_v61_STD.json?at=10201d1a588) | Records starting date 18 February 2000. Product is a composite, not daily field monitoring. |

The NASA POWER raw responses in `evidence/` are first-party measurements/model
outputs retrieved by this session. Their manifest records exact request URLs,
headers, parameter units, SHA-256 hashes and retrieval timestamps.

## Agronomy and decision methods

| ID | Resource | Use and limits |
|---|---|---|
| A01 | [FAO Irrigation and Drainage Paper 56](https://www.fao.org/4/x0490e/x0490e00.htm), Allen et al., 1998 | Reference evapotranspiration, crop coefficients, water balance and water-stress framework. A method reference, not local cultivar validation. |
| A02 | [FAO crop water needs, Table 14](https://www.fao.org/4/s2022e/s2022e07.htm) | Indicative seasonal ET needs: maize 500–800 mm, groundnut 500–700 mm, paddy rice 450–700 mm. Not irrigation delivery requirements. Generic beans must not stand in for mung bean or cowpea. |
| A03 | [Sri Lanka DOA mung bean, Sinhala](https://doa.gov.lk/field-crops-mungbean-si/) | Local growing conditions, planting windows, drainage, irrigation and variety guidance. Review translation and cultivar applicability before encoding. English landing page is a placeholder. |
| A04 | [DOA Kilinochchi crop guidance](https://doa.gov.lk/fcrdi-rardckilinochchi-crops/) | Regional crop references for maize, cowpea and groundnut. Descriptive preferred ranges are not universal lethal thresholds. |
| A05 | [DOA crop suitability user guide](https://csrforgnd.doa.gov.lk/User%20Guide%20for%20web.pdf) | Agroecological region, soils, crop calendars and drainage. Existing administrative mapping is provisional; requires current local checking. |
| A06 | [RRDI rice land preparation water](https://doa.gov.lk/rrdi_watermanagement_landpreparation/) | Paddy water includes soaking, ponding, seepage/percolation and evaporation; distinguish from crop ET. |
| A07 | [DOA 2021 Yala advisory](https://doa.gov.lk/wp-content/uploads/2021/05/Agro-met-advisory-SWM-2021.pdf) | Historical example of conditional rice/other-field-crop transitions and residual-moisture mung bean. Not a 2026 forecast or current blanket recommendation. |
| A08 | [Government Analysis Function MCDA introduction](https://analysisfunction.civilservice.gov.uk/policy-store/an-introductory-guide-to-mcda/) | Additive value models, swing weighting and sensitivity analysis. Agricultural scores still require our own documented evidence and validation. |
| A09 | [FAO integrated soil management manual](https://www.fao.org/4/x4799e/x4799e.pdf) | Rotation/residue/soil-management concepts. Does not justify fixed nitrogen credits for every grain-legume rotation. |

Still needed: cultivar-specific durations and temperature responses; mung-bean
and cowpea water references; actual local rotation trial evidence; drainage and
soil applicability; farmer/expert review. No completed reference table is yet
sufficient to call the Sri Lanka model agronomically validated.

## Tooling

- [Streamlit installation](https://docs.streamlit.io/get-started/installation/command-line): isolated venv, pip, built-in hello example. Retrieved page lists Python 3.11–3.15 support.
- [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app): dependencies, secrets, file layout and deployment. Recheck available Python versions in deployment settings.
- [VS Code WSL](https://code.visualstudio.com/docs/remote/wsl): use Windows VS Code connected to the WSL interpreter.
- [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) & GeoNames (CC BY 4.0): free non-commercial place search used in `agroshift/geography.py`.
- [OpenStreetMap](https://www.openstreetmap.org/copyright) & [Folium](https://python-visualization.github.io/folium/): interactive map tiles and markers used in `app.py`.

All software recommendations remain subject to actual installation and checks
recorded in STATUS.md. A linked documentation page is not an executed test.
