const AUTH_TOKEN_KEY = "flight-logger:auth-token";

export function loadToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function saveToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}
