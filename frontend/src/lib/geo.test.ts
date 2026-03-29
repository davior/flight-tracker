import { deriveRadiusFromBounds } from "@/lib/geo";

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
