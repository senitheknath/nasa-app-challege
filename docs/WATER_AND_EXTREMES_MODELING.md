# Evapotranspiration, Crop Water Balance, and Extreme Weather Modeling

**Date:** 2026-11-09  
**Scope:** Section 8 (`Evapotranspiration and Crop Water Balance`) & Section 9 (`Extreme Weather and Growing-Stage Risk`)

---

## 1. Reference Evapotranspiration ($ET_0$) (`agroshift/water_balance.py`, `agroshift/climate.py`)

### 1.1 Dual-Method FAO-56 Implementation (`compute_fao56_penman_monteith_daily`)
Following FAO Irrigation and Drainage Paper 56 (Allen et al., 1998):
1. **FAO-56 Penman-Monteith (Eq. 6 — Primary when wind, radiation, and humidity are available):**
   $$ET_{0,\text{PM}} = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T_{\text{mean}} + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$
   - Extraterrestrial radiation $R_a$ (Eq. 21–25), clear-sky radiation $R_{so} = (0.75 + 2 \times 10^{-5} z) R_a$ (Eq. 37), net shortwave $R_{ns} = 0.77 R_s$ (Eq. 38), net longwave $R_{nl}$ (Eq. 39), and daily soil heat flux $G = 0$ (Eq. 42).
   - Vapour pressure deficit $e_s - e_a$ from $T_{\max}$, $T_{\min}$, and `T2MDEW` (Eq. 14) or `RH2M` (Eq. 19).
   - 2 m wind speed $u_2$ from `WS2M` or logarithmic profile conversion from `WS10M` (Eq. 47: $u_2 = 0.748 u_{10}$).
   - Psychrometric constant $\gamma = 0.000665 P$ from `PS` or elevation barometric formula (Eq. 7–8).
2. **FAO-56 Hargreaves Fallback (Eq. 52 — Automatic when wind speed is absent):**
   $$ET_{0,\text{Hargreaves}} = 0.0023 (T_{\text{mean}} + 17.8) \sqrt{\max(T_{\max} - T_{\min}, 0)} \, (0.408 R_a)$$
- Every daily and seasonal output explicitly records `et0_method` (`"fao56_penman_monteith"`, `"fao56_hargreaves"`, or `"mixed_pm_hargreaves"`).

---

## 2. Daily Stage-Specific Crop Water Balance (`simulate_season_crop_water_balance`)

1. **Four-Stage Piecewise-Linear $K_c$ Curve (`build_daily_kc_curve`):**
   - Divides the growing window into `initial` (constant $K_{c,\text{ini}}$), `development` (linear ramp $K_{c,\text{ini}} \to K_{c,\text{mid}}$), `mid_season` (constant $K_{c,\text{mid}}$), and `late_season` (linear decline $K_{c,\text{mid}} \to K_{c,\text{end}}$) using reviewed FAO-56 Table 11/12 parameters stored in `ag_growth_stage`.
2. **Root-Zone Depletion & Water Stress Coefficient ($K_s$, FAO-56 Eq. 82–85):**
   - Total Available Water $\text{TAW}(t) = Z_r(t) \times \text{AWC}$, where rooting depth $Z_r(t)$ progresses from $0.30 Z_{r,\max}$ at establishment to $Z_{r,\max}$ at canopy closure.
   - Readily Available Water $\text{RAW}(t) = p_{\text{adj}}(t) \times \text{TAW}(t)$, with $p_{\text{adj}} = \text{clip}(p + 0.04(5 - ET_c), 0.10, 0.80)$ (FAO-56 Table 22 note).
   - Water stress coefficient:
     $$K_s(t) = \begin{cases} 1.0 & \text{if } D_r(t) \le \text{RAW}(t) \\ \frac{\text{TAW}(t) - D_r(t)}{\text{TAW}(t) - \text{RAW}(t)} & \text{if } D_r(t) > \text{RAW}(t) \end{cases}$$
   - Actual crop evapotranspiration $ET_{c,\text{adj}}(t) = K_s(t) \times K_c(t) \times ET_0(t)$.
3. **Bunded Paddy Rice Water Balance (`is_paddy=True`):**
   - Explicitly separates land soaking/puddling water requirement (`paddy_land_prep_mm`, default 175 mm) and daily percolation/seepage (`paddy_percolation_mm_day`, default 3.0 mm/day) from standard unsaturated root-zone depletion.

---

## 3. Multi-Year Extreme Weather & Stage-Specific Risk (`agroshift/extremes.py`)

`summarize_historical_extremes` computes multi-year seasonal distributions across all complete historical seasons:
- **Thermal Time (GDD):** $\sum \max(0, \min(T_{\text{mean}}, T_{\text{upper}}) - T_{\text{base}})$ using crop-specific base temperatures ($5^\circ\text{C}$ for cool-season cereals/pulses, $10^\circ\text{C}$ for warm-season cereals/legumes, $12^\circ\text{C}$ for cotton/sugarcane).
- **Frost Hazard:** Days with $T_{\min} < 0^\circ\text{C}$, severe frost days ($T_{\min} < -2^\circ\text{C}$), and fraction of historical seasons experiencing frost.
- **Heat-Stress Hazard:** Days exceeding crop-specific maximum temperature thresholds ($32^\circ\text{C}$ for cool-season/reproductive-sensitive crops, $35^\circ\text{C}$ general threshold), longest consecutive heat-wave run, and fraction of seasons affected.
- **Drought / Dry-Spell Hazard:** Median, 75th percentile, and maximum Consecutive Dry Days ($\text{CDD} < 1\text{ mm/day}$), plus fraction of seasons with $\text{CDD} \ge 10$ and $\ge 15$ days.
- **Heavy Rainfall & Waterlogging Hazard:** Days with $\ge 25\text{ mm}$ and $\ge 50\text{ mm}$ precipitation, plus maximum 1-day (`Rx1day`) and 3-day (`Rx3day`) cumulative rainfall.
- **Stage-Specific vs. Whole-Window Safeguard:**
  - When `sowing_date_confirmed=True` (farmer-confirmed or calendar-matched sowing window), `reproductive_stage_summary` isolates flowering/mid-season heat, frost, and dry-spell exposure.
  - When `sowing_date_confirmed=False`, `stage_specific_mode` is set to `"general_seasonal_exposure_only"` so unconfirmed sowing dates never fabricate stage-specific flowering timing.
