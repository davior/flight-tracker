import { createPinia, setActivePinia } from "pinia";

import { useMapStore } from "@/stores/map";

describe("useMapStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("keeps the chosen center stable when viewport bounds update", () => {
    const mapStore = useMapStore();
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });

    mapStore.setBounds({
      north: -37.7,
      south: -37.9,
      east: 145.1,
      west: 144.8,
    });

    expect(mapStore.center).toEqual({ lat: -37.8136, lon: 144.9631 });
    expect(mapStore.viewportCenter).toEqual({ lat: -37.8, lon: 144.95 });
    expect(mapStore.query).toEqual({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      center: { lat: -37.8, lon: 144.95 },
    });
    expect(mapStore.liveQuery).toEqual({
      visibleBounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      queryBounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      center: { lat: -37.8, lon: 144.95 },
      isClamped: false,
    });
  });

  it("does not expose a nearby query until map bounds exist", () => {
    const mapStore = useMapStore();
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });

    expect(mapStore.query).toBeNull();
    expect(mapStore.liveQuery).toBeNull();
  });

  it("derives a clamped live query when visible bounds exceed the API limit", () => {
    const mapStore = useMapStore();

    mapStore.setBounds({
      north: -33.879656336198934,
      south: -35.32308617090494,
      east: 143.9140319824219,
      west: 140.4698181152344,
    });

    expect(mapStore.liveQuery?.isClamped).toBe(true);
    expect(mapStore.liveQuery?.queryBounds).not.toEqual(mapStore.liveQuery?.visibleBounds);
    expect(mapStore.liveQuery?.center.lat).toBeCloseTo(-34.60137125355194, 10);
    expect(mapStore.liveQuery?.center.lon).toBeCloseTo(142.19192504882812, 10);
  });
});
