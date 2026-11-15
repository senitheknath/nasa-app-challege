# CRESCO

CRESCO is an Expo SDK 58 crop rotation planner for Android, iOS, and web. Its five screens follow the supplied Figma Make prototype. It starts with mock data.

## Windows setup

Use a supported Node.js version, npm, and PowerShell.

```powershell
Set-Location 'C:\Users\aksek\Documents\nasa-apps-react'
npm ci
Copy-Item .env.example .env.local
npx expo start
```

Press `w` for the browser. The browser preview also starts directly with `npm run web`. For Android, use a connected device, an emulator, or an Expo development build. Use an iOS device or an iOS development build when developing from Windows. Config plugin changes take effect after rebuilding the native app.

Open `/dev/gallery` in the development preview to inspect reusable components. Production builds redirect that route to the country screen.

## Data configuration

| Variable | Behavior |
| --- | --- |
| `EXPO_PUBLIC_USE_MOCKS` | `true` (default) selects the mock transport. Set to `false` to use HTTP. |
| `EXPO_PUBLIC_API_BASE_URL` | API origin or base path without a trailing slash. Required for HTTP. Use a host reachable from your device. |
| `EXPO_PUBLIC_MOCK_ERRORS` | Omit for occasional transient errors. Use `off` for repeatable visual QA or `always` to test retry states. |

To connect the real API, implement [API_CONTRACT.md](API_CONTRACT.md), set the base URL and disable mocks in `.env.local`, then restart Expo and reload. The app validates JSON in both modes. Real authorization tokens are provided to `tokenStore.set` by a future sign-in flow. Requests attach a bearer token when present. A 401 clears the token and sends the user to the session-expiry placeholder. Native token storage uses SecureStore. Browser tokens live in memory for the current page session. Use HTTPS when deploying and keep secrets out of `EXPO_PUBLIC_*`.

The mock map uses the aerial photo from the prototype and its field measurement scale. Place suggestions can be picked, and the drawing preview uses normalized image coordinates. Plans are previews for the current draft.

## Project structure

- `src/app` contains Expo Router routes and the root providers.
- `src/features` contains screens, DTO schemas, view models, mappers, and queries.
- `src/api` contains environment selection, endpoint functions, authenticated transport, query keys, and connectivity integration.
- `src/mocks` contains example data, preview calculations, latency, and error simulation.
- `src/state` holds the in-progress selections and drawing in Zustand. TanStack Query owns remote data.
- `src/components`, `src/theme`, `src/i18n`, and `src/utils` contain the UI kit, design tokens, static copy, and formatting.

```powershell
npm run lint
npm run typecheck
npm test -- --runInBand
```

See [FIGMA_INVENTORY.md](FIGMA_INVENTORY.md), [DECISIONS.md](DECISIONS.md), and [QA_REPORT.md](QA_REPORT.md) for design and verification details.
