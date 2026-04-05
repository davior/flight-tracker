import { mount } from "@vue/test-utils";

import LoggedFlightPopup from "@/components/LoggedFlightPopup.vue";
import { formatTimestamp } from "@/lib/format";

describe("LoggedFlightPopup", () => {
  it("shows the flight_time timestamp", () => {
    const flightTime = "2026-03-28T10:15:00Z";
    const createdAt = "2026-03-28T12:00:00Z";
    const wrapper = mount(LoggedFlightPopup, {
      props: {
        flight: {
          id: 1,
          created_at: createdAt,
          flight_time: flightTime,
          icao24: "abc123",
          callsign: "TEST123",
          note: "Low pass",
          aircraft_latitude: -37.8,
          aircraft_longitude: 144.9,
          logger_latitude: null,
          logger_longitude: null,
          owner_uuid: null,
          type_code: null,
          manufacturer: null,
          model: null,
          category: null,
          category_label: null,
          category_description: null,
          display_type: null,
          photos: [],
          distance_km: 2.5,
          is_owner: false,
        },
      },
    });

    expect(wrapper.text()).toContain(formatTimestamp(flightTime));
    expect(wrapper.text()).not.toContain(formatTimestamp(createdAt));
  });
});
