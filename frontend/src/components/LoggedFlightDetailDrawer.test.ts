import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import LoggedFlightDetailDrawer from "@/components/LoggedFlightDetailDrawer.vue";
import { formatTimestamp } from "@/lib/format";
import * as api from "@/lib/api";
import type { ApiLoggedFlight } from "@/types/api";

function makeFlight(overrides: Partial<ApiLoggedFlight> = {}): ApiLoggedFlight {
  return {
    id: 1,
    created_at: "2026-03-28T12:00:00Z",
    flight_time: "2026-03-28T10:15:00Z",
    icao24: "abc123",
    callsign: "TEST123",
    note: "Low pass",
    aircraft_latitude: -37.8,
    aircraft_longitude: 144.9,
    logger_latitude: null,
    logger_longitude: null,
    owner_uuid: null,
    owner_id: 5,
    owner_username: "spotterone",
    type_code: null,
    manufacturer: null,
    model: null,
    category: null,
    category_label: null,
    category_description: null,
    display_type: null,
    photos: [],
    distance_km: 2.5,
    is_owner: false,
    trajectory: null,
    ...overrides,
  };
}

describe("LoggedFlightDetailDrawer", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("shows flight time and logged-by metadata", () => {
    const flightTime = "2026-03-28T10:15:00Z";
    const createdAt = "2026-03-28T12:00:00Z";
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ flight_time: flightTime, created_at: createdAt }) },
    });

    expect(wrapper.text()).toContain("Flight Time");
    expect(wrapper.text()).toContain(formatTimestamp(flightTime));
    expect(wrapper.text()).toContain(`Logged by spotterone at ${formatTimestamp(createdAt)}`);
  });

  it("does not show edit or delete buttons when not owner", () => {
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ is_owner: false }) },
    });
    expect(wrapper.text()).not.toContain("Edit note");
    expect(wrapper.text()).not.toContain("Delete");
  });

  it("shows edit and delete buttons when is_owner is true", () => {
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ is_owner: true }) },
    });
    expect(wrapper.text()).toContain("Edit note");
    expect(wrapper.text()).toContain("Delete");
  });

  it("shows edit textarea when Edit note is clicked", async () => {
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ is_owner: true, note: "original" }) },
    });
    const editBtn = wrapper.findAll("button").find((b) => b.text() === "Edit note");
    await editBtn?.trigger("click");
    const textarea = wrapper.find("textarea");
    expect(textarea.exists()).toBe(true);
    expect((textarea.element as HTMLTextAreaElement).value).toBe("original");
  });

  it("shows delete confirmation when Delete is clicked", async () => {
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ is_owner: true }) },
    });
    const deleteBtn = wrapper.findAll("button").find((b) => b.text() === "Delete");
    await deleteBtn?.trigger("click");
    expect(wrapper.text()).toContain("Delete this log?");
    expect(wrapper.text()).toContain("This cannot be undone.");
  });

  it("calls patchLog and hides editor on save", async () => {
    vi.spyOn(api, "patchLog").mockResolvedValue({} as any);
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ is_owner: true, note: "original" }) },
    });

    const editBtn = wrapper.findAll("button").find((b) => b.text() === "Edit note");
    await editBtn?.trigger("click");
    const textarea = wrapper.find("textarea");
    await textarea.setValue("updated note");

    const saveBtn = wrapper.findAll("button").find((b) => b.text() === "Save");
    await saveBtn?.trigger("click");
    await wrapper.vm.$nextTick();

    expect(api.patchLog).toHaveBeenCalledWith(1, "updated note");
  });

  it("calls deleteLog and emits close after confirmation", async () => {
    vi.spyOn(api, "deleteLog").mockResolvedValue(undefined);
    const wrapper = mount(LoggedFlightDetailDrawer, {
      props: { flight: makeFlight({ is_owner: true }) },
    });

    const deleteBtn = wrapper.findAll("button").find((b) => b.text() === "Delete");
    await deleteBtn?.trigger("click");

    const confirmBtn = wrapper.findAll("button").find((b) => b.text() === "Yes, delete");
    await confirmBtn?.trigger("click");
    await wrapper.vm.$nextTick();

    expect(api.deleteLog).toHaveBeenCalledWith(1);
    expect(wrapper.emitted("close")).toBeTruthy();
  });
});
