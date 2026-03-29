import { mount } from "@vue/test-utils";
import { defineComponent, h, nextTick } from "vue";
import { vi } from "vitest";

vi.mock("@/components/LiveFlightMarkers.vue", () => ({
  default: defineComponent({
    name: "LiveFlightMarkers",
    props: {
      flights: {
        type: Array,
        required: true,
      },
    },
    setup() {
      return () => h("div", { "data-testid": "live-flight-markers" });
    },
  }),
}));

vi.mock("@/components/LoggedFlightMarkers.vue", () => ({
  default: defineComponent({
    name: "LoggedFlightMarkers",
    props: {
      flights: {
        type: Array,
        required: true,
      },
      selectedId: {
        type: Number,
        default: null,
      },
    },
    setup() {
      return () => h("div", { "data-testid": "logged-flight-markers" });
    },
  }),
}));

vi.mock("@vue-leaflet/vue-leaflet", () => ({
  LMap: defineComponent({
    name: "LMap",
    props: {
      center: {
        type: Array,
        required: true,
      },
      zoom: {
        type: Number,
        required: true,
      },
      zoomControl: {
        type: Boolean,
        default: true,
      },
      useGlobalLeaflet: {
        type: Boolean,
        default: true,
      },
    },
    setup(_, { slots }) {
      return () => h("div", { "data-testid": "leaflet-map" }, slots.default?.());
    },
  }),
  LTileLayer: defineComponent({
    name: "LTileLayer",
    setup() {
      return () => h("div", { "data-testid": "tile-layer" });
    },
  }),
}));

import MapShell from "@/components/MapShell.vue";

describe("MapShell", () => {
  beforeEach(() => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("configures the map to use Leaflet ESM with the expected core props", () => {
    const wrapper = mount(MapShell, {
      props: {
        center: { lat: -37.8136, lon: 144.9631 },
        zoom: 12,
        mode: "live",
        liveFlights: [],
        loggedFlights: [],
        selectedLogId: null,
        manualLocationActive: false,
      },
    });

    const map = wrapper.getComponent({ name: "LMap" });

    expect(map.props("useGlobalLeaflet")).toBe(false);
    expect(map.props("zoom")).toBe(12);
    expect(map.props("center")).toEqual([-37.8136, 144.9631]);
    expect(map.props("zoomControl")).toBe(false);
  });

  it("uses the ready Leaflet instance for bounds updates and recentering", async () => {
    const invalidateSize = vi.fn();
    const setView = vi.fn();
    const getZoom = vi.fn(() => 12);
    const getCenter = vi.fn(() => ({
      lat: -37.82,
      lng: 144.95,
    }));
    const getBounds = vi.fn(() => ({
      getNorth: () => -37.7,
      getSouth: () => -37.9,
      getEast: () => 145.1,
      getWest: () => 144.8,
    }));
    const whenReady = vi.fn((callback: () => void) => callback());

    const wrapper = mount(MapShell, {
      props: {
        center: { lat: -37.8136, lon: 144.9631 },
        zoom: 12,
        mode: "live",
        liveFlights: [],
        loggedFlights: [],
        selectedLogId: null,
        manualLocationActive: false,
      },
    });

    await wrapper.getComponent({ name: "LMap" }).vm.$emit("ready", {
      invalidateSize,
      setView,
      getZoom,
      getCenter,
      getBounds,
      whenReady,
    });
    await nextTick();

    expect(whenReady).toHaveBeenCalledTimes(1);
    expect(invalidateSize).toHaveBeenCalledWith(false);
    expect(getBounds).toHaveBeenCalled();
    expect(wrapper.emitted("updateBounds")?.[0]).toEqual([
      {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
    ]);

    await wrapper.setProps({
      center: { lat: -37.81, lon: 144.97 },
    });

    expect(setView).toHaveBeenCalledWith([-37.81, 144.97], 12, { animate: true });

    await wrapper.getComponent({ name: "LMap" }).vm.$emit("moveend", { target: {} });

    expect(getBounds).toHaveBeenCalledTimes(2);
  });

  it("does not call setView again when the store center already matches the map center", async () => {
    const setView = vi.fn();

    const wrapper = mount(MapShell, {
      props: {
        center: { lat: -37.8136, lon: 144.9631 },
        zoom: 12,
        mode: "live",
        liveFlights: [],
        loggedFlights: [],
        selectedLogId: null,
        manualLocationActive: false,
      },
    });

    await wrapper.getComponent({ name: "LMap" }).vm.$emit("ready", {
      invalidateSize: vi.fn(),
      setView,
      getZoom: vi.fn(() => 12),
      getCenter: vi.fn(() => ({
        lat: -37.8136,
        lng: 144.9631,
      })),
      getBounds: vi.fn(() => ({
        getNorth: () => -37.7,
        getSouth: () => -37.9,
        getEast: () => 145.1,
        getWest: () => 144.8,
      })),
      whenReady: vi.fn((callback: () => void) => callback()),
    });
    await nextTick();

    await wrapper.setProps({
      center: { lat: -37.8136, lon: 144.9631 },
    });

    expect(setView).not.toHaveBeenCalled();
  });

  it("shows the map target overlay while manual location mode is active", () => {
    const wrapper = mount(MapShell, {
      props: {
        center: { lat: -37.8136, lon: 144.9631 },
        zoom: 12,
        mode: "live",
        liveFlights: [],
        loggedFlights: [],
        selectedLogId: null,
        manualLocationActive: true,
      },
    });

    expect(wrapper.find(".manual-location-target").exists()).toBe(true);
  });
});
