import { loadToken } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function adminFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = loadToken();
  const response = await fetch(`${API_BASE}/admin${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (typeof payload.detail === "string") message = payload.detail;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  is_verified: boolean;
  is_admin: boolean;
  is_active: boolean;
  tutorial_seen: boolean;
  created_at: string;
  flight_log_count: number;
}

export interface AdminUserListResponse {
  total: number;
  page: number;
  per_page: number;
  items: AdminUser[];
}

export interface MetricsOverview {
  total_users: number;
  active_users: number;
  admin_users: number;
  total_flight_logs: number;
  requests_today: number;
  unique_visitors_today: number;
  requests_last_7_days: number;
}

export interface DailyMetricPoint {
  date: string;
  value: number;
}

export interface RequestLogItem {
  id: number;
  ip_address: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  user_id: number | null;
  requested_at: string;
}

export interface RequestLogListResponse {
  total: number;
  page: number;
  per_page: number;
  items: RequestLogItem[];
}

export interface IpBlock {
  ip_address: string;
  reason: string | null;
  blocked_at: string;
  release_at: string | null;
  auto_blocked: boolean;
  blocked_by_user_id: number | null;
}

export interface DataSyncStatus {
  source: string;
  last_synced_at: string | null;
  last_sync_status: string | null;
  row_count: number | null;
}

export interface ApiProviderStat {
  provider: string;
  total: number;
  successes: number;
  errors: number;
}

export interface AiQueryResponse {
  answer: string;
  chart_type: string | null;
  chart_data: { labels: string[]; datasets: { label: string; data: number[] }[] } | null;
  model_used: string | null;
}

// Users
export const getUsers = (page = 1, search = "") =>
  adminFetch<AdminUserListResponse>(`/users?page=${page}&search=${encodeURIComponent(search)}`);

export const getUser = (id: number) => adminFetch<AdminUser>(`/users/${id}`);

export const createUser = (data: { email: string; username: string; password: string; is_admin: boolean }) =>
  adminFetch<AdminUser>("/users", { method: "POST", body: JSON.stringify(data) });

export const updateUser = (id: number, data: Partial<AdminUser>) =>
  adminFetch<AdminUser>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteUser = (id: number) => adminFetch<void>(`/users/${id}`, { method: "DELETE" });

export const setUserPassword = (id: number, password: string) =>
  adminFetch<{ message: string }>(`/users/${id}/set-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: password }),
  });

export const sendPasswordReset = (id: number) =>
  adminFetch<{ message: string }>(`/users/${id}/send-reset`, { method: "POST" });

// Metrics
export const getMetricsOverview = () => adminFetch<MetricsOverview>("/metrics/overview");
export const getDailyVisitors = (days = 30) => adminFetch<DailyMetricPoint[]>(`/metrics/daily-visitors?days=${days}`);
export const getDailyRequests = (days = 30) => adminFetch<DailyMetricPoint[]>(`/metrics/daily-requests?days=${days}`);
export const getApiCallStats = (days = 7) => adminFetch<ApiProviderStat[]>(`/metrics/api-calls?days=${days}`);

// Logs
export const getRequestLogs = (page = 1, ip = "", path = "", status = 0) => {
  const params = new URLSearchParams({ page: String(page) });
  if (ip) params.set("ip", ip);
  if (path) params.set("path", path);
  if (status) params.set("status", String(status));
  return adminFetch<RequestLogListResponse>(`/logs/requests?${params}`);
};

export const getBlockedIps = () => adminFetch<IpBlock[]>("/logs/blocked-ips");
export const blockIp = (ip: string, reason?: string, releaseHours?: number) =>
  adminFetch<IpBlock>("/logs/blocked-ips", {
    method: "POST",
    body: JSON.stringify({ ip_address: ip, reason, release_hours: releaseHours }),
  });
export const unblockIp = (ip: string) => adminFetch<void>(`/logs/blocked-ips/${encodeURIComponent(ip)}`, { method: "DELETE" });
export const analyzeThreats = () => adminFetch<AiQueryResponse>("/logs/analyze-threats", { method: "POST" });

// Data sync
export const getDataSyncStatus = () => adminFetch<DataSyncStatus[]>("/data-sync");
export const triggerSync = (source: string) =>
  adminFetch<{ source: string; message: string }>(`/data-sync/${source}/trigger`, { method: "POST" });

// AI
export const aiQuery = (question: string, contextHint?: string) =>
  adminFetch<AiQueryResponse>("/ai/query", {
    method: "POST",
    body: JSON.stringify({ question, context_hint: contextHint }),
  });
export const getAiProviders = () => adminFetch<{ configured_provider: string; api_key_set: boolean; available_providers: { id: string; label: string }[] }>("/ai/providers");
