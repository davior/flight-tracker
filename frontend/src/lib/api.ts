import type { ApiCreatedLog, ApiLiveFlight, ApiLoggedFlight, CreateLogFields, TimeWindow } from "@/types/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function buildApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    let detail: unknown;
    let message = `Request failed with status ${response.status}`;

    if (contentType.includes("application/json")) {
      try {
        const payload = (await response.json()) as { detail?: unknown; message?: string };
        detail = payload.detail;

        if (typeof payload.message === "string" && payload.message) {
          message = payload.message;
        } else if (typeof payload.detail === "string" && payload.detail) {
          message = payload.detail;
        } else if (
          payload.detail &&
          typeof payload.detail === "object" &&
          "message" in payload.detail &&
          typeof payload.detail.message === "string"
        ) {
          message = payload.detail.message;
        }
      } catch {
        message = `Request failed with status ${response.status}`;
      }
    } else {
      const text = await response.text();
      if (text) {
        message = text;
      }
    }

    throw new ApiError(message, response.status, detail);
  }

  return (await response.json()) as T;
}

export async function fetchLiveFlights(params: {
  lat: number;
  lon: number;
  radiusKm: number;
}): Promise<ApiLiveFlight[]> {
  const search = new URLSearchParams({
    lat: params.lat.toString(),
    lon: params.lon.toString(),
    radius_km: params.radiusKm.toFixed(3),
  });
  return fetchJson<ApiLiveFlight[]>(`/flights/nearby?${search.toString()}`);
}

export async function fetchLoggedFlights(params: {
  lat: number;
  lon: number;
  radiusKm: number;
  timeWindow: TimeWindow;
  viewerUuid: string;
}): Promise<ApiLoggedFlight[]> {
  const search = new URLSearchParams({
    lat: params.lat.toString(),
    lon: params.lon.toString(),
    radius_km: params.radiusKm.toFixed(3),
    time_window: params.timeWindow,
    viewer_uuid: params.viewerUuid,
  });
  return fetchJson<ApiLoggedFlight[]>(`/logs/nearby?${search.toString()}`);
}

export async function createFlightLog(fields: CreateLogFields, files: File[]): Promise<ApiCreatedLog> {
  const formData = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") {
      return;
    }
    formData.append(key, String(value));
  });
  files.forEach((file) => formData.append("photos", file));

  return fetchJson<ApiLoggedFlight>("/logs", {
    method: "POST",
    body: formData,
  });
}
