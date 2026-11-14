"""AgroShift 'Field & Soil' agricultural design system and tokens."""

from urllib.parse import quote

TOKENS = {
    "ink": "#1B2A21",
    "muted": "#56645A",
    "forest": "#143D24",
    "primary": "#1F6B3A",
    "primary-hover": "#18562E",
    "leaf": "#3F8F55",
    "page": "#F7F5EF",
    "surface": "#FFFFFF",
    "wash": "#EFECE3",
    "wheat": "#F5EDDA",
    "gold": "#C8962E",
    "gold-ink": "#7A5A12",
    "soil": "#6B4F35",
    "soil-wash": "#F3ECE3",
    "rain": "#1F5F9E",
    "rain-wash": "#E8F1FA",
    "sun": "#B4472A",
    "sun-wash": "#FBEAE4",
    "blue": "#1F6B3A",
    "blue-hover": "#18562E",
    "blue-wash": "#E6F4EA",
    "green": "#17643A",
    "green-wash": "#E6F4EA",
    "line": "#D7DDD6",
    "control": "#8A968C",
    "warning": "#7A4D00",
    "warning-wash": "#FDF2D8",
    "outside": "#8C3D0E",
    "outside-wash": "#FBE7D8",
    "error": "#A11B1B",
    "error-wash": "#FCE6E6",
    "disabled": "#ECEFF1",
}

MARK = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44">'
    '<defs><linearGradient id="agG" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0%" stop-color="#1A5C34"/><stop offset="100%" stop-color="#0E331C"/></linearGradient></defs>'
    '<rect width="44" height="44" rx="12" fill="url(#agG)" stroke="#3F8F55" stroke-width="1"/>'
    '<circle cx="22" cy="22" r="14" fill="none" stroke="rgba(230,244,234,0.18)" stroke-width="1" stroke-dasharray="3 2"/>'
    '<path d="M9 33c7-1.5 19-1.5 26 0" stroke="#D9A336" stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M22 33V12" stroke="#E6F4EA" stroke-width="2.3" stroke-linecap="round"/>'
    '<path d="M22 25c-6.5 0-10.5-4.2-10.5-9.5 6.5 0 10.5 4.2 10.5 9.5Z" fill="#35A85A" stroke="#E6F4EA" stroke-width="1.3"/>'
    '<path d="M22 19.5c6.5 0 10.5-4.2 10.5-9.5-6.5 0-10.5 4.2-10.5 9.5Z" fill="#D9A336" stroke="#FFF8E7" stroke-width="1.3"/>'
    '<circle cx="22" cy="9" r="2" fill="#7CE89E"/>'
    "</svg>"
)

BRAND = (
    '<div class="as-brand" aria-label="AgroShift">'
    '<div>AgroShift<span>AI</span><small>PRECISION FIELD &amp; CROP INTELLIGENCE</small></div>'
    "</div>"
)

HERO = (
    '<section class="as-hero">'
    '<div class="as-hero-overlay">'
    '<p class="as-eyebrow">◈ SATELLITE TELEMETRY · SOIL PHYSICS · FAO CROP INTELLIGENCE</p>'
    '<h1>Smart crop decisions<br class="as-desktop-break"> rooted in your land.</h1>'
    "<p>Combine 25-year NASA satellite weather, ISRIC SoilGrids root-zone profiles, "
    "FAO GAEZ agro-ecological maps, and 107 reviewed crop references in a clean, field-ready workspace.</p>"
    '<div class="as-hero-badges">'
    '<span><b>25 yrs</b> NASA POWER daily climate</span>'
    '<span><b>107</b> global crops &amp; 295 traits</span>'
    '<span><b>48</b> FAO GAEZ v5 suitability maps</span>'
    '<span><b>250 m</b> SoilGrids &amp; FAO calendars</span>'
    "</div>"
    "</div>"
    "</section>"
)

HOME_SHOWCASE = (
    '<section class="as-showcase" aria-label="How AgroShift works">'
    '<div class="as-showcase-grid">'
    '<article class="as-feature-card">'
    '<div class="as-feature-head">'
    '<span class="as-feature-icon">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2"/></svg>'
    '</span>'
    '<div class="as-feature-num">01 · SATELLITE &amp; SOIL SENSING</div>'
    "</div>"
    "<h3>Pin your field on satellite imagery</h3>"
    "<p>Select any country, region, or field polygon worldwide. AgroShift automatically pulls 25 years of daily NASA weather, "
    "reference evapotranspiration (ET₀), and modelled topsoil pH.</p>"
    "</article>"
    '<article class="as-feature-card">'
    '<div class="as-feature-head">'
    '<span class="as-feature-icon as-feature-icon-blue">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 19h16"/><path d="M7 15v-5"/><path d="M12 15V7"/><path d="M17 15v-8"/><circle cx="12" cy="4" r="1.5"/></svg>'
    '</span>'
    '<div class="as-feature-num">02 · AGRO-CLIMATIC GROWING CALENDAR</div>'
    "</div>"
    "<h3>See rain-supported growing months</h3>"
    "<p>A Walter–Lieth climograph and FAO Length-of-Growing-Period detector highlight which months have sufficient rainfall "
    "versus evaporative demand—and let you apply the suggested season in one click.</p>"
    "</article>"
    '<article class="as-feature-card as-feature-photo">'
    '<div class="as-feature-head">'
    '<span class="as-feature-icon as-feature-icon-gold">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 2L4 6v6c0 5.5 3.4 10.3 8 12 4.6-1.7 8-6.5 8-12V6l-8-4Z"/><path d="m9 12 2 2 4-4"/></svg>'
    '</span>'
    '<div class="as-feature-num">03 · TRANSPARENT SCIENTIFIC SCREENING</div>'
    "</div>"
    "<h3>Compare crops, rotations &amp; GAEZ maps</h3>"
    "<p>Every crop card separates measured field data from satellite/model estimates, checks thermal, water, soil, and pest risks, "
    "and cross-checks FAO GAEZ v5 rainfed &amp; irrigated land classes.</p>"
    "</article>"
    "</div>"
    "</section>"
)

STYLE = (
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');"
    ":root{"
    + "".join("--" + k + ":" + v + ";" for k, v in TOKENS.items())
    + "}</style>"
)

STYLE += """
<style>
[data-testid=stAppViewContainer]{
    background:radial-gradient(circle at 15% 0%, #F1F6F2 0%, #F7F5EF 52%, #F3F0E6 100%);
    font-family:'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, .as-brand, .as-hero h1, .as-card h2{
    font-family:'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
[data-testid=stMainBlockContainer]{max-width:1320px;padding:1.4rem 2rem 4rem}
header[data-testid=stHeader]{height:0;background:transparent}
.st-key-app_shell [data-testid=stCaptionContainer]{color:var(--muted);opacity:1}
.st-key-app_shell [data-testid=stCaptionContainer] p{color:inherit;opacity:1}
.st-key-app_shell{max-width:1260px;margin-inline:auto;font-variant-numeric:tabular-nums}
.st-key-app_header{
    align-items:center;
    background:linear-gradient(135deg, #0E2F1B 0%, #174B2B 55%, #1E6138 100%);
    border:1px solid #0B2616;
    border-radius:18px;
    padding:13px 22px!important;
    margin-bottom:24px;
    gap:20px!important;
    box-shadow:0 10px 28px rgba(14,47,27,0.16), inset 0 1px 0 rgba(255,255,255,0.12);
}
.st-key-navigation{gap:6px!important}
.st-key-navigation button{
    font-weight:600;
    border:1px solid transparent!important;
    border-radius:10px!important;
    padding-inline:15px!important;
    font-size:14px;
    color:#E6F4EA!important;
    background:rgba(255,255,255,0.06)!important;
}
.st-key-navigation button:hover{
    background:rgba(255,255,255,0.15)!important;
    color:#FFFFFF!important;
}
.st-key-navigation button p{font-size:14px;white-space:normal;overflow:visible;color:inherit!important}
.st-key-navigation button[kind=primary]{
    background:#F5EDDA!important;
    color:#143D24!important;
    border-color:#C8962E!important;
    box-shadow:0 2px 8px rgba(0,0,0,0.16);
}
.st-key-navigation button[kind=primary] p{color:#143D24!important;font-weight:700}
.st-key-navigation button[kind=primary]:hover{background:#FFF8E7!important;color:#0E2D1A!important}
.st-key-farm_context button{
    background:rgba(245,237,218,0.14)!important;
    color:#FFF8E7!important;
    border:1px solid rgba(200,150,46,0.55)!important;
    border-radius:999px!important;
    padding-inline:14px!important;
}
.st-key-farm_context button p,.st-key-farm_context button span{color:#FFF8E7!important}
.st-key-app_shell button{min-height:44px;font-weight:600}
.st-key-app_shell button:focus-visible,.st-key-app_shell a:focus-visible,.st-key-app_shell summary:focus-visible{
    outline:3px solid var(--gold)!important;outline-offset:3px
}
.as-brand{display:flex;align-items:center;gap:12px;font-size:21px;font-weight:750;letter-spacing:-.5px;color:#FFFFFF;white-space:nowrap;min-height:44px}
.as-brand::before{content:"";width:38px;height:38px;flex-shrink:0;background:center/contain no-repeat url("data:image/svg+xml,BRAND_DATA")}
.as-brand div{display:flex;flex-direction:column;line-height:1.1}
.as-brand span{font-size:11px;letter-spacing:.08em;color:#F5EDDA;background:rgba(200,150,46,0.32);padding:2px 6px;border-radius:5px;font-weight:700;margin-left:6px;vertical-align:middle}
.as-brand small{font-size:10px;letter-spacing:.12em;color:#B8D8C2;font-weight:600;margin-top:3px}

/* Hero Banner */
.as-hero{
    position:relative;
    border-radius:20px;
    overflow:hidden;
    background:#143D24 url("app/static/hero-fields.webp") center/cover no-repeat;
    border:1px solid #143D24;
    box-shadow:0 14px 36px rgba(20,42,28,0.16);
    margin-bottom:14px;
}
.as-hero-overlay{
    padding:46px 44px;
    background:linear-gradient(95deg, rgba(14,42,24,0.93) 0%, rgba(20,61,36,0.84) 52%, rgba(20,61,36,0.32) 100%);
    color:#FFFFFF;
}
.as-eyebrow{
    display:inline-block;
    font-size:11.5px;
    font-weight:700;
    letter-spacing:.11em;
    color:#F5EDDA;
    background:rgba(200,150,46,0.28);
    border:1px solid rgba(245,237,218,0.35);
    padding:5px 11px;
    border-radius:999px;
    margin:0 0 16px;
}
.as-hero h1{
    font-size:44px;
    line-height:1.12;
    letter-spacing:-1.2px;
    font-weight:750;
    margin:0 0 16px;
    max-width:680px;
    color:#FFFFFF;
}
.as-hero-overlay>p{
    font-size:17px;
    color:#E4EFE7;
    line-height:1.6;
    max-width:630px;
    margin:0 0 24px;
}
.as-hero-badges{
    display:flex;
    flex-wrap:wrap;
    gap:10px;
}
.as-hero-badges span{
    background:rgba(255,255,255,0.12);
    backdrop-filter:blur(6px);
    border:1px solid rgba(255,255,255,0.22);
    color:#F7F5EF;
    font-size:13px;
    padding:6px 12px;
    border-radius:9px;
}
.as-hero-badges b{color:#F5EDDA;font-weight:700}

/* Home Feature Showcase */
.as-showcase{margin:18px 0 8px}
.as-showcase-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
.as-feature-card{
    background:var(--surface);
    border:1px solid var(--line);
    border-top:4px solid var(--primary);
    border-radius:16px;
    padding:22px 22px 20px;
    box-shadow:0 6px 18px rgba(27,42,33,0.06);
    transition:transform .16s ease, box-shadow .16s ease;
}
.as-feature-card:hover{
    transform:translateY(-2px);
    box-shadow:0 12px 26px rgba(27,42,33,0.10);
}
.as-feature-head{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.as-feature-icon{
    width:34px;
    height:34px;
    border-radius:9px;
    background:#E6F4EA;
    border:1px solid #B7DFC2;
    color:#17643A;
    display:inline-grid;
    place-content:center;
    flex-shrink:0;
}
.as-feature-icon svg{width:19px;height:19px}
.as-feature-icon-blue{background:#E8F1FA;border-color:#B4D2F0;color:#1F5F9E}
.as-feature-icon-gold{background:rgba(245,237,218,0.20);border-color:rgba(245,237,218,0.45);color:#F5EDDA}
.as-feature-card.as-feature-photo{
    background:linear-gradient(180deg, rgba(16,52,30,0.88) 0%, rgba(14,43,25,0.95) 100%), url("app/static/seedlings.webp") center/cover no-repeat;
    color:#FFFFFF;
    border-top-color:var(--gold);
}
.as-feature-card.as-feature-photo h3{color:#FFFFFF}
.as-feature-card.as-feature-photo p{color:#DCEBE0}
.as-feature-card.as-feature-photo .as-feature-num{color:#F5EDDA;margin-bottom:0}
.as-feature-num{font-size:11px;font-weight:700;letter-spacing:.09em;color:var(--primary);margin-bottom:0;font-family:'JetBrains Mono','Inter',monospace}
.as-feature-card h3{font-size:18px;font-weight:700;color:var(--ink);margin:0 0 8px;letter-spacing:-.2px}
.as-feature-card p{font-size:14px;line-height:1.55;color:var(--muted);margin:0}

.st-key-home_actions{margin-top:12px;margin-bottom:8px;gap:12px!important}
.as-caption{font-size:14px;line-height:1.55;color:var(--muted);margin:4px 0}

/* Context & KPI Strips */
.as-context,.ag-context-bar{
    display:flex;
    flex-wrap:wrap;
    gap:14px 28px;
    background:linear-gradient(90deg, #FFFFFF 0%, #FAF8F2 100%);
    border:1px solid var(--line);
    border-left:5px solid var(--primary);
    border-radius:14px;
    padding:15px 22px!important;
    margin:8px 0 14px;
    box-shadow:0 3px 12px rgba(27,42,33,0.05);
}
.as-context>div,.ag-context-bar>div{min-width:0;display:flex;flex-direction:column;gap:2px}
.as-context dt,.ag-context-bar small{font-size:11px;text-transform:uppercase;letter-spacing:.07em;font-weight:700;color:var(--muted);margin-bottom:2px}
.as-context dd,.ag-context-bar strong{font-size:15px;color:var(--ink);font-weight:700;margin:0;overflow-wrap:anywhere}
.ag-card{
    background:linear-gradient(135deg, #FFFFFF 0%, #F7FAF8 100%);
    border:1px solid #CFE0D4;
    border-left:5px solid var(--primary);
    border-radius:14px;
    padding:14px 18px;
    margin:8px 0 16px;
    box-shadow:0 3px 12px rgba(27,42,33,0.05);
    color:var(--ink);
}

/* Explore Categorized Hub Strip */
.as-explore-hub{
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:10px;
    margin:6px 0 12px;
}
.as-hub-cat{
    background:var(--surface);
    border:1px solid var(--line);
    border-top:3px solid #B7C4B9;
    border-radius:12px;
    padding:10px 13px;
}
.as-hub-cat.as-hub-active,.as-hub-cat.as-hub-cat-active{
    background:linear-gradient(180deg, #EAF6EE 0%, #FFFFFF 100%);
    border-color:#98CEA8;
    border-top:3px solid var(--primary);
    box-shadow:0 3px 10px rgba(31,107,58,0.08);
}
.as-hub-cat small{
    display:block;
    font-size:10.5px;
    font-weight:700;
    letter-spacing:.08em;
    text-transform:uppercase;
    color:var(--primary);
    font-family:'JetBrains Mono','Inter',monospace;
    margin-bottom:3px;
}
.as-hub-cat strong{
    display:block;
    font-size:13.5px;
    color:var(--ink);
    margin-bottom:2px;
}
.as-hub-cat span{
    display:block;
    font-size:12px;
    color:var(--muted);
    line-height:1.35;
}

/* Automated Site Intelligence Banner & KPI Tiles */
.as-intel-panel{
    background:linear-gradient(180deg, #FFFFFF 0%, #F9F7F1 100%);
    border:1px solid var(--line);
    border-radius:16px;
    padding:18px 20px;
    margin:10px 0 18px;
    box-shadow:0 4px 16px rgba(27,42,33,0.05);
}
.as-intel-header{
    display:flex;
    flex-wrap:wrap;
    justify-content:space-between;
    align-items:center;
    gap:8px;
    margin-bottom:12px;
}
.as-intel-title{
    display:flex;
    align-items:center;
    gap:8px;
    font-size:13px;
    font-weight:700;
    letter-spacing:.06em;
    text-transform:uppercase;
    color:var(--forest);
}
.as-intel-badge{
    font-size:12px;
    font-weight:600;
    padding:3px 10px;
    border-radius:999px;
    background:var(--green-wash);
    color:var(--green);
    border:1px solid #B7DFC2;
    font-family:'JetBrains Mono','Inter',monospace;
}
.as-kpi-grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
    gap:12px;
}
.as-kpi-tile{
    background:var(--surface);
    border:1px solid var(--line);
    border-top:3px solid var(--primary);
    border-radius:12px;
    padding:12px 14px;
    box-shadow:0 2px 6px rgba(27,42,33,0.03);
}
.as-kpi-tile.as-kpi-rain{border-top-color:var(--rain)}
.as-kpi-tile.as-kpi-temp{border-top-color:var(--sun)}
.as-kpi-tile.as-kpi-season{border-top-color:var(--primary)}
.as-kpi-tile.as-kpi-soil{border-top-color:var(--soil)}
.as-kpi-tile .as-kpi-label{
    font-size:11.5px;
    font-weight:650;
    color:var(--muted);
    margin-bottom:4px;
    display:flex;
    align-items:center;
    gap:6px;
}
.as-kpi-tile .as-kpi-label svg{width:15px;height:15px;flex-shrink:0}
.as-kpi-tile .as-kpi-value{
    font-size:20px;
    font-weight:750;
    color:var(--ink);
    line-height:1.2;
    font-family:'Plus Jakarta Sans','Inter',sans-serif;
}
.as-kpi-tile .as-kpi-sub{
    font-size:12px;
    color:var(--muted);
    margin-top:3px;
}

/* 12-Month Agro-Climatic Calendar Strip */
.as-cal-wrap{
    background:var(--surface);
    border:1px solid var(--line);
    border-radius:15px;
    padding:16px 18px;
    margin:10px 0 16px;
}
.as-cal-head{
    display:flex;
    flex-wrap:wrap;
    justify-content:space-between;
    align-items:center;
    gap:8px;
    margin-bottom:10px;
}
.as-cal-head strong{font-size:14px;color:var(--ink)}
.as-cal-legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--muted)}
.as-cal-legend span{display:inline-flex;align-items:center;gap:5px}
.as-cal-dot{width:10px;height:10px;border-radius:3px;display:inline-block}
.as-cal-strip{
    display:grid;
    grid-template-columns:repeat(12,minmax(0,1fr));
    gap:6px;
}
.as-cal-cell{
    border:1px solid var(--line);
    border-radius:10px;
    padding:8px 4px 6px;
    text-align:center;
    background:#FAFAF7;
    position:relative;
}
.as-cal-cell.as-cal-supported{
    background:var(--green-wash);
    border-color:#95CFA6;
}
.as-cal-cell.as-cal-selected{
    box-shadow:inset 0 0 0 2px var(--gold), 0 2px 6px rgba(200,150,46,0.22);
    background:var(--wheat);
    border-color:var(--gold);
}
.as-cal-cell.as-cal-supported.as-cal-selected{
    background:linear-gradient(180deg, #E6F4EA 0%, #F5EDDA 100%);
    border-color:var(--primary);
    box-shadow:inset 0 0 0 2px var(--primary);
}
.as-cal-m{font-size:12px;font-weight:700;color:var(--ink);display:block}
.as-cal-rain{font-size:11px;color:var(--rain);font-weight:650;display:block;margin-top:2px}
.as-cal-temp{font-size:10.5px;color:var(--muted);display:block}
.as-cal-bar-track{height:4px;background:#E2E8F0;border-radius:2px;margin:5px 4px 2px;overflow:hidden}
.as-cal-bar-fill{height:100%;background:var(--rain);border-radius:2px}

/* Status Chips (Icon + High-Contrast Color + Text) */
.as-status{
    display:inline-flex;
    align-items:center;
    gap:6px;
    font-size:12px;
    line-height:1.35;
    padding:5px 11px;
    border-radius:999px;
    font-weight:700;
    background:#ECEFF1;
    color:#46505A;
    border:1px solid #CFD6DC;
    margin-bottom:10px;
}
.as-status-possible{color:#145E34;background:#E3F5E9;border-color:#9AD2AC}
.as-status-check{color:#7A4D00;background:#FFF3D6;border-color:#E7C77F}
.as-status-outside{color:#8C3D0E;background:#FBE7D8;border-color:#E8B490}
.as-status-blocked{color:#A11B1B;background:#FCE6E6;border-color:#E5A3A3}

/* Crop Cards & Vibrant Botanical Group Avatars */
.as-card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.as-crop-avatar{
    width:46px;
    height:46px;
    border-radius:13px;
    background:var(--wheat);
    border:1px solid #E2D4B5;
    display:inline-grid;
    place-content:center;
    color:var(--forest);
    flex-shrink:0;
    box-shadow:0 2px 6px rgba(27,42,33,0.06);
}
.as-crop-avatar svg{width:25px;height:25px}
.as-avatar-cereal{background:linear-gradient(135deg,#FDF3DC 0%,#F5E3B8 100%);border-color:#DFC078;color:#78510B}
.as-avatar-legume{background:linear-gradient(135deg,#E3F6EB 0%,#C8ECD6 100%);border-color:#94D1AC;color:#145A32}
.as-avatar-root{background:linear-gradient(135deg,#F9EBE2 0%,#EED4C3 100%);border-color:#D8AC91;color:#733617}
.as-avatar-oilseed{background:linear-gradient(135deg,#FEF6DB 0%,#F7E2A4 100%);border-color:#E2BE5F;color:#7C5800}
.as-avatar-vegetable{background:linear-gradient(135deg,#E6F5EC 0%,#FCE9DF 100%);border-color:#C5DEC9;color:#1D5B38}
.as-avatar-fruit{background:linear-gradient(135deg,#FDECE6 0%,#F9D5C8 100%);border-color:#E6AA94;color:#882914}
.as-card h2{font-size:20px;line-height:1.25;letter-spacing:-.3px;font-weight:750;margin:2px 0 4px;padding:0;color:var(--ink)}
.as-card .as-category{font-size:13px;color:var(--muted);font-weight:550;margin:0 0 14px}
.as-card-reason{font-size:13.5px;line-height:1.5;color:var(--ink);background:#F8F7F2;border-radius:10px;padding:10px 13px;margin:0 0 12px;border:1px solid #E5E1D6;border-left:3px solid var(--primary)}
.as-findings{margin:0;padding:0!important}
.as-findings>div{display:grid;grid-template-columns:116px minmax(0,1fr);gap:12px;padding:9px 0;border-top:1px solid var(--line);font-size:13.5px;line-height:1.45;align-items:center}
.as-findings dt{color:var(--muted);font-weight:600;display:flex;align-items:center;gap:6px}
.as-findings dd{margin:0;color:var(--ink);font-weight:550;overflow-wrap:anywhere}
.as-f-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}
.as-f-dot-ok{background:#1F7A44;box-shadow:0 0 0 2px #D9F2E2}
.as-f-dot-wait{background:#C88A1E;box-shadow:0 0 0 2px #F9E8C2}
.as-constraint{
    border-left:4px solid var(--warning);
    background:var(--warning-wash);
    border-radius:0 8px 8px 0;
    padding:10px 12px;
    font-size:13.5px;
    line-height:1.5;
    margin:12px 0;
    color:#694100;
    font-weight:550;
}
.as-unknown{font-size:12.5px;line-height:1.55;color:var(--muted);margin:12px 0 0;padding-top:8px;border-top:1px dashed var(--line)}

/* Grids & Containers */
.st-key-crop_grid,.st-key-farm_grid,.st-key-dashboard_grid{
    display:grid!important;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:20px!important;
    align-items:stretch;
}
.st-key-crop_grid>div,.st-key-farm_grid>div,.st-key-dashboard_grid>div{width:100%!important;min-width:0;border-color:var(--line)!important}
.st-key-crop_grid>div>div,.st-key-farm_grid>div>div,.st-key-dashboard_grid>div>div,.st-key-compare_grid>div>div{
    background:var(--surface)!important;
    border-radius:16px!important;
    border:1px solid var(--line)!important;
    box-shadow:0 4px 16px rgba(27,42,33,0.05);
    height:100%;
    transition:transform .15s ease, box-shadow .15s ease;
}
.st-key-crop_grid>div>div:hover{
    box-shadow:0 8px 24px rgba(27,42,33,0.10);
}
.st-key-crop_grid>div>div{padding:22px!important}
.st-key-compare_grid{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px!important}
.st-key-compare_grid>div{width:100%!important;min-width:0;border-color:var(--line)!important}
.st-key-compare_grid .as-findings>div{display:block;min-height:84px}
.st-key-compare_grid dt{margin-bottom:6px}
.st-key-form_shell{max-width:880px;margin-inline:auto}

/* Wizard Stepper */
.as-steps{display:flex;gap:10px;padding:0!important;margin:0 0 22px;list-style:none}
.as-steps li{
    display:flex;
    gap:10px;
    align-items:center;
    font-size:14px;
    color:var(--muted);
    flex:1;
    background:var(--surface);
    border:1px solid var(--line);
    border-bottom:3px solid var(--line);
    border-radius:12px;
    padding:10px 14px;
    font-weight:550;
}
.as-steps li[aria-current=step]{
    color:var(--forest);
    background:var(--green-wash);
    border-color:#A5D6B2;
    border-bottom:3px solid var(--primary);
    font-weight:700;
}
.as-steps b{
    display:inline-grid;
    place-content:center;
    width:26px;
    height:26px;
    border-radius:50%;
    font-size:12.5px;
    background:var(--wash);
    color:var(--ink);
    font-weight:700;
}
.as-steps li[aria-current=step] b{background:var(--primary);color:#FFFFFF}

/* GAEZ 8-class Suitability Bar & Range Gauges */
.as-gauge-card{
    background:var(--surface);
    border:1px solid var(--line);
    border-radius:14px;
    padding:16px 18px;
    margin:10px 0;
}
.as-gauge-title{font-size:13.5px;font-weight:700;color:var(--ink);margin:0 0 8px;display:flex;justify-content:space-between;align-items:center}
.as-gaez-scale{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:4px;margin:8px 0}
.as-gaez-step{
    border-radius:6px;
    padding:6px 3px;
    text-align:center;
    font-size:10.5px;
    font-weight:700;
    line-height:1.15;
    opacity:0.38;
    border:1px solid rgba(0,0,0,0.12);
}
.as-gaez-step.as-gaez-active{
    opacity:1;
    transform:scale(1.04);
    box-shadow:0 0 0 2px var(--ink), 0 3px 8px rgba(0,0,0,0.18);
}
.as-range-track{
    position:relative;
    height:14px;
    background:#ECEAE2;
    border-radius:999px;
    margin:10px 0 6px;
    overflow:hidden;
    border:1px solid var(--line);
}
.as-range-band{
    position:absolute;
    top:0;
    bottom:0;
    background:rgba(31,107,58,0.28);
    border-left:2px solid var(--primary);
    border-right:2px solid var(--primary);
}
.as-range-marker{
    position:absolute;
    top:-2px;
    bottom:-2px;
    width:6px;
    border-radius:3px;
    background:var(--sun);
    box-shadow:0 0 0 2px #FFFFFF;
}

.as-empty{
    padding:36px 28px;
    background:var(--surface);
    border:1px dashed var(--control);
    border-radius:16px;
    max-width:620px;
}
.as-empty h2{font-size:22px;margin:0 0 10px;color:var(--ink)}
.as-empty p{font-size:15.5px;line-height:1.6;color:var(--muted);margin:0}
.as-farm-title{font-size:20px;margin:0 0 4px;line-height:1.35;color:var(--ink);font-weight:720}
.as-farm-meta{font-size:13.5px;line-height:1.55;color:var(--muted);margin:0 0 10px}

/* Rotation Succession Pill on Crop Cards */
.as-rot-pill{
    display:inline-flex;
    align-items:center;
    gap:5px;
    font-size:11.5px;
    font-weight:650;
    padding:4px 9px;
    border-radius:7px;
    margin:0 0 10px;
}
.as-rot-legume_benefit,.as-rot-good{background:#E6F4EA;color:#17643A;border:1px solid #A5D6B2}
.as-rot-caution{background:#FDF2D8;color:#7A4D00;border:1px solid #E7C77F}
.as-rot-blocked{background:#FCE6E6;color:#A11B1B;border:1px solid #E5A3A3}

/* 12-Month × Crop Sowing Heatmap Matrix */
.as-matrix-table{width:100%;border-collapse:separate;border-spacing:4px;font-size:12px;margin:8px 0}
.as-matrix-table th{font-size:11px;font-weight:700;color:var(--muted);text-align:center;padding:4px 2px}
.as-matrix-table th:first-child{text-align:left;padding-left:6px}
.as-matrix-crop{font-weight:650;color:var(--ink);padding:6px 8px;background:#FAFAF7;border-radius:7px;border:1px solid var(--line);white-space:nowrap}
.as-matrix-crop small{display:block;font-size:10.5px;color:var(--muted);font-weight:500}
.as-mcell{text-align:center;padding:6px 2px;border-radius:6px;font-weight:700;font-size:11px;border:1px solid transparent}
.as-mcell-optimal{background:#E6F4EA;color:#17643A;border-color:#A5D6B2}
.as-mcell-needs_water{background:#E8F1FA;color:#1F5F9E;border-color:#B4D2F0}
.as-mcell-marginal{background:#FDF2D8;color:#7A4D00;border-color:#E7C77F}
.as-mcell-outside{background:#F3F4F6;color:#6B7280;border-color:#E5E7EB}

/* 4-Stage FAO-56 Water Demand Bars */
.as-stage-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0}
.as-stage-card{background:#FAFAF7;border:1px solid var(--line);border-radius:11px;padding:11px 12px}
.as-stage-card strong{display:block;font-size:12.5px;color:var(--ink);margin-bottom:4px}
.as-stage-meta{font-size:11.5px;color:var(--muted);margin-bottom:8px}
.as-dual-bar{display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600}
.as-bar-row{display:flex;align-items:center;gap:6px}
.as-bar-track2{flex:1;height:7px;background:#E5E7EB;border-radius:4px;overflow:hidden}
.as-bar-etc{height:100%;background:var(--soil);border-radius:4px}
.as-bar-rain{height:100%;background:var(--rain);border-radius:4px}

/* 6-Layer Evidence Scorecard */
.as-layer-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:8px 0}
.as-layer-item{background:#FAFAF7;border:1px solid var(--line);border-left:4px solid var(--primary);border-radius:10px;padding:10px 12px}
.as-layer-item h4{font-size:12.5px;font-weight:700;color:var(--forest);margin:0 0 4px}
.as-layer-item p{font-size:12.5px;color:var(--ink);margin:0;line-height:1.45}

@media(max-width:1100px){
    .st-key-app_header{gap:14px!important}
    .st-key-farm_context{display:none!important}
    .as-showcase-grid{grid-template-columns:1fr}
}
@media(max-width:760px){
    [data-testid=stMainBlockContainer]{padding:1rem 1rem 3rem}
    .st-key-app_header{display:block!important;padding:14px!important;margin-bottom:18px}
    .st-key-navigation{display:grid!important;grid-template-columns:1fr 1fr;gap:6px!important;margin-top:12px}
    .st-key-navigation>div{width:100%!important}
    .st-key-navigation button{width:100%;font-size:13.5px;padding-inline:8px!important}
    .st-key-crop_grid,.st-key-farm_grid,.st-key-dashboard_grid,.st-key-compare_grid{grid-template-columns:1fr!important;gap:14px!important}
    .as-hero-overlay{padding:28px 22px}
    .as-hero h1{font-size:32px;letter-spacing:-.8px;line-height:1.15}
    .as-hero-overlay>p{font-size:15.5px}
    .as-cal-strip{grid-template-columns:repeat(6,minmax(0,1fr))}
    .as-gaez-scale{grid-template-columns:repeat(4,minmax(0,1fr))}
    .as-steps{flex-direction:column;gap:8px}
    .st-key-home_actions>div:first-child{width:100%!important}
    .st-key-home_actions>div:first-child button{width:100%}
}
@media(prefers-reduced-motion:reduce){
    .st-key-app_shell *{scroll-behavior:auto!important;animation-duration:.01ms!important;transition-duration:.01ms!important}
}
</style>
""".replace("BRAND_DATA", quote(MARK, safe=""))
