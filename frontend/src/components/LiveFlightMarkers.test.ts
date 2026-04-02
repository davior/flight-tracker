import { mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";

vi.mock("@vue-leaflet/vue-leaflet", () => ({
  LMarker: defineComponent({
    name: "LMarker",
    props: {
      latLng: {
        type: Array,
        required: true,
      },
    },
    setup(_, { slots }) {
      return () => h("div", { "data-testid": "leaflet-marker" }, slots.default?.());
    },
  }),
  LPopup: defineComponent({
    name: "LPopup",
    setup(_, { slots }) {
      return () => h("div", { "data-testid": "leaflet-popup" }, slots.default?.());
    },
  }),
  LIcon: defineComponent({
    name: "LIcon",
    props: {
      iconSize: {
        type: Array,
        required: true,
      },
      iconAnchor: {
        type: Array,
        required: true,
      },
      className: {
        type: String,
        default: "",
      },
    },
    setup(_, { slots }) {
      return () => h("div", { "data-testid": "leaflet-icon" }, slots.default?.());
    },
  }),
}));

vi.mock("@/components/LiveFlightPopup.vue", () => ({
  default: defineComponent({
    name: "LiveFlightPopup",
    props: {
      flight: {
        type: Object,
        required: true,
      },
    },
    setup() {
      return () => h("div", { "data-testid": "live-flight-popup" });
    },
  }),
}));

import LiveFlightMarkers from "@/components/LiveFlightMarkers.vue";

describe("LiveFlightMarkers", () => {
  it("renders live flights as rotated aircraft icons", () => {
    const wrapper = mount(LiveFlightMarkers, {
      props: {
        flights: [
          {
            icao24: "abc123",
            callsign: "TEST123",
            origin_country: "Australia",
            latitude: -37.8136,
            longitude: 144.9631,
            altitude: 10000,
            velocity: 200,
            heading: 135,
            vertical_rate: 0,
            last_contact: 123456,
            distance_km: 4.2,
            type_code: "A320",
            manufacturer: "Airbus",
            model: "A320-232",
            category: "L",
            category_label: "Light",
            category_description: "Small aircraft in the light wake turbulence category.",
            display_type: "Airbus A320-232",
          },
        ],
      },
    });

    expect(wrapper.getComponent({ name: "LMarker" }).props("latLng")).toEqual([-37.8136, 144.9631]);
    expect(wrapper.getComponent({ name: "LIcon" }).props("className")).toBe("live-flight-marker-icon");
    expect(wrapper.find(".live-flight-marker__aircraft").attributes("style")).toContain("--flight-heading: 135deg;");
  });
});
