import { ApiError, fetchLiveFlights } from "@/lib/api";

describe("fetchLiveFlights", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("preserves structured backend detail for JSON errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "opensky_unavailable",
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
        lat: -37.8136,
        lon: 144.9631,
        radiusKm: 20,
      }),
    ).rejects.toMatchObject<ApiError>({
      status: 502,
      message: "OpenSky responded with status 429",
      detail: {
        code: "opensky_unavailable",
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
        lat: -37.8136,
        lon: 144.9631,
        radiusKm: 20,
      }),
    ).rejects.toMatchObject<ApiError>({
      status: 502,
      message: "Bad Gateway",
    });
  });
});
