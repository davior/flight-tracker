import type {
  ApiCreatedLog,
  ApiLiveFlight,
  ApiLiveFlightCapabilities,
  ApiLoggedFlight,
  ApiProviderStatus,
  ApiTrajectoryResponse,
  CreateLogFields,
  LoggedTimeWindowDays,
  MapBounds,
} from "@/types/api";
import type { AuthUser } from "@/types/auth";
import { clearToken, loadToken } from "@/lib/auth";

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
  const token = loadToken();
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }

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
  bounds: MapBounds;
  timeShiftMinutes: number;
}): Promise<ApiLiveFlight[]> {
  const search = new URLSearchParams({
    north: params.bounds.north.toString(),
    south: params.bounds.south.toString(),
    east: params.bounds.east.toString(),
    west: params.bounds.west.toString(),
    time_shift_minutes: params.timeShiftMinutes.toString(),
  });
  return fetchJson<ApiLiveFlight[]>(`/flights/nearby?${search.toString()}`);
}

export async function fetchLiveFlightCapabilities(): Promise<ApiLiveFlightCapabilities> {
  return fetchJson<ApiLiveFlightCapabilities>("/flights/capabilities");
}

export async function fetchProviderStatus(): Promise<ApiProviderStatus> {
  return fetchJson<ApiProviderStatus>("/flights/provider-status");
}

export async function fetchLoggedFlights(params: {
  bounds: MapBounds;
  timeWindowDays: LoggedTimeWindowDays;
}): Promise<ApiLoggedFlight[]> {
  const search = new URLSearchParams({
    north: params.bounds.north.toString(),
    south: params.bounds.south.toString(),
    east: params.bounds.east.toString(),
    west: params.bounds.west.toString(),
    time_window_days: params.timeWindowDays.toString(),
  });
  return fetchJson<ApiLoggedFlight[]>(`/logs/nearby?${search.toString()}`);
}

export async function fetchFlightTrajectory(
  icao24: string,
  opts: {
    maxHistoryMinutes?: number;
    stepMinutes?: number;
    timeShiftMinutes?: number;
  } = {},
): Promise<ApiTrajectoryResponse> {
  const search = new URLSearchParams({ icao24 });
  if (opts.maxHistoryMinutes !== undefined) {
    search.set("max_history_minutes", opts.maxHistoryMinutes.toString());
  }
  if (opts.stepMinutes !== undefined) {
    search.set("step_minutes", opts.stepMinutes.toString());
  }
  if (opts.timeShiftMinutes !== undefined) {
    search.set("time_shift_minutes", opts.timeShiftMinutes.toString());
  }
  return fetchJson<ApiTrajectoryResponse>(`/flights/${icao24}/trajectory?${search.toString()}`);
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

  return fetchJson<ApiCreatedLog>("/logs", {
    method: "POST",
    body: formData,
  });
}

export async function deleteLog(id: number): Promise<void> {
  const token = loadToken();
  const response = await fetch(buildApiUrl(`/logs/${id}`), {
    method: "DELETE",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }
  if (!response.ok) {
    throw new ApiError(`Failed to delete log`, response.status);
  }
}

export async function patchLog(id: number, note: string | null): Promise<ApiCreatedLog> {
  return fetchJson<ApiCreatedLog>(`/logs/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
}

export async function updateProfile(payload: {
  username?: string;
  current_password?: string;
  new_password?: string;
}): Promise<AuthUser> {
  return fetchJson<AuthUser>("/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
