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
      north: -29,
      south: -40,
      east: 151,
      west: 138,
    });

    expect(mapStore.liveQuery?.isClamped).toBe(true);
    expect(mapStore.liveQuery?.queryBounds).not.toEqual(mapStore.liveQuery?.visibleBounds);
    expect(mapStore.liveQuery?.center.lat).toBeCloseTo(-34.5, 10);
    expect(mapStore.liveQuery?.center.lon).toBeCloseTo(144.5, 10);
  });
});
