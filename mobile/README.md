# CRESCO Mobile Application

**CRESCO** is a cross-platform agricultural decision support and crop rotation planner built with **Expo SDK 58** and **React Native** for Android, iOS, and Web, developed for the **NASA Space Apps Challenge**.

For the comprehensive system architecture, NASA data sources, and scientific modeling details, see the root [README.md](../README.md).

---

## Quick Start

### 1. Install Dependencies
```bash
npm ci
```

### 2. Configure Environment
```bash
# Copy example configuration
cp .env.example .env.local
```

| Environment Variable | Description | Default |
| :--- | :--- | :--- |
| `EXPO_PUBLIC_API_BASE_URL` | AgroShift backend URL (without trailing slash) | `https://agro.332536.xyz` |
| `EXPO_PUBLIC_USE_MOCKS` | Set to `true` to run offline using bundled mock data | `false` |
| `EXPO_PUBLIC_MOCK_ERRORS` | Error simulation mode: `off`, `transient`, or `always` | `off` |

### 3. Launch Development Server
```bash
# Start Expo development bundler
npx expo start

# Or start directly in web browser
npm run web
```
- Press `w` to open in browser ([http://localhost:8081](http://localhost:8081)).
- Press `a` to open in connected Android emulator / device.
- Press `i` to open in iOS simulator (macOS only).
- Scan the QR code with **Expo Go** on Android/iOS.

---

## Available Scripts

| Script | Command | Description |
| :--- | :--- | :--- |
| `npm start` | `expo start` | Start the Expo CLI development server |
| `npm run web` | `expo start --web` | Start the interactive web preview |
| `npm run android` | `expo run:android` | Build and run native Android project |
| `npm run ios` | `expo run:ios` | Build and run native iOS project |
| `npm run lint` | `expo lint` | Lint codebase with ESLint & Expo config |
| `npm run typecheck` | `tsc --noEmit` | Check TypeScript types without emitting files |
| `npm test` | `jest` | Run test suite with Jest |

---

## Application Structure

- `src/app/` — Expo Router file-based route definitions (`index`, `area`, `strategy`, `crop`, `plan`, `monitor`, `cresco`, `login`).
- `src/api/` — API transport client, query keys, session token persistence, and endpoints.
- `src/features/` — Feature-sliced modules (Screen components, hooks, DTOs, and view-models).
- `src/components/` — Design system primitives, glassmorphism containers, 3D SVG canvases, and interactive cards.
- `src/state/` — Zustand store for farm drafts, polygon geometry, and uncertainty thresholds.
- `src/theme/` — Design tokens (colors, typography, spacing, radius, and shadows).
- `src/i18n/` — Agricultural UI copy and string constants.
- `src/utils/` — Unit conversions, date formatters, and native haptics.
- `tests/` — Automated tests covering API contracts, geometry, and session handling.

---

## Design System & Development Preview

- Visit `/dev/gallery` in the development build to preview all reusable design system components, typography styles, and interactive cards.
- Design tokens adhere to the Figma specification: deep forest palette (`#12170C`), luminous lime accents (`#C8F31D`), and accessible glass surfaces.

---

## Documentation

- [API Contract](API_CONTRACT.md) — REST API specifications and Zod DTO definitions.
- [Implementation Decisions](DECISIONS.md) — Technical tradeoffs and architecture decisions.
- [Figma Inventory](FIGMA_INVENTORY.md) — Component mapping and visual specification.
- [QA Report](QA_REPORT.md) — Verification checklist and screen comparison notes.
