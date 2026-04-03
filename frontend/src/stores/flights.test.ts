import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, vi } from "vitest";

import { ApiError } from "@/lib/api";
import * as api from "@/lib/api";
import { MAX_NEARBY_RADIUS_KM, deriveRadiusFromBounds } from "@/lib/geo";
import { useFlightsStore } from "@/stores/flights";
import { useMapStore } from "@/stores/map";
import { useUiStore } from "@/stores/ui";

describe("useFlightsStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts and stops polling cleanly", () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });

    flightsStore.startPolling();
    expect(flightsStore.pollingHandle).not.toBeNull();

    flightsStore.stopPolling();
    expect(flightsStore.pollingHandle).toBeNull();
  });

  it("does not schedule polling while the window is inactive", () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });

    flightsStore.setWindowActive(false);
    flightsStore.startPolling();

    expect(flightsStore.pollingHandle).toBeNull();
  });

  it("backs off after live-provider rate limits and resets after a success", async () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });
    flightsStore.liveCapabilities = {
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    };

    const fetchLiveFlightsSpy = vi
      .spyOn(api, "fetchLiveFlights")
      .mockRejectedValueOnce(
        new ApiError("OpenSky responded with status 429", 502, {
          code: "live_provider_unavailable",
          provider: "opensky",
          reason: "rate_limited",
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

  it("refreshes immediately for viewport changes without waiting for the poll interval", async () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });
    flightsStore.liveCapabilities = {
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    };
    useUiStore().liveTimeShiftMinutes = 15;

    const fetchLiveFlightsSpy = vi.spyOn(api, "fetchLiveFlights").mockResolvedValue([]);

    await flightsStore.refresh("viewport");

    expect(fetchLiveFlightsSpy).toHaveBeenCalledWith({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      timeShiftMinutes: 15,
    });
  });

  it("clamps oversized visible bounds to a centered live coverage box", async () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setBounds({
      north: -29,
      south: -40,
      east: 151,
      west: 138,
    });
    flightsStore.liveCapabilities = {
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    };

    const fetchLiveFlightsSpy = vi.spyOn(api, "fetchLiveFlights").mockResolvedValue([]);

    await flightsStore.refresh("viewport");

    expect(fetchLiveFlightsSpy).toHaveBeenCalledWith({
      bounds: mapStore.liveQuery?.queryBounds,
      timeShiftMinutes: 0,
    });
    expect(deriveRadiusFromBounds(mapStore.liveQuery!.queryBounds)).toBeLessThanOrEqual(MAX_NEARBY_RADIUS_KM);
    expect(flightsStore.coverageMessage).toBe("Showing live flights for the highlighted area. Visible coverage is limited to 500 km.");
    expect(flightsStore.error).toBeNull();
  });

  it("does not bypass the active rate-limit cooldown on viewport refresh", async () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });
    flightsStore.liveCapabilities = {
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    };

    const fetchLiveFlightsSpy = vi
      .spyOn(api, "fetchLiveFlights")
      .mockRejectedValueOnce(
        new ApiError("OpenSky responded with status 429", 502, {
          code: "live_provider_unavailable",
          provider: "opensky",
          reason: "rate_limited",
          message: "OpenSky responded with status 429",
        }),
      )
      .mockResolvedValueOnce([]);

    await flightsStore.refresh("viewport");
    await flightsStore.refresh("viewport");

    expect(fetchLiveFlightsSpy).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(60_000);
    await flightsStore.refresh("viewport");

    expect(fetchLiveFlightsSpy).toHaveBeenCalledTimes(2);
  });

  it("loads live-flight capabilities", async () => {
    const flightsStore = useFlightsStore();

    vi.spyOn(api, "fetchLiveFlightCapabilities").mockResolvedValue({
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    });

    await flightsStore.loadCapabilities();

    expect(flightsStore.liveCapabilities).toEqual({
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    });
    expect(flightsStore.capabilitiesError).toBeNull();
  });

  it("forces a zero time shift when history support is unavailable", async () => {
    const flightsStore = useFlightsStore();
    const mapStore = useMapStore();
    const uiStore = useUiStore();
    mapStore.setBounds({ north: -37.7, south: -37.9, east: 145.1, west: 144.8 });
    uiStore.liveTimeShiftMinutes = 20;
    flightsStore.liveCapabilities = {
      provider: "adsbx",
      supports_history: false,
      max_history_minutes: 0,
      history_step_minutes: 1,
    };

    const fetchLiveFlightsSpy = vi.spyOn(api, "fetchLiveFlights").mockResolvedValue([]);

    await flightsStore.refresh("manual");

    expect(fetchLiveFlightsSpy).toHaveBeenCalledWith({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      timeShiftMinutes: 0,
    });
  });
});
