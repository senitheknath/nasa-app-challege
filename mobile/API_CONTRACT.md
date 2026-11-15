# CRESCO frontend API contract

All paths are relative to `EXPO_PUBLIC_API_BASE_URL`. Requests accept JSON. POST bodies use `Content-Type: application/json`. When a token exists the client sends `Authorization: Bearer <token>`. Responses are validated with Zod. Unknown object keys are ignored. Fields shown below are required unless optional or nullable. Use a stable ID within each collection. Human-readable labels are display strings and can be localized by the API.

Use 200 with a JSON body on success. Collections use an empty array when there are no matches. Nullable results use JSON `null` when unavailable. Prefer a stable domain code in errors, for example `{"code":"UNSUPPORTED_COUNTRY"}`. The client treats 401 as session expiry and can retry network errors, 429s, and 5xx responses. Enable browser CORS for the deployed frontend origin, JSON requests, and the Authorization header.

## GET /v1/countries

No params. Returns `CountryDataDto`, beginning with the current season, catalog count, season count, supported default, and initial selections for the planner. The default country must be supported when the list is nonempty.

```ts
type CountryDto = { id: string; name: string; supported: boolean }
type CountryDataDto = {
  defaultCountryId: string
  currentSeason: string
  cropCount: number
  seasonCount: number
  defaultStrategyId: string
  defaultCropId: string
  countries: CountryDto[]
}
```

```json
{
  "defaultCountryId": "LK",
  "currentSeason": "Maha",
  "cropCount": 10,
  "seasonCount": 2,
  "defaultStrategyId": "standing",
  "defaultCropId": "rice",
  "countries": [
    { "id": "IN", "name": "India", "supported": false },
    { "id": "LK", "name": "Sri Lanka", "supported": true }
  ]
}
```

## GET /v1/map

Query `country` is a supported country ID. Returns the image used for the field canvas and Plan hero. Its HTTPS URL must be reachable by the client.

```ts
type MapDto = { imageUrl: string } | null
```

```json
{ "imageUrl": "https://assets.example.com/maps/LK.jpg" }
```

## GET /v1/places

Query `country` is a supported country ID and `q` is the search text. Return relevant suggestions in display order. The current prototype uses suggestions as labels over the country’s static image.

```ts
type PlaceDto = { id: string; name: string }
type Response = PlaceDto[]
```

```json
[{ "id": "kandy", "name": "Kandy" }]
```

## POST /v1/fields/measure

Body `FieldDto`. Points are the ordered vertices of an implicitly closed polygon in normalized canvas coordinates from 0 to 100, with the origin at the top left. Require at least three distinct vertices with positive area and no crossing edges. Use the country map's documented scale. Return the preview geometry in hectares, acres, and kilometers. This computation is repeatable and has no storage side effects.

```ts
type Point = { x: number; y: number }
type FieldDto = { countryId: string; points: Point[] }
type MeasurementDto = { hectares: number; acres: number; perimeterKm: number } | null
```

Example body

```json
{ "countryId": "LK", "points": [{"x": 0, "y": 0}, {"x": 20, "y": 0}, {"x": 20, "y": 10}] }
```

Example response

```json
{ "hectares": 5, "acres": 12.355, "perimeterKm": 3.142 }
```

## GET /v1/strategies

Query `country` is a supported country ID. Return Fallow and Current crop in display order. `requiresCrop` controls whether selection continues through Crop or opens the Plan preview directly.

```ts
type StrategyDto = { id: string; tag: string; title: string; description: string; requiresCrop: boolean }
type Response = StrategyDto[]
```

```json
[
  { "id": "fallow", "tag": "Fallow", "title": "No rotation", "description": "Newly cleared land", "requiresCrop": false },
  { "id": "standing", "tag": "Standing", "title": "Current crop", "description": "Already planted", "requiresCrop": true }
]
```

## GET /v1/crop-categories

Query `country` is a supported country ID. Return categories in display order. The frontend adds All.

```ts
type CategoryDto = { id: string; label: string }
type Response = CategoryDto[]
```

```json
[{"id":"cereals","label":"Cereals"},{"id":"legumes","label":"Legumes"}]
```

## GET /v1/crops

Query `country` is required. Optional `q` filters names, `category` is a category ID, and `cursor` is the previous page's opaque `nextCursor`. Use stable ordering within the same filter. Set `nextCursor` to null on the final page. Water is a 0–100 index. Yield is tonnes per hectare.

```ts
type CropDto = {
  id: string
  name: string
  category: CategoryDto
  yieldTonnesPerHectare: number
  waterPercent: number
}
type CropPageDto = { items: CropDto[]; nextCursor: string | null }
```

```json
{
  "items": [
    { "id": "rice", "name": "Paddy Rice", "category": { "id": "cereals", "label": "Cereals" }, "yieldTonnesPerHectare": 5.2, "waterPercent": 85 }
  ],
  "nextCursor": null
}
```

## POST /v1/plans/preview

Body `PlanRequestDto`. Omit `cropId` when the strategy can choose the crop. The calendar date has format YYYY-MM-DD and no timezone. The response crop is the selected or resolved crop. The first chronological timeline entry is the next sowing action. The count comes from the timeline. This endpoint can be repeated without saving a plan.

```ts
type PlanRequestDto = FieldDto & { strategyId: string; cropId?: string; sowingDate: string }
type PlanSeasonDto = { id: string; season: string; year: number; crop: CropDto; note: string }
type PlanDto = { hectares: number; strategyTag: string; crop: CropDto; timeline: PlanSeasonDto[] } | null
```

Example body

```json
{
  "countryId": "LK",
  "points": [{"x": 0, "y": 0}, {"x": 20, "y": 0}, {"x": 20, "y": 10}],
  "strategyId": "standing",
  "cropId": "rice",
  "sowingDate": "2026-11-15"
}
```

Example response

```json
{
  "hectares": 5,
  "strategyTag": "Standing",
  "crop": {
    "id": "rice", "name": "Paddy Rice", "category": {"id": "cereals", "label": "Cereals"},
    "yieldTonnesPerHectare": 5.2, "waterPercent": 85
  },
  "timeline": [
    {
      "id": "maha-2026", "season": "Maha", "year": 2026,
      "crop": {
        "id": "rice", "name": "Paddy Rice", "category": {"id": "cereals", "label": "Cereals"},
        "yieldTonnesPerHectare": 5.2, "waterPercent": 85
      },
      "note": "Current"
    },
    {
      "id": "yala-2027", "season": "Yala", "year": 2027,
      "crop": {
        "id": "groundnut", "name": "Groundnut", "category": {"id": "legumes", "label": "Legumes"},
        "yieldTonnesPerHectare": 2.1, "waterPercent": 40
      },
      "note": "Restores nitrogen"
    }
  ]
}
```
