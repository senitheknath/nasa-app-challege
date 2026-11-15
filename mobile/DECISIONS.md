# Implementation decisions

- The attached brief explicitly names `Documents/nasa-apps-react`, which did not exist. The project was initialized there using the sibling Expo starter's Git history.
- The design handoff is an executable Figma Make export. It contains component source and a documented design system. No 2× screen exports, Figma document, or Figma MCP connection were available. The export is the visual reference.
- The prototype uses a static aerial photograph and normalized illustration coordinates. The mock boundary calculations retain its scale. Place search returns suggestions and lets users select a place; the static reference image cannot pan to geographic coordinates. Future geographic imagery, coordinates, and measurement accuracy need an API and an updated design.
- The reference permits Fallow to skip crop calibration. The Crop tab stays locked while Fallow is selected, and Plan’s Back button returns to Strategy. New plan clears the entire draft. A fresh load starts at Country because the draft lives in memory. The plan endpoint accepts an optional crop for this strategy and may select one. Its mock picks the default crop.
- The web date field uses the browser’s date input. Native uses the system date picker. Native status bars and display cutouts determine safe areas; web reserves the prototype's top inset.
- Android uses the opaque glass treatment specified by the source. iOS and web use blur in the source's glass surfaces. Segments, sheet handle, and suggestions have accessible controls. The plan's compact stat grid wraps to two columns at larger font scales.
- The session-expiry route is a placeholder for a future sign-in flow. Native stores tokens in SecureStore; web uses an in-memory token during the current page session.
