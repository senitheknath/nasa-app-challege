# CRESCO QA report

## Reference and environments

I rendered the supplied Figma Make export at 390 × 820 and compared its screenshots with the running Expo web preview at the same viewport. Both renders used the reference photo bytes. I also ran the touch flow at 360 × 640 and 820 × 1000. The comparison covers the executable handoff.

## Screen comparison

| Screen | Status | Compared states and deviations |
| --- | --- | --- |
| Country | Close match on Expo web | Matched the hero, Manrope typography, glass search, metric tiles, workflow, and lime start action. Checked country search, unavailable-country feedback, no results, and offline recovery. |
| Mark your field | Close match on Expo web | Matched the aerial framing, grid, parcel geometry, control group, and metric tiles. The same 390 × 820 test vertices produced 54.3 ha, 134.1 acres, and 8.08 km in both previews. The app also returns place suggestions. The image stays fixed when a place is selected. |
| Field status | Close match on Expo web | Compared the field summary, three status cards, and selected style. Allowed text to grow and wrap within the cards. |
| Active crop | Close match on Expo web | Compared the date and preset block, category strip, search, crop cards, selected check, and water bar. Tested date entry, category selection, and an empty search. Crop results are cursor-paginated. The browser and native OS supply their respective date pickers. |
| Rotation plan | Close match on Expo web | Compared the aerial parcel, sheet, Overview, and Timeline. Checked the selected crop in the sowing action, drag, tap, and keyboard activation for the two-position sheet, Fallow’s Crop bypass and Back route, and New plan reset. The detail area scrolls on short screens. Larger font settings can use a two-column stat grid. |
| Session expiry | Infrastructure | The placeholder is outside the design flow. Jest verified bearer headers, 401 normalization and token clearing, and preservation of a newer token when a stale request returns 401. |
| Component gallery | Infrastructure | Opened the development route and verified that the component gallery renders. |

## Verification

- Expo web ran the five-screen flow and the mobile and tablet touch checks.
- Jest passed 11 tests across DTO validation, view-model mapping, React Query pagination and retry, formatting, and HTTP transport.
- TypeScript, Expo lint, and the Expo dependency compatibility check passed.
- Expo exports completed for Android, iOS, and web. Native device rendering, native picker appearance, iOS blur, and Android's opaque glass fallback still need on-device visual verification.
- The HTTP transport uses intercepted responses in Jest. A deployed endpoint was outside the frontend handoff.
