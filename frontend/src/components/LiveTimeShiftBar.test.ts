import { mount } from "@vue/test-utils";

import LiveTimeShiftBar from "@/components/LiveTimeShiftBar.vue";

describe("LiveTimeShiftBar", () => {
  it("renders the current time-shift label and emits 1-minute updates", async () => {
    const wrapper = mount(LiveTimeShiftBar, {
      props: {
        value: 1,
        disabled: false,
        helperText: "Showing flights from 1 min ago.",
      },
    });

    expect(wrapper.text()).toContain("1 min ago");
    expect(wrapper.text()).toContain("10m");

    await wrapper.get("input").setValue("17");
    await wrapper.setProps({ value: 17, helperText: "Showing flights from 17 min ago." });

    expect(wrapper.emitted("update:value")?.[0]).toEqual([17]);
    expect(wrapper.text()).toContain("17 min ago");
  });

  it("shows Now when the slider is at zero", () => {
    const wrapper = mount(LiveTimeShiftBar, {
      props: {
        value: 0,
        disabled: false,
        helperText: "Showing flights from now.",
      },
    });

    expect(wrapper.text()).toContain("Now");
  });

  it("supports a disabled explanatory state", () => {
    const wrapper = mount(LiveTimeShiftBar, {
      props: {
        value: 0,
        disabled: true,
        helperText: "Time shift unavailable for the current live provider.",
      },
    });

    expect(wrapper.get("input").attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("Unavailable");
    expect(wrapper.text()).toContain("Time shift unavailable for the current live provider.");
  });
});
