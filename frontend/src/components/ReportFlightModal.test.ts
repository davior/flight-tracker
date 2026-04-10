import { mount } from "@vue/test-utils";

import ReportFlightModal from "@/components/ReportFlightModal.vue";
import type { ApiLiveFlight } from "@/types/api";

function makeFlight(overrides: Partial<ApiLiveFlight> = {}): ApiLiveFlight {
  return {
    icao24: "abc123",
    callsign: "QF101",
    origin_country: "AU",
    latitude: -37.8,
    longitude: 144.9,
    altitude: 5000,
    velocity: 250,
    heading: 90,
    vertical_rate: 0,
    last_contact: null,
    distance_km: 2.0,
    type_code: "B738",
    manufacturer: "Boeing",
    model: "737-800",
    category: "L",
    category_label: "Large",
    category_description: null,
    display_type: "Boeing 737-800",
    ...overrides,
  };
}

describe("ReportFlightModal", () => {
  it("is hidden when open is false", () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: false, flight: makeFlight(), submitting: false },
    });
    expect(wrapper.find("[class*='absolute']").exists()).toBe(false);
  });

  it("is hidden when flight is null", () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: true, flight: null, submitting: false },
    });
    expect(wrapper.find("[class*='absolute']").exists()).toBe(false);
  });

  it("shows callsign as title when open", () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: true, flight: makeFlight({ callsign: "VA456" }), submitting: false },
    });
    expect(wrapper.text()).toContain("VA456");
  });

  it("shows aircraft display type when available", () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: true, flight: makeFlight({ display_type: "Boeing 737-800" }), submitting: false },
    });
    expect(wrapper.text()).toContain("Boeing 737-800");
  });

  it("emits submit with note and empty files when submitted", async () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: true, flight: makeFlight(), submitting: false },
    });
    const textarea = wrapper.find("textarea");
    await textarea.setValue("Great sighting!");
    const submitBtn = wrapper.findAll("button").find((b) => b.text() === "Submit report");
    await submitBtn?.trigger("click");
    expect(wrapper.emitted("submit")).toBeTruthy();
    const payload = wrapper.emitted("submit")?.[0]?.[0] as { note: string; files: File[] };
    expect(payload.note).toBe("Great sighting!");
    expect(payload.files).toHaveLength(0);
  });

  it("shows submitting state on the submit button", () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: true, flight: makeFlight(), submitting: true },
    });
    expect(wrapper.text()).toContain("Submitting...");
  });

  it("emits close when the close button is clicked", async () => {
    const wrapper = mount(ReportFlightModal, {
      props: { open: true, flight: makeFlight(), submitting: false },
    });
    await wrapper.find("button[aria-label='Close']").trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
  });
});
