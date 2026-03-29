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
  });

  it("caps the query radius at the backend maximum", () => {
    const mapStore = useMapStore();
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });

    mapStore.setBounds({
      north: 85,
      south: -85,
      east: 179,
      west: -179,
    });

    expect(mapStore.query).toEqual({
      center: { lat: 0, lon: 0 },
      radiusKm: 100,
    });
  });
});
