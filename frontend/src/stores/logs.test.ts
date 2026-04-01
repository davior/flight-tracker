import { createPinia, setActivePinia } from "pinia";

import * as api from "@/lib/api";
import { useIdentityStore } from "@/stores/identity";
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
    const identityStore = useIdentityStore();
    const uiStore = useUiStore();

    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });
    uiStore.timeWindow = "1d";
    identityStore.ensureIdentity();

    const fetchLoggedFlightsSpy = vi.spyOn(api, "fetchLoggedFlights").mockResolvedValue([]);

    await logsStore.refresh();

    expect(fetchLoggedFlightsSpy).toHaveBeenCalledWith({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      timeWindow: "1d",
      viewerUuid: expect.any(String),
    });
  });

  it("skips oversized bounds queries that the backend would reject", async () => {
    const logsStore = useLogsStore();
    const mapStore = useMapStore();

    mapStore.setBounds({ north: 85, south: -85, east: 179, west: -179 });

    const fetchLoggedFlightsSpy = vi.spyOn(api, "fetchLoggedFlights").mockResolvedValue([]);

    await logsStore.refresh();

    expect(fetchLoggedFlightsSpy).not.toHaveBeenCalled();
    expect(logsStore.error).toBe("Zoom in to load nearby logs within 100 km.");
  });
});
