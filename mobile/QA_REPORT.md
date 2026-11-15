# CRESCO QA report

## Reference and environments

I rendered the supplied Figma Make export at 390 × 820 and compared its screenshots with the running Expo web preview at the same viewport. Both renders used the reference photo bytes. I also ran the touch flow at 360 × 640 and 820 × 1000. The comparison covers the executable handoff.

## Screen comparison

| Screen | Status | Compared states and deviations |
| --- | --- | --- |
| Country | Close match on Expo web | Matched the hero, Manrope typography, glass search, metric tiles, workflow, and lime start action. Checked country search, unavailable-country feedback, no results, and offline recovery. |
| Mark your field | Close match on Expo web | Matched the aerial framing, grid, parcel geometry, control group, and metric tiles. The same 390 × 820 test vertices produced 54.3 ha, 134.1 acres, and 8.08 km in both previews. The app also returns place suggestions. The image stays fixed when a place is selected. |
| Field status | Close match on Expo web | Compared the field summary and selected style. The app now offers No rotation and Current crop. Verified both navigation paths in Expo web, with Current crop selected by default. |
| Active crop | Close match on Expo web | Compared the date and preset block, category strip, search, crop cards, selected check, and water bar. Tested date entry, category selection, and an empty search. Crop results are cursor-paginated. The browser and native OS supply their respective date pickers. |
| Rotation plan | Close match on Expo web | Compared the aerial parcel, sheet, Overview, and Timeline. Checked the selected crop in the sowing action, drag, tap, and keyboard activation for the two-position sheet, Fallow’s Crop bypass and Back route, and New plan reset. The detail area scrolls on short screens. Larger font settings can use a two-column stat grid. |
| Session expiry | Infrastructure | The placeholder is outside the design flow. Jest verified bearer headers, 401 normalization and token clearing, and preservation of a newer token when a stale request returns 401. |
| Component gallery | Infrastructure | Opened the development route and verified that the component gallery renders. |

## Follow-up UI and logic audit

| Area | Finding and fix |
| --- | --- |
| Country | The footer covered suggestions at 320 × 568 and tabbing away from the input dismissed the list. Suggestions now scroll above the footer, focus stays within the picker, and Enter and Escape work from the keyboard. The search pill carries the focus outline. |
| Field drawing | A stale place result could still be selected while a new search was pending. Search now clears stale options. Crossed or repeated corners are rejected before measurement. Measurement loading retains the metric row layout. An unavailable map image uses the map retry state. |
| Field status and navigation | Switching away from Fallow could leave the old Plan route unlocked. A change to strategy, crop, or date now invalidates later steps until the updated draft is confirmed. |
| Crop | The Generate plan button could submit an old selection during a search or on an empty result list. It now requires a selected crop in the current results. Last Yala selects the first day of the most recently completed Yala season. |
| Plan | The collapsed sheet handle could move behind the footer after resizing. The sheet measures its available height, and scrollable content stays above the footer. |
| Accessibility and rendering | Selected controls expose their state on web. Empty strings no longer produce raw text children inside React Native views. |

## Verification

- Expo web ran the five-screen flow and the mobile and tablet touch checks.
- Jest passed 15 tests across DTO validation, view-model mapping, React Query pagination and retry, formatting, and HTTP transport.
- TypeScript, Expo lint, and the Expo dependency compatibility check passed.
- Expo exports completed for Android, iOS, and web. Native device rendering, native picker appearance, iOS blur, and Android's opaque glass fallback still need on-device visual verification.
- The HTTP transport uses intercepted responses in Jest. A deployed endpoint was outside the frontend handoff.
