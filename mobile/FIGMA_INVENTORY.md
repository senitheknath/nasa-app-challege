# CRESCO Figma inventory

The design handoff is the Figma Make export under `Downloads/project`. The screen implementations, design system, screen map, SVG paths and image URLs in that export are the source for this port.

| Screen | Prototype UI and states | Dynamic values |
| --- | --- | --- |
| Country | Hero photo, logo, season pill, country search with suggestion list, supported and unavailable rows, no-match and country error, three stat tiles, how-it-works strip, start action | Current season, counts for crops/seasons/steps, country name and availability |
| Mark your field | Full-bleed aerial image and grid, place search, drawing controls, open dotted and closed filled parcel, emphasized first vertex, drawing hint, metric tiles, disabled Continue until closed | Country, optional place matches, map image, field points, hectares, acres, estimated perimeter |
| Field status | Field-size summary and exclusive status cards, selected check or unselected arrow. The app offers No rotation and Current crop. | Hectares, strategy id, tag, title and description |
| Active crop | Sowing date field and three presets, scrollable category selector, search, empty crop result, selected and unselected cards | Date, category labels, crop name, category, yield and water need |
| Rotation plan | Parcel hero, two-position sheet, Overview/Timeline switch, skeleton, sowing action, stat grid, water bar, timeline rows and notes | Boundary, hectares, strategy, first recommended sowing action, season, category, yield, water, next crop, ordered season entries |

## Reusable components

| Component | Variants and states |
| --- | --- |
| Logo, season badge, workflow strip | Default |
| Header and icon buttons | Glass/default, dark, lime, pressed, disabled |
| Primary button | Default, pressed, disabled, busy |
| Floating step navigation | Current, completed, reached, locked, pressed |
| Card surface | Glass, strong glass, translucent card, selected, action highlight |
| Search field and suggestions | Idle, focused, entered, loading, empty, unavailable, error, selected |
| Metric tile, compact stat | Default, muted, accent, large or compact |
| Segmented control and preset chip | Selected, unselected, pressed, horizontally scrollable |
| Strategy and crop cards | Default, pressed, selected |
| Progress | Empty, partial, full, animated |
| Date field | Selected date and native or browser calendar editing |
| Map control and boundary | Drawing, closing, reset, first-point close target, open or closed boundary |
| Plan sheet and timeline card | Expanded/collapsed, overview/timeline, first/ordinary season, scroll |
| Feedback | Layout skeleton, empty message, unsupported country, error/retry, offline/retry |

## Prototype navigation

Country → Area → Field status → Active crop → Rotation plan. Choosing Fallow goes directly from Field status to Rotation plan. Back from that plan returns to Field status. The location pin returns to Country. Reached steps remain accessible through the floating navigation. New plan clears the boundary and locks later steps. The sheet can be dragged between two positions and both tabs remain part of the Plan screen.

The reference has no authentication screen. The requested session-expiry destination and development gallery are infrastructure routes. Loading, empty, offline and error treatments extend the reference feedback styles where API states are unspecified.
