import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import FlightListPanel from "@/components/FlightListPanel.vue";
import type { ApiLiveFlight, ApiLoggedFlight } from "@/types/api";

function makeLiveFlight(overrides: Partial<ApiLiveFlight> = {}): ApiLiveFlight {
  return {
    icao24: "abc123",
    callsign: "TEST1",
    origin_country: "AU",
    latitude: -37.8,
    longitude: 144.9,
    altitude: 5000,
    velocity: 250,
    heading: 90,
    vertical_rate: 0,
    last_contact: null,
    distance_km: 3.1,
    type_code: null,
    manufacturer: null,
    model: null,
    category: null,
    category_label: null,
    category_description: null,
    display_type: null,
    ...overrides,
  };
}

function makeLoggedFlight(overrides: Partial<ApiLoggedFlight> = {}): ApiLoggedFlight {
  return {
    id: 1,
    created_at: "2026-03-28T12:00:00Z",
    flight_time: "2026-03-28T10:00:00Z",
    icao24: "abc123",
    callsign: "LOG1",
    note: "Nice sighting",
    aircraft_latitude: -37.8,
    aircraft_longitude: 144.9,
    logger_latitude: null,
    logger_longitude: null,
    owner_uuid: null,
    owner_id: 1,
    owner_username: "pilot",
    heading: null,
    type_code: null,
    manufacturer: null,
    model: null,
    category: null,
    category_label: null,
    category_description: null,
    display_type: null,
    photos: [],
    distance_km: 1.2,
    is_owner: true,
    trajectory: null,
    ...overrides,
  };
}

describe("FlightListPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders live flights in live mode", () => {
    const flight = makeLiveFlight({ callsign: "QF101" });
    const wrapper = mount(FlightListPanel, {
      props: {
        mode: "live",
        liveFlights: [flight],
        loggedFlights: [],
        selectedLogId: null,
      },
    });
    expect(wrapper.text()).toContain("QF101");
    expect(wrapper.text()).toContain("Live Flight");
  });

  it("renders logged flights in logged mode", () => {
    const flight = makeLoggedFlight({ callsign: "VA456" });
    const wrapper = mount(FlightListPanel, {
      props: {
        mode: "logged",
        liveFlights: [],
        loggedFlights: [flight],
        selectedLogId: null,
      },
    });
    expect(wrapper.text()).toContain("VA456");
    expect(wrapper.text()).toContain("Logged Flight");
  });

  it("shows empty list when no flights", () => {
    const wrapper = mount(FlightListPanel, {
      props: {
        mode: "live",
        liveFlights: [],
        loggedFlights: [],
        selectedLogId: null,
      },
    });
    expect(wrapper.findAll("article")).toHaveLength(0);
  });

  it("emits report event when Report button is clicked on a live flight", async () => {
    const flight = makeLiveFlight();
    const wrapper = mount(FlightListPanel, {
      props: {
        mode: "live",
        liveFlights: [flight],
        loggedFlights: [],
        selectedLogId: null,
      },
    });
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("report")).toBeTruthy();
    expect(wrapper.emitted("report")?.[0]?.[0]).toMatchObject({ icao24: "abc123" });
  });

  it("emits selectLog event when View details is clicked on a logged flight", async () => {
    const flight = makeLoggedFlight({ id: 42 });
    const wrapper = mount(FlightListPanel, {
      props: {
        mode: "logged",
        liveFlights: [],
        loggedFlights: [flight],
        selectedLogId: null,
      },
    });
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("selectLog")).toEqual([[42]]);
  });

  it("labels own log as 'Your log' and others as 'Community log'", () => {
    const own = makeLoggedFlight({ id: 1, is_owner: true, callsign: "OWN1" });
    const community = makeLoggedFlight({ id: 2, is_owner: false, callsign: "COM1" });
    const wrapper = mount(FlightListPanel, {
      props: {
        mode: "logged",
        liveFlights: [],
        loggedFlights: [own, community],
        selectedLogId: null,
      },
    });
    expect(wrapper.text()).toContain("Your log");
    expect(wrapper.text()).toContain("Community log");
  });
});
