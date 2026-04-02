import { deriveCenterFromBounds, deriveRadiusFromBounds, fitBoundsToMaxRadius, MAX_NEARBY_RADIUS_KM } from "@/lib/geo";

describe("deriveRadiusFromBounds", () => {
  it("derives a positive query radius from map bounds", () => {
    const radius = deriveRadiusFromBounds({
      north: -37.7,
      south: -37.9,
      east: 145.1,
      west: 144.8,
    });

    expect(radius).toBeGreaterThan(0);
    expect(radius).toBeLessThan(30);
  });
});

describe("fitBoundsToMaxRadius", () => {
  it("returns the original bounds when they already fit the limit", () => {
    const bounds = {
      north: -37.7,
      south: -37.9,
      east: 145.1,
      west: 144.8,
    };

    expect(fitBoundsToMaxRadius(bounds, MAX_NEARBY_RADIUS_KM)).toEqual({
      bounds,
      isClamped: false,
    });
  });

  it("returns a centered square that fits the limit when visible bounds are too large", () => {
    const visibleBounds = {
      north: -29,
      south: -40,
      east: 151,
      west: 138,
    };

    const result = fitBoundsToMaxRadius(visibleBounds, MAX_NEARBY_RADIUS_KM);

    expect(result.isClamped).toBe(true);
    expect(deriveRadiusFromBounds(result.bounds)).toBeLessThanOrEqual(MAX_NEARBY_RADIUS_KM);
    expect(deriveCenterFromBounds(result.bounds)).toEqual(deriveCenterFromBounds(visibleBounds));
    expect(result.bounds.north - result.bounds.south).toBeCloseTo(result.bounds.east - result.bounds.west, 5);
  });
});
