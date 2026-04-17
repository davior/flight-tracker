import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { AuthTokenResponse, AuthUser } from "@/types/auth";
import { clearToken, loadToken, saveToken } from "@/lib/auth";
import { updateProfile as apiUpdateProfile } from "@/lib/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function authFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = loadToken();
  const response = await fetch(`${API_BASE}${path}`, {
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
  return (await response.json()) as T;
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(null);
  const user = ref<AuthUser | null>(null);
  const isLoading = ref(true);

  const isAuthenticated = computed(() => !!token.value && !!user.value);
  const needsVerification = computed(() => isAuthenticated.value && !user.value?.is_verified);
  const needsTutorial = computed(
    () => isAuthenticated.value && user.value?.is_verified && !user.value?.tutorial_seen,
  );

  function _applyToken(response: AuthTokenResponse): void {
    token.value = response.access_token;
    user.value = response.user;
    saveToken(response.access_token);
  }

  function _clearAuth(): void {
    token.value = null;
    user.value = null;
    clearToken();
  }

  async function initialize(): Promise<void> {
    const stored = loadToken();
    if (!stored) {
      isLoading.value = false;
      return;
    }
    token.value = stored;
    try {
      const me = await authFetch<AuthUser>("/auth/me");
      user.value = me;
    } catch {
      _clearAuth();
    } finally {
      isLoading.value = false;
    }
  }

  async function login(loginValue: string, password: string): Promise<void> {
    const response = await authFetch<AuthTokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ login: loginValue, password }),
    });
    _applyToken(response);
  }

  async function register(email: string, username: string, password: string): Promise<{ message: string }> {
    return authFetch<{ message: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    });
  }

  async function verifyEmail(verifyToken: string): Promise<void> {
    const response = await authFetch<AuthTokenResponse>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token: verifyToken }),
    });
    _applyToken(response);
  }

  async function resendVerification(): Promise<void> {
    await authFetch("/auth/resend-verification", { method: "POST", body: "{}" });
  }

  async function forgotPassword(email: string): Promise<void> {
    await authFetch("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  async function resetPassword(resetToken: string, newPassword: string): Promise<void> {
    const response = await authFetch<AuthTokenResponse>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token: resetToken, new_password: newPassword }),
    });
    _applyToken(response);
  }

  async function loginWithGoogle(idToken: string): Promise<void> {
    const response = await authFetch<AuthTokenResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    });
    _applyToken(response);
  }

  async function markTutorialSeen(): Promise<void> {
    const updated = await authFetch<AuthUser>("/auth/me/tutorial-seen", { method: "PATCH" });
    user.value = updated;
  }

  async function updateProfile(payload: {
    username?: string;
    current_password?: string;
    new_password?: string;
  }): Promise<void> {
    const updated = await apiUpdateProfile(payload);
    user.value = updated;
  }

  function logout(): void {
    _clearAuth();
  }

  return {
    token,
    user,
    isLoading,
    isAuthenticated,
    needsVerification,
    needsTutorial,
    initialize,
    login,
    register,
    verifyEmail,
    resendVerification,
    forgotPassword,
    resetPassword,
    loginWithGoogle,
    markTutorialSeen,
    updateProfile,
    logout,
  };
});
