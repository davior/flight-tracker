import { createPinia, setActivePinia } from "pinia";

import * as api from "@/lib/api";
import { useLogsStore } from "@/stores/logs";
import { useMapStore } from "@/stores/map";
import { useUiStore } from "@/stores/ui";

describe("useLogsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("requests logged flights with map bounds", async () => {
    const logsStore = useLogsStore();
    const mapStore = useMapStore();
    const uiStore = useUiStore();

    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });
    uiStore.loggedTimeWindowDays = 1;

    const fetchLoggedFlightsSpy = vi.spyOn(api, "fetchLoggedFlights").mockResolvedValue([]);

    await logsStore.refresh();

    expect(fetchLoggedFlightsSpy).toHaveBeenCalledWith({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      timeWindowDays: 1,
    });
  });

  it("skips oversized bounds queries that the backend would reject", async () => {
    const logsStore = useLogsStore();
    const mapStore = useMapStore();

    mapStore.setBounds({ north: 85, south: -85, east: 179, west: -179 });

    const fetchLoggedFlightsSpy = vi.spyOn(api, "fetchLoggedFlights").mockResolvedValue([]);

    await logsStore.refresh();

    expect(fetchLoggedFlightsSpy).not.toHaveBeenCalled();
    expect(logsStore.error).toBe("Zoom in to load nearby logs within 500 km.");
  });

  it("deleteLogById removes the flight from the store", async () => {
    const logsStore = useLogsStore();
    vi.spyOn(api, "deleteLog").mockResolvedValue(undefined);

    // Seed with two flights
    logsStore.loggedFlights = [
      { id: 1, icao24: "aaa", callsign: null, note: null, flight_time: "", created_at: "", aircraft_latitude: null, aircraft_longitude: null, logger_latitude: null, logger_longitude: null, owner_uuid: null, owner_id: 1, owner_username: null, heading: null, type_code: null, manufacturer: null, model: null, category: null, category_label: null, category_description: null, display_type: null, photos: [], distance_km: 1, is_owner: true, trajectory: null },
      { id: 2, icao24: "bbb", callsign: null, note: null, flight_time: "", created_at: "", aircraft_latitude: null, aircraft_longitude: null, logger_latitude: null, logger_longitude: null, owner_uuid: null, owner_id: 1, owner_username: null, heading: null, type_code: null, manufacturer: null, model: null, category: null, category_label: null, category_description: null, display_type: null, photos: [], distance_km: 2, is_owner: true, trajectory: null },
    ];

    await logsStore.deleteLogById(1);

    expect(api.deleteLog).toHaveBeenCalledWith(1);
    expect(logsStore.loggedFlights).toHaveLength(1);
    expect(logsStore.loggedFlights[0].id).toBe(2);
  });

  it("patchLogNote updates the note of the matching flight", async () => {
    const logsStore = useLogsStore();
    vi.spyOn(api, "patchLog").mockResolvedValue({} as any);

    logsStore.loggedFlights = [
      { id: 5, icao24: "ccc", callsign: null, note: "original", flight_time: "", created_at: "", aircraft_latitude: null, aircraft_longitude: null, logger_latitude: null, logger_longitude: null, owner_uuid: null, owner_id: 1, owner_username: null, heading: null, type_code: null, manufacturer: null, model: null, category: null, category_label: null, category_description: null, display_type: null, photos: [], distance_km: 1, is_owner: true, trajectory: null },
    ];

    await logsStore.patchLogNote(5, "updated");

    expect(api.patchLog).toHaveBeenCalledWith(5, "updated");
    expect(logsStore.loggedFlights[0].note).toBe("updated");
  });
});
