import { loadOrCreateIdentity } from "@/lib/identity";

describe("loadOrCreateIdentity", () => {
  it("persists and reuses a local uuid", () => {
    window.localStorage.clear();

    const first = loadOrCreateIdentity();
    const second = loadOrCreateIdentity();

    expect(first).toBeTruthy();
    expect(first).toBe(second);
  });
});
