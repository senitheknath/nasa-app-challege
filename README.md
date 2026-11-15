# CRESCO · AgroShift Mobile

> **NASA International Space Apps Challenge**  
> Next-Generation Cross-Platform Mobile Agricultural Decision Support System & 3D Satellite Terrain Monitor.

[![React Native](https://img.shields.io/badge/React%20Native-0.88-61DAFB?logo=react&logoColor=black)](https://reactnative.dev/)
[![Expo SDK](https://img.shields.io/badge/Expo%20SDK-58-000020?logo=expo&logoColor=white)](https://expo.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TanStack Query](https://img.shields.io/badge/TanStack%20Query-v5-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/query/latest)
[![Zustand](https://img.shields.io/badge/State-Zustand-443e38)](https://zustand.docs.pmnd.rs/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

**CRESCO** is a cross-platform mobile application (Android, iOS, Web) built for the **NASA Space Apps Challenge**. It translates multi-spectral Earth observation data, satellite radar wetness indicators, digital elevation models, and soil horizon databases into actionable, farmer-friendly crop rotation plans.

Farmers and agricultural planners can draw their fields on aerial satellite maps, analyze soil composition and topography in real-time 3D, simulate weather volatility, and generate multi-season crop rotation schedules that maximize yields, prevent pest outbreaks, and conserve water.

```
      NASA / ESA Earth Observation Data
 (NASA POWER, Copernicus DEM, Sentinel-1 & 2)
                     │
                     ▼
        AgroShift Scientific Backend
 (Hydrology, GAEZ v5, FAO-56 Kc, SoilGrids 2.0)
                     │
                     ▼
          CRESCO Mobile Client
 ┌──────────────────────────────────────────────┐
 │  🗺️ Interactive Field & Boundary Mapping     │
 │  🌱 Intelligent Crop Rotation Planner        │
 │  🏔️ 3D Terrain & Chlorophyll Live Monitor   │
 │  🤖 Cresco AI Agronomist (Google Gemini)     │
 │  ⚙️ Farm Management & Custom Backend Switch  │
 └──────────────────────────────────────────────┘
```

---

## Key Features

### 1. Interactive Field Boundary Mapping & Geospatial Geometry
- **Interactive Parcel Canvas**: Tap to place polygon vertices directly over aerial imagery.
- **Geodetic Calculations**: Real-time conversion between canvas coordinates and GPS coordinates (`latitude`, `longitude`).
- **Precision Metrics**: Instant calculation of field area in hectares (`ha`), acres, and parcel perimeter in kilometers (`km`).
- **Safety Validations**: Automatic polygon closure validation, intersection and self-crossing detection.
- **Geographic Place Search**: Search and center on global farming locations and administrative zones.

### 2. Algorithmic Crop Rotation Planner
- **Multi-Season Timelines**: Models multi-season rotations (e.g., Sri Lanka's *Maha* and *Yala* monsoon seasons, Mediterranean, and temperate cycles).
- **Comprehensive Crop Database**: 107+ crop profiles across 25 botanical families with water requirement indexes, yield projections ($t/ha$), and growth durations.
- **Succession Strategies**: Supports both **Standing Crop** (active rotation calibration) and **Fallow** (newly cleared or rested soil) entry modes.
- **Turnaround & Expiry Logic**:
  - **Safe Cutoff vs. Hard Cutoff**: Evaluates optimal sowing windows with delay slack days.
  - **Collision Risk Calculation**: Predicts harvest-to-sowing scheduling collisions based on weather forecast variance cones.
- **Multi-Criteria Optimization Filters**: Rank rotation options dynamically by:
  - 🌟 **Best Match** (balanced yield and sustainability)
  - 💧 **Water Saving** (low water footprint)
  - 🌿 **Soil & Nitrogen** (nitrogen-fixing legumes and green manure)
  - 🛡️ **Pest Break** (botanical family alternation)
  - ⚡ **Easy Cycle** (low turnaround complexity)
- **Custom Rotation Builder**: Manually reorder or substitute sequence crops while receiving real-time agronomic feedback.

### 3. 3D Satellite & Terrain Live Monitor
- **Interactive 3D Elevation Mesh**: Renders Copernicus DEM 90m topography with touch-driven pan, pitch, tilt, and zoom controls.
- **3D Chlorophyll & NDVI Heatmaps**: Live chlorophyll concentration ($\mu g/cm^2$) and Sentinel-2 NDVI overlayed on terrain slopes.
- **3D Soil Cutaway Slab**: Visualizes vertical soil horizons from topsoil to root depths with true USDA soil texture color coding (sand, silt, clay, loam).
- **Topographical Hydrology**:
  - Runoff vectors and flow direction arrows ($\vec{dx}, \vec{dy}$).
  - Topographical Wetness Index (TWI) and moisture fusion (topsoil vs. root zone).
  - Low-lying water pooling risk alerts.
- **Forecast Volatility Cones**: Visualizes uncertainty spreads ($\sigma = 0.10$ to $0.28$) impacting seasonal transitions.

### 4. Cresco AI Agronomist (Google Gemini)
- **Context-Aware Assistance**: Automatically receives current field telemetry (exact coordinates, boundary geometry, soil pH, active crop, rotation status).
- **Floating Avoidance Bubble (`CrescoBubble`)**:
  - Draggable, interactive overlay available across all screens.
  - Smart collision avoidance: dynamically detects interactive UI buttons and shifts away from active touch zones.
  - Tap to expand into a full conversational agronomist interface.
- **Gemini AI Integration**: Connect directly using a Google AI Studio API key to activate natural language crop recommendations, pest management advice, and localized planting strategies.

### 5. Multi-Farm Management & Backend Configuration
- **Cloud & Local Synchronization**: Save, load, and manage multiple field profiles and boundaries.
- **Custom Server Switch**: Switch between the production cloud backend (`https://agro.332536.xyz`), local development servers (`127.0.0.1:8000`), or custom LAN edge devices.
- **Uncertainty Presets**: Tune safety buffer days and risk tolerances across **Conservative**, **Balanced**, **Flexible**, or **Custom** profiles.

---

## Tech Stack & Architecture

```
mobile/
├── assets/                  # Icons, aerial maps, brand assets, and fonts
├── src/
│   ├── api/                 # HTTP client, endpoint definitions, query keys, token store
│   │   ├── client.ts        # Fetch wrapper with bearer auth & error mapping
│   │   ├── config.ts        # Dynamic server base URL & local storage persistence
│   │   ├── endpoints.ts     # Zod-validated REST endpoints
│   │   ├── query.ts         # TanStack Query client lifecycle & offline handler
│   │   └── session.ts       # SecureStore token management & session expiry events
│   ├── app/                 # Expo Router filesystem-based routes
│   │   ├── _layout.tsx      # Root provider tree (fonts, query, safe area, AI bubble)
│   │   ├── index.tsx        # Country & season selection
│   │   ├── area.tsx         # Field mapping & parcel polygon drawing
│   │   ├── strategy.tsx     # Field status selection (Standing / Fallow)
│   │   ├── crop.tsx         # Crop search, category filter, and calibration
│   │   ├── plan.tsx         # Rotation plan timeline & alternatives carousel
│   │   ├── monitor.tsx      # 3D DEM mesh, soil cutaway slab & satellite telemetry
│   │   ├── cresco.tsx       # Cresco AI Gemini assistant chat view
│   │   ├── login.tsx        # Auth, server URL settings, and farm management
│   │   └── dev/gallery.tsx  # Design system component gallery preview
│   ├── components/          # Reusable UI kit (glass surfaces, buttons, cards, maps)
│   ├── features/            # Feature-sliced modules (area, auth, country, cresco, crop, monitor, plan)
│   ├── hooks/               # Custom utility hooks (debounce, search focus)
│   ├── i18n/                # Localization strings and agricultural terminology
│   ├── state/               # Zustand global store (planner draft, thresholds, farms)
│   ├── theme/               # Design tokens (Manrope font, forest dark palette, glassmorphism)
│   └── utils/               # Date, measurement, number formatters, and haptics
└── tests/                   # Jest test suites (API, models, geometry, avoidance)
```

### Core Technologies
- **Framework**: [Expo SDK 58](https://expo.dev/) with [React Native 0.88](https://reactnative.dev/) & [React 19](https://react.dev/)
- **Routing**: [Expo Router v58](https://docs.expo.dev/router/introduction/) (File-based typed routing)
- **State Management**: [Zustand 5](https://zustand.docs.pmnd.rs/) (lightweight reactive client state)
- **Data Fetching & Cache**: [TanStack React Query v5](https://tanstack.com/query/latest)
- **Schema Validation**: [Zod 4](https://zod.dev/) for contract-enforced network responses
- **Graphics & Vectors**: [React Native SVG](https://github.com/software-mansion/react-native-svg) for 3D isometric DEM projections and heatmaps
- **Animations & Gestures**: [React Native Reanimated 4](https://docs.swmansion.com/react-native-reanimated/) and [React Native Gesture Handler](https://docs.swmansion.com/react-native-gesture-handler/)
- **Security & Storage**: [Expo SecureStore](https://docs.expo.dev/versions/latest/sdk/securestore/) for hardware-backed token encryption
- **Typography & Styling**: Google Font `Manrope` with custom dark-forest glassmorphism tokens

---

## Earth Observation & Scientific Data Sources

| Provider / Dataset | Data Type | Usage in CRESCO |
| :--- | :--- | :--- |
| **NASA POWER** | Solar radiation, temperature, rainfall archives (2001–2025) | Historical agro-climatology and daily weather distributions |
| **Copernicus DEM (90m)** | High-resolution digital elevation model | 3D terrain elevation mesh, slope calculation, and runoff vectors |
| **Sentinel-2 (ESA)** | Multi-spectral imagery & NDVI | In-season vegetation index and chlorophyll content monitoring |
| **Sentinel-1 (ESA)** | Synthetic Aperture Radar (SAR) backscatter | Surface and root-zone soil wetness index calculation |
| **ISRIC SoilGrids 2.0** | Global gridded soil data (0–200 cm depth) | Soil pH, sand/silt/clay texture, organic carbon, field capacity |
| **FAO GAEZ v5** | Global Agro-Ecological Zones | Agro-climatic crop suitability indices and water regimes |
| **FAO-56 Irrigation Guide** | Crop coefficients ($K_c$) & stage lengths | Crop evapotranspiration ($ET_c$) and water requirements |

---

## Getting Started

### Prerequisites
- **Node.js**: `v20.x` or later
- **Package Manager**: `npm` (or `bun` / `yarn`)
- **Expo Go App** (optional): Installed on your physical Android or iOS device for live testing.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/nasa-app-challege.git
   cd nasa-app-challege/mobile
   ```

2. **Install dependencies:**
   ```bash
   npm ci
   ```

3. **Configure environment variables:**
   Copy the example environment configuration:
   ```bash
   cp .env.example .env.local
   ```
   Edit `.env.local` as needed:
   ```env
   # Backend API Base URL (defaults to production if omitted)
   EXPO_PUBLIC_API_BASE_URL=https://agro.332536.xyz

   # Set to true to run fully offline with mock data
   EXPO_PUBLIC_USE_MOCKS=false

   # Mock error simulation: "off", "transient", or "always"
   EXPO_PUBLIC_MOCK_ERRORS=off
   ```

---

## Running the Application

From within the `mobile/` directory:

### Run in Web Browser
```bash
npm run web
```
*Launches Expo Web on [http://localhost:8081](http://localhost:8081).*

### Run on Mobile Devices / Emulators
```bash
npm start
```
- Press `a` in the terminal to launch the **Android Emulator**.
- Press `i` in the terminal to launch the **iOS Simulator** (macOS required).
- Scan the printed QR code using the **Expo Go** app on your physical mobile device.

### Native Prebuilds (Optional)
```bash
npm run android   # Generates and builds native Android project
npm run ios       # Generates and builds native iOS project (macOS only)
```

---

## Testing & Quality Assurance

CRESCO includes a suite of automated unit, integration, and geometry verification tests:

```bash
# Run Jest test suites
npm test

# Run ESLint validation
npm run lint

# Run TypeScript static typechecking
npm run typecheck
```

### Component Gallery
Inspect the design system, cards, chips, and input controls in development:
- Navigate to `/dev/gallery` in the running web or emulator preview.

---

## Design System & UX Standards

The visual design is grounded in an agricultural dark-mode aesthetic with accessible glassmorphism:
- **Base Background**: Deep Forest (`#12170C`)
- **Accent Primary**: Fluorescent Lime (`#C8F31D`) for primary calls to action, selected nodes, and active boundaries.
- **Warm Neutral**: Cream (`#F1F4E6`) and Sage (`#B5C19B`) for legible typography and secondary labels.
- **Soil Horizon Palette**: True hex representations for USDA textures (Sandy Loam, Silty Clay, Clay Loam, etc.).
- **Typography**: 100% Manrope variable font geometry with tabular figures for scientific telemetry.

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Ensure linting and tests pass: `npm run lint && npm run typecheck && npm test`
3. Commit your changes: `git commit -m "feat(module): add meaningful description"`
4. Push to branch: `git push origin feature/your-feature-name`
5. Open a Pull Request.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.  
All underlying NASA, ESA, ISRIC, and FAO datasets retain their respective public domain and open research citations.
