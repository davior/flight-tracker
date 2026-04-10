import { mount } from "@vue/test-utils";

import BottomModeNav from "@/components/BottomModeNav.vue";

describe("BottomModeNav", () => {
  it("renders both mode buttons", () => {
    const wrapper = mount(BottomModeNav, { props: { mode: "live" } });
    expect(wrapper.text()).toContain("Live Flights");
    expect(wrapper.text()).toContain("Logged Flights");
  });

  it("highlights the live button when mode is live", () => {
    const wrapper = mount(BottomModeNav, { props: { mode: "live" } });
    const buttons = wrapper.findAll("button");
    const liveBtn = buttons.find((b) => b.text() === "Live Flights");
    const loggedBtn = buttons.find((b) => b.text() === "Logged Flights");
    expect(liveBtn?.classes()).toContain("bg-[var(--live)]");
    expect(loggedBtn?.classes()).not.toContain("bg-[var(--logged)]");
  });

  it("highlights the logged button when mode is logged", () => {
    const wrapper = mount(BottomModeNav, { props: { mode: "logged" } });
    const buttons = wrapper.findAll("button");
    const loggedBtn = buttons.find((b) => b.text() === "Logged Flights");
    expect(loggedBtn?.classes()).toContain("bg-[var(--logged)]");
  });

  it("emits update:mode with 'logged' when Logged Flights button is clicked", async () => {
    const wrapper = mount(BottomModeNav, { props: { mode: "live" } });
    const loggedBtn = wrapper.findAll("button").find((b) => b.text() === "Logged Flights");
    await loggedBtn?.trigger("click");
    expect(wrapper.emitted("update:mode")).toEqual([["logged"]]);
  });

  it("emits update:mode with 'live' when Live Flights button is clicked", async () => {
    const wrapper = mount(BottomModeNav, { props: { mode: "logged" } });
    const liveBtn = wrapper.findAll("button").find((b) => b.text() === "Live Flights");
    await liveBtn?.trigger("click");
    expect(wrapper.emitted("update:mode")).toEqual([["live"]]);
  });
});
