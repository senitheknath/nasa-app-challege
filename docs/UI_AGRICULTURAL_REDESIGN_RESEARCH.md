# Agricultural UI redesign: research and design decisions

Prepared 9 November 2026 before the "Field & Soil" interface redesign. This records what was researched, what was verified, and which design decisions follow from the evidence. It does not change any scientific calculation.

## 1. Baseline UI audit

| Area | Before the redesign | Problem for farmers |
|---|---|---|
| Visual identity | Generic SaaS blue (`#2563EB`) on white, a single text hero with no imagery | Nothing reads as agricultural, and the page did not look trustworthy enough for land-use decisions |
| Home | Headline and three buttons | Didn't show what data is used, what the tool can do, or how many crops are covered |
| Location | Map preview hidden behind a checkbox; OpenStreetMap street tiles only | Farmers recognise fields from imagery, not street maps |
| Field and season | Plain stacked forms; no location context after a place was chosen | Already-retrieved soil and climate history was not shown; farmers had to guess growing months |
| Results | Text-only cards in a 2×2 grid | No at-a-glance overview, icons or visual hierarchy; status was mostly communicated by text colour |
| Crop details | Long expander list; the FAO GAEZ map class had to be fetched manually per water system | Important context was buried; one manual step per scenario |
| Climate | Single-variable bar chart that switched with a radio button | Rain and temperature could not be read together, which is how agronomists read climate |
| Dashboard | Two text boxes | No visual summary, no data-completeness guidance |

## 2. Research findings

### 2.1 Farmer-facing decision-support UX

Recurring findings in agtech UX literature and practitioner guidance (summarised from searches of field-usability writing on medium.com, GSMA AgriTech, researchgate field studies and agency case studies):

- **Field conditions**: high contrast for sunlight legibility. Touch targets of 44–48 px. Lightweight pages for mid-range phones and patchy networks.
- **Visual over text**: icons, colour-coded status *plus* text labels, and simple illustrations instead of numerical tables.
- **Decision-centric layout and progressive disclosure**: a headline summary first, with detail one tap away.
- **Trust through explanation**: say *why* a crop is shown, show sources, and let the farmer override automation (human in the loop).
- **Automation with confirmation**: pre-fill what is known, but let the farmer confirm. Never silently commit an automated guess.

**Decision:** keep the three-step wizard. Show a "What we already know about this location" panel at each step, use icons and status chips throughout, put an overview first on results, and offer suggestions only as explicit, one-click actions the farmer confirms.

### 2.2 Leading agtech product patterns

Field-management products (OneSoil, Climate FieldView, xarvio FIELD MANAGER, Cropwise) consistently use:

- a **map-first** field view with satellite imagery and a field pin or boundary;
- **modular cards** with a hero summary (field name, area, crop, season);
- **micro-charts and KPI tiles** rather than long tables;
- a **crop-calendar timeline** (12-month strip) for seasons;
- an **earthy green** primary palette with muted amber and red for alerts, and readable sans-serif type with tabular numerals.

**Decision:** adopt satellite imagery for location and field maps, KPI tiles, a 12-month calendar strip and a forest-green, wheat and soil palette.

### 2.3 Agricultural climate visualisation standards

- **Walter–Lieth climate diagram (climograph)**: monthly precipitation bars plus a temperature curve on one chart, the standard way ecologists and agronomists read site climate. (Walter & Lieth, *Klimadiagramm-Weltatlas*, 1967; FU Berlin teaching material.)
- **FAO Length of Growing Period (LGP)**: in FAO agro-ecological zoning, the rainfed growing period begins when precipitation reaches **half of potential evapotranspiration** (P ≥ 0.5 PET), and the thermal growing period requires mean temperature above 5 °C. FAO adds soil-moisture carry-over (about 100 mm) after rains end. (FAO AEZ methodology; FAO *Agro-ecological zoning guidelines*, Soils Bulletin 73.)
- **FAO / GIEWS crop calendars**: a 12-column (J–D) grid with coloured bars for sowing, growing and harvest periods.

**Decisions:**

1. The climate page and dashboard use one combined climograph: monthly rain bars, Hargreaves reference evapotranspiration (ET₀) and mean temperature. Months that meet the FAO rain threshold are shaded.
2. Season step: a **suggested growing window** computed from the site's own NASA POWER history. It uses the longest continuous run of months where mean monthly rain ≥ 0.5 × ET₀ and mean temperature ≥ 5 °C. It is labelled as a **monthly approximation without soil-water carry-over**. The farmer must press a button to use it, and it never selects months automatically.
3. Season step: a FAO-style **12-month calendar strip** showing rainfall intensity, rain-supported months, the suggested window and the farmer's chosen season.

### 2.4 Official colour legends

- **GAEZ v5 suitability classes**: colours were taken from the official FAO SLD style (`data.apps.fao.org/gismgr/api/v2/catalog/workspaces/GAEZ-V5/styles/SIX/sld`, fetched 9 Nov 2026): Very high `#007000`, High `#15ae11`, Good `#ace15e`, Medium `#fed801`, Moderate `#ce9d53`, Marginal `#cd6c01`, Very marginal `#808080`, Not suitable `#cfcfcf`, Water `#aad3df`. AgroShift shows these colours *with* the class label (WCAG 1.4.1).

### 2.5 Satellite basemap licensing (verified)

| Candidate | Finding | Decision |
|---|---|---|
| Esri World Imagery | Use outside ArcGIS requires an ArcGIS Location Platform account under Esri's terms | Not used |
| **EOX Sentinel-2 cloudless 2016** (`s2cloudless_3857`) | WMTS capabilities abstract (fetched 9 Nov 2026): "released under Creative Commons Attribution 4.0 International License". A tile request returned HTTP 200 `image/jpeg`. Later years (2017–2024) are **CC BY-NC-SA 4.0** | **Used** as the default satellite layer, with the required attribution: "Sentinel-2 cloudless – s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016)" |
| OpenStreetMap | ODbL, attribution required | Kept as an alternative layer |

**Scientific safeguard:** the 2016 cloud-free mosaic is a *location reference only*. The UI labels it "2016 cloud-free mosaic – not current crop condition", and it never feeds any assessment.

### 2.6 Accessibility (WCAG 2.2 AA)

- 1.4.3 text contrast ≥ 4.5:1; 1.4.11 non-text contrast ≥ 3:1; 2.5.8 target size ≥ 24 px (we use ≥ 44 px); 1.4.1 colour is never the only means.
- Every palette pair was computed before implementation:

| Pair | Ratio |
|---|---|
| Ink `#1B2A21` on page `#F7F5EF` | 13.76 |
| Muted `#56645A` on page | 5.72 |
| White on primary `#1F6B3A` | 6.52 |
| White on header `#143D24` | 12.19 |
| Status: possible / check / outside / blocked / unknown text on their washes | 6.33 / 6.53 / 6.28 / 6.55 / 7.12 |
| Rain blue `#1F5F9E` on white | 6.59 |
| Temperature `#B4472A` on white | 5.42 |
| Control border `#8A968C` on white | 3.08 |

Every status chip also carries an icon and a text label.

## 3. Design system: "Field & Soil"

| Token | Value | Use |
|---|---|---|
| `forest` | `#143D24` | App bar, hero overlay |
| `primary` | `#1F6B3A` | Primary actions, active navigation |
| `leaf` | `#3F8F55` | Accents, rain-supported months |
| `wheat` | `#F5EDDA` / gold `#C8962E` | Highlight surfaces, chosen season |
| `soil` | `#6B4F35` | Soil visuals, ET₀ line |
| `rain` | `#1F5F9E` | Rainfall |
| `sun` | `#B4472A` | Temperature |
| `page` | `#F7F5EF` | Warm paper background |
| `ink` / `muted` | `#1B2A21` / `#56645A` | Text |

Type: Inter (already bundled under the SIL OFL) with tabular numerals for metrics. Icons are inline SVG, so no external icon font is needed and pages work offline.

## 4. Automation added (all scientifically safe)

| Automation | Source | Safeguard |
|---|---|---|
| Satellite map preview appears as soon as a location is selected | EOX S2 cloudless 2016 | Location reference only, labelled with its date |
| Location snapshot (annual rain, mean temperature, rain-supported months, modelled soil pH) on the field and season steps | NASA POWER history already loaded; SoilGrids context already retrieved | Modelled pH is labelled "map estimate" and is never copied into the measured pH field |
| Suggested growing window | FAO LGP rule applied to the site's NASA climatology | Explicit button; labelled approximation; farmer can change it |
| FAO GAEZ class retrieved automatically for **both** rainfed and irrigated scenarios in crop details | Local verified GAEZ v5 rasters | Shown as ordinal model classes, never as probability or yield |
| Field-information completeness meter with "what to add next" prompts | Farmer inputs | Missing values stay unknown; the meter only guides data entry |
| Temperature-fit and pH-scale charts in crop details | Cited trait ranges and NASA climatology | Visualise existing comparisons only; no new score |

## 5. What was deliberately not done

- No browser geolocation: Streamlit has no first-party geolocation API, and a third-party JavaScript component would add an unaudited dependency.
- No NDVI or current-season satellite layer: no licence-clear, auth-free current imagery source was verified, and current vegetation does not feed the scientific engine.
- No crop photographs per card: there is no licence-verified image set for 107 crops. Category icons are used instead.
- No dark mode in this iteration: the field-sunlight use case favours the high-contrast light theme.

## 6. Sources

- Walter, H. & Lieth, H. (1967). *Klimadiagramm-Weltatlas*. VEB Gustav Fischer.
- FAO (1996). *Agro-ecological zoning guidelines*. FAO Soils Bulletin 73; FAO AEZ methodology (P ≥ 0.5 PET growing-period rule).
- Allen, R. G. et al. (1998). *FAO-56 Crop Evapotranspiration*, Eq. 52 (Hargreaves ET₀).
- FAO GIEWS country briefs and the FAO Crop Calendar platform (12-month calendar convention).
- FAO GAEZ v5 SIX style descriptor (official legend colours), fetched 9 Nov 2026.
- EOX IT Services, Sentinel-2 cloudless WMTS capabilities, fetched 9 Nov 2026 (2016 layer CC BY 4.0).
- W3C (2023). *Web Content Accessibility Guidelines 2.2*, SC 1.4.1, 1.4.3, 1.4.11, 2.5.8.
