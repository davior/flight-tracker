import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, vi } from "vitest";

import { ApiError } from "@/lib/api";
import * as api from "@/lib/api";
import { useFlightsStore } from "@/stores/flights";
import { useMapStore } from "@/stores/map";

describe("useFlightsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  it("starts and stops polling cleanly", () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });

    flightsStore.startPolling();
    expect(flightsStore.pollingHandle).not.toBeNull();

    flightsStore.stopPolling();
    expect(flightsStore.pollingHandle).toBeNull();
  });

  it("does not schedule polling while the window is inactive", () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });

    flightsStore.setWindowActive(false);
    flightsStore.startPolling();

    expect(flightsStore.pollingHandle).toBeNull();
  });

  it("backs off after OpenSky rate limits and resets after a success", async () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });

    const fetchLiveFlightsSpy = vi
      .spyOn(api, "fetchLiveFlights")
      .mockRejectedValueOnce(
        new ApiError("OpenSky responded with status 429", 502, {
          code: "opensky_unavailable",
          message: "OpenSky responded with status 429",
        }),
      )
      .mockResolvedValueOnce([]);

    flightsStore.startPolling();
    await vi.runOnlyPendingTimersAsync();

    expect(flightsStore.consecutiveRateLimitFailures).toBe(1);
    expect(flightsStore.error).toBe("OpenSky responded with status 429");
    expect(flightsStore.pollingHandle).not.toBeNull();

    await vi.advanceTimersByTimeAsync(60_000);

    expect(fetchLiveFlightsSpy).toHaveBeenCalledTimes(2);
    expect(flightsStore.consecutiveRateLimitFailures).toBe(0);
    expect(flightsStore.error).toBeNull();
    expect(flightsStore.pollingHandle).not.toBeNull();
  });
});
