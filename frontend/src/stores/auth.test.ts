import { createPinia, setActivePinia } from "pinia";

import * as api from "@/lib/api";
import * as authLib from "@/lib/auth";
import { useAuthStore } from "@/stores/auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(authLib, "loadToken").mockReturnValue(null);
    vi.spyOn(authLib, "saveToken").mockImplementation(() => {});
    vi.spyOn(authLib, "clearToken").mockImplementation(() => {});
  });

  it("is not authenticated initially", () => {
    const store = useAuthStore();
    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
  });

  it("sets user and token on login", async () => {
    const store = useAuthStore();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: "tok-123",
          token_type: "bearer",
          user: { id: 1, email: "a@b.com", username: "pilot", is_verified: true, tutorial_seen: false },
        }),
      }),
    );

    await store.login("pilot", "pass");

    expect(store.isAuthenticated).toBe(true);
    expect(store.user?.username).toBe("pilot");
    expect(authLib.saveToken).toHaveBeenCalledWith("tok-123");
  });

  it("clears token and user on logout", async () => {
    const store = useAuthStore();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: "tok-123",
          token_type: "bearer",
          user: { id: 1, email: "a@b.com", username: "pilot", is_verified: true, tutorial_seen: false },
        }),
      }),
    );

    await store.login("pilot", "pass");
    store.logout();

    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
    expect(authLib.clearToken).toHaveBeenCalled();
  });

  it("needsVerification is true when authenticated but not verified", async () => {
    const store = useAuthStore();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: "tok",
          token_type: "bearer",
          user: { id: 1, email: "a@b.com", username: "pilot", is_verified: false, tutorial_seen: false },
        }),
      }),
    );

    await store.login("pilot", "pass");

    expect(store.isAuthenticated).toBe(true);
    expect(store.needsVerification).toBe(true);
  });

  it("needsTutorial is true when verified but tutorial not seen", async () => {
    const store = useAuthStore();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: "tok",
          token_type: "bearer",
          user: { id: 1, email: "a@b.com", username: "pilot", is_verified: true, tutorial_seen: false },
        }),
      }),
    );

    await store.login("pilot", "pass");

    expect(store.needsTutorial).toBe(true);
    expect(store.needsVerification).toBe(false);
  });

  it("initialize loads user from stored token", async () => {
    vi.spyOn(authLib, "loadToken").mockReturnValue("stored-tok");
    const store = useAuthStore();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ id: 2, email: "b@c.com", username: "spotter", is_verified: true, tutorial_seen: true }),
      }),
    );

    await store.initialize();

    expect(store.user?.username).toBe("spotter");
    expect(store.isAuthenticated).toBe(true);
  });

  it("initialize clears auth if stored token is invalid", async () => {
    vi.spyOn(authLib, "loadToken").mockReturnValue("bad-tok");
    const store = useAuthStore();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: "Unauthorized" }) }),
    );

    await store.initialize();

    expect(store.isAuthenticated).toBe(false);
    expect(authLib.clearToken).toHaveBeenCalled();
  });

  it("updateProfile updates the user in store", async () => {
    const store = useAuthStore();
    // seed the store with a logged in user
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            access_token: "tok",
            token_type: "bearer",
            user: { id: 1, email: "a@b.com", username: "pilot", is_verified: true, tutorial_seen: true },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: 1, email: "a@b.com", username: "newpilot", is_verified: true, tutorial_seen: true }),
        }),
    );

    await store.login("pilot", "pass");
    await store.updateProfile({ username: "newpilot" });

    expect(store.user?.username).toBe("newpilot");
  });
});
