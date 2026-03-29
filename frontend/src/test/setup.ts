import { afterEach, vi } from "vitest";

afterEach(() => {
  vi.restoreAllMocks();
});

const storage = new Map<string, string>();

Object.defineProperty(window, "localStorage", {
  writable: true,
  value: {
    getItem: vi.fn((key: string) => storage.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      storage.set(key, value);
    }),
    removeItem: vi.fn((key: string) => {
      storage.delete(key);
    }),
    clear: vi.fn(() => {
      storage.clear();
    }),
  },
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

Object.defineProperty(URL, "createObjectURL", {
  writable: true,
  value: vi.fn(() => "blob:preview"),
});

Object.defineProperty(URL, "revokeObjectURL", {
  writable: true,
  value: vi.fn(),
});
