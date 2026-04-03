import { ApiError, fetchLiveFlightCapabilities, fetchLiveFlights, fetchLoggedFlights } from "@/lib/api";

describe("fetchLiveFlights", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("preserves structured backend detail for JSON errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "live_provider_unavailable",
            provider: "opensky",
            reason: "rate_limited",
            message: "OpenSky responded with status 429",
          },
        }),
        {
          status: 502,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(
      fetchLiveFlights({
        bounds: {
          north: -37.7,
          south: -37.9,
          east: 145.1,
          west: 144.8,
        },
        timeShiftMinutes: 0,
      }),
    ).rejects.toMatchObject<ApiError>({
      status: 502,
      message: "OpenSky responded with status 429",
      detail: {
        code: "live_provider_unavailable",
        provider: "opensky",
        reason: "rate_limited",
        message: "OpenSky responded with status 429",
      },
    });
  });

  it("falls back to plain-text error messages for non-JSON responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Bad Gateway", {
        status: 502,
        headers: {
          "Content-Type": "text/plain",
        },
      }),
    );

    await expect(
      fetchLiveFlights({
        bounds: {
          north: -37.7,
          south: -37.9,
          east: 145.1,
          west: 144.8,
        },
        timeShiftMinutes: 0,
      }),
    ).rejects.toMatchObject<ApiError>({
      status: 502,
      message: "Bad Gateway",
    });
  });

  it("encodes map bounds for live-flight requests", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    await fetchLiveFlights({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      timeShiftMinutes: 30,
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/flights/nearby?north=-37.7&south=-37.9&east=145.1&west=144.8&time_shift_minutes=30",
      expect.any(Object),
    );
  });

  it("fetches live-flight capabilities", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          provider: "opensky",
          supports_history: true,
          max_history_minutes: 60,
          history_step_minutes: 1,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(fetchLiveFlightCapabilities()).resolves.toEqual({
      provider: "opensky",
      supports_history: true,
      max_history_minutes: 60,
      history_step_minutes: 1,
    });

    expect(globalThis.fetch).toHaveBeenCalledWith("/api/flights/capabilities", expect.any(Object));
  });
});

describe("fetchLoggedFlights", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("encodes map bounds for logged-flight requests", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    await fetchLoggedFlights({
      bounds: {
        north: -37.7,
        south: -37.9,
        east: 145.1,
        west: 144.8,
      },
      timeWindow: "1d",
      viewerUuid: "viewer-1",
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/logs/nearby?north=-37.7&south=-37.9&east=145.1&west=144.8&time_window=1d&viewer_uuid=viewer-1",
      expect.any(Object),
    );
  });
});
