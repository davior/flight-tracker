import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";

describe("aircraft helpers", () => {
  it("formats category labels with their code", () => {
    expect(
      formatAircraftCategory({
        category: "L",
        category_label: "Light",
        category_description: "Small aircraft in the light wake turbulence category.",
      }),
    ).toBe("Light (L)");
  });

  it("falls back to the raw category code when no label exists", () => {
    expect(
      formatAircraftCategory({
        category: "CUSTOM",
        category_label: null,
        category_description: null,
      }),
    ).toBe("CUSTOM");
  });

  it("returns the category description when present", () => {
    expect(
      getAircraftCategoryDescription({
        category: "L",
        category_label: "Light",
        category_description: "Small aircraft in the light wake turbulence category.",
      }),
    ).toBe("Small aircraft in the light wake turbulence category.");
  });

  it("prefers display_type when present", () => {
    expect(
      getAircraftDisplayLabel({
        display_type: "Airbus A320-232",
        category: "L",
        category_label: "Light",
        category_description: "Small aircraft in the light wake turbulence category.",
      }),
    ).toBe("Airbus A320-232");
  });

  it("falls back to category when display_type is unavailable", () => {
    expect(
      getAircraftDisplayLabel({
        display_type: null,
        category: "HELICOPTER",
        category_label: "Helicopter",
        category_description: "Rotary-wing helicopter aircraft.",
      }),
    ).toBe("Helicopter (HELICOPTER)");
  });

  it("returns null when neither display_type nor category is available", () => {
    expect(
      getAircraftDisplayLabel({
        display_type: null,
        category: null,
        category_label: null,
        category_description: null,
      }),
    ).toBeNull();
  });
});
