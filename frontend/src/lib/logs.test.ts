import { sortLoggedFlightsNearestFirst } from "@/lib/logs";
import type { ApiLoggedFlight } from "@/types/api";

function makeLog(id: number, distance: number, createdAt: string, flightTime: string): ApiLoggedFlight {
  return {
    id,
    created_at: createdAt,
    flight_time: flightTime,
    icao24: "abc123",
    callsign: null,
    note: null,
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
    distance_km: distance,
    is_owner: false,
  };
}

describe("sortLoggedFlightsNearestFirst", () => {
  it("sorts by distance and then by newest first", () => {
    const sorted = sortLoggedFlightsNearestFirst([
      makeLog(1, 5, "2026-03-28T10:00:00Z", "2026-03-28T10:00:00Z"),
      makeLog(2, 2, "2026-03-28T12:00:00Z", "2026-03-28T09:00:00Z"),
      makeLog(3, 2, "2026-03-28T08:00:00Z", "2026-03-28T11:00:00Z"),
    ]);

    expect(sorted.map((item) => item.id)).toEqual([3, 2, 1]);
  });
});
