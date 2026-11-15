import { normalizeGeoBoundary, usePlanner } from '@/state/usePlanner';

describe('loadSavedFarm & normalizeGeoBoundary', () => {
  beforeEach(() => {
    usePlanner.getState().reset();
  });

  it('parses GeoJSON Polygon boundaries without crashing', () => {
    const geoJson = {
      type: 'Polygon',
      coordinates: [
        [
          [80.4, 7.3],
          [80.42, 7.3],
          [80.42, 7.32],
          [80.4, 7.32],
          [80.4, 7.3],
        ],
      ],
    };

    const ring = normalizeGeoBoundary(geoJson);
    expect(ring).toHaveLength(4);
    expect(ring[0]).toEqual({ latitude: 7.3, longitude: 80.4 });

    usePlanner.getState().loadSavedFarm({
      id: 42,
      name: 'Kandy Parcel',
      country: 'LK',
      latitude: 7.31,
      longitude: 80.41,
      area_ha: 2.5,
      boundary: geoJson,
      farm: {
        irrigation: 'irrigated',
        crop_id: 'rice',
        start_date: '2026-05-01',
      },
    });

    const state = usePlanner.getState();
    expect(state.farmId).toBe(42);
    expect(state.boundary).toHaveLength(4);
    expect(state.points.length).toBeGreaterThanOrEqual(4);
    expect(state.cropId).toBe('rice');
    expect(state.irrigation).toBe('irrigated');
    expect(state.sowingDate).toBe('2026-05-01');
    expect(state.reached).toBe(6);
  });

  it('handles null or malformed boundaries safely', () => {
    expect(normalizeGeoBoundary(null)).toEqual([]);
    expect(normalizeGeoBoundary('not-json')).toEqual([]);
    expect(normalizeGeoBoundary({ type: 'Point', coordinates: [80, 7] })).toEqual([]);

    usePlanner.getState().loadSavedFarm({
      id: 7,
      name: 'No Boundary Farm',
      country: 'LK',
      latitude: 7.87,
      longitude: 80.77,
      boundary: null,
    });

    const state = usePlanner.getState();
    expect(state.farmId).toBe(7);
    expect(state.boundary).toEqual([]);
    expect(state.points).toHaveLength(4);
    expect(state.closed).toBe(true);
  });
});
