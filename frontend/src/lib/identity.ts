const STORAGE_KEY = "flight-logger:user-uuid";

export function loadOrCreateIdentity(): string {
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const generated =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `user-${Math.random().toString(36).slice(2, 12)}`;
  window.localStorage.setItem(STORAGE_KEY, generated);
  return generated;
}
