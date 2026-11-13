# TERRAFORGE AGRO

A front-end agricultural decision-support prototype for planning and optimizing crop production across a selected territory. The app combines a country selection flow, interactive parcel demarcation, crop strategy planning, and agronomic prioritization to generate an industrial-style recommendation dashboard.

## Overview

TERRAFORGE AGRO is a static web application built for exploring field-level agricultural planning. Users can:

- choose a country or region
- draw a field parcel boundary on a satellite map
- select a crop strategy or rotation plan
- configure irrigation, equipment, and market assumptions
- tune water, soil, income, erosion, and forage priorities
- review simulated agronomic outputs and recommendations

The project is designed as a polished prototype and is intentionally front-end focused, with no backend service required for local use.

## Features

- Interactive geodesic parcel drawing with Leaflet
- Satellite and vector map layers for agricultural field planning
- Region-based country selection and workflow navigation
- Crop strategy selection for current crop, rotation, or fallow scenarios
- Farm constraint inputs for irrigation, machinery, and market targets
- Weighted priority sliders for agronomic optimization
- Simulation-oriented output panels for industrial planning decisions
- Responsive Apple-style UI with a modern dashboard aesthetic

## Tech stack

- HTML5
- CSS3
- Vanilla JavaScript
- Leaflet for GIS map rendering
- ArcGIS/Esri basemaps for satellite imagery
- Google Fonts (Inter)

## Project structure

```text
nasa-app-challege/
├── frontend/
│   ├── index.html                 # Landing page
│   ├── pages/
│   │   └── input.html             # Main workflow interface
│   ├── css/
│   │   └── styles.css             # Shared styling and UI theme
│   ├── js/
│   │   ├── app.js                 # App-level logic
│   │   ├── pages/
│   │   │   ├── landing.js         # Landing page interactions
│   │   │   └── input.js           # Input-state/data workflow
│   │   └── modules/
│   │       ├── crop.js           # Crop database and logic
│   │       ├── workflow.js        # GIS + workflow engine
│   │       └── ...
│   ├── userData.json              # Example configuration payload
│   └── ...
├── README.md
└── .gitignore
```

## Run locally

Because this is a static front-end project, you can run it with any simple local web server.

### Option 1: Python

From the project root:

```bash
cd "C:\Users\aksek\Documents\nasa app\nasa-app-challege"
python -m http.server 8000
```

Then open:

- http://localhost:8000/frontend/
- or http://localhost:8000/frontend/pages/input.html

### Option 2: VS Code Live Server / other static server

Open the project in VS Code and launch the `frontend/index.html` file with a static preview extension such as Live Server.

## Notes

- The application depends on internet access for map tiles and CDN assets.
- This is a prototype and not yet connected to a real backend or database.
- User and crop data are handled in frontend JavaScript and example JSON payloads.

## Intended workflow

1. Start on the landing page and choose a country.
2. Move to the field demarcation step and draw a parcel polygon.
3. Select crop strategy and season configuration.
4. Set farm constraints and optimization priorities.
5. Review the generated agronomic synthesis.

## Example use case

The prototype is suitable for exploring:

- crop rotation planning
- water-use optimization
- soil health tradeoffs
- risk-aware crop selection for a given parcel
- precision agriculture concept demonstration

## Future enhancements

Potential extensions for the next iteration include:

- real API-driven weather and soil data
- export of recommendations as PDF/CSV
- user authentication and persistent saved projects
- backend integration for analytics and optimization models
- enhanced validation and geospatial accuracy checks
