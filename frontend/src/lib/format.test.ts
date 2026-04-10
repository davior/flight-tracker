import { formatTimestamp, formatUnixTimestamp } from "@/lib/format";

describe("formatTimestamp", () => {
  it("builds timestamps in the expected fixed order with timezone", () => {
    const formatted = formatTimestamp("2026-03-28T09:15:00.000Z");

    expect(formatted).toMatch(/^\d{1,2} [A-Z][a-z]{2} \d{4} \d{1,2}:\d{2} (AM|PM) .+$/);
  });

  it("treats timezone-naive ISO strings as UTC", () => {
    expect(formatTimestamp("2026-04-10T08:56:06")).toBe(formatTimestamp("2026-04-10T08:56:06Z"));
  });

  it("returns the original value for invalid timestamps", () => {
    expect(formatTimestamp("not-a-date")).toBe("not-a-date");
  });

  it("formats unix timestamps using the same output contract", () => {
    const formatted = formatUnixTimestamp(1712728920);

    expect(formatted).toMatch(/^\d{1,2} [A-Z][a-z]{2} \d{4} \d{1,2}:\d{2} (AM|PM) .+$/);
  });
});
