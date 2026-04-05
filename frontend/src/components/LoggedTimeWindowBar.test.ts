import { mount } from "@vue/test-utils";

import LoggedTimeWindowBar from "@/components/LoggedTimeWindowBar.vue";

describe("LoggedTimeWindowBar", () => {
  it("renders the current logged time window label and emits 0.5-day updates", async () => {
    const wrapper = mount(LoggedTimeWindowBar, {
      props: {
        value: 1.5,
      },
    });

    expect(wrapper.text()).toContain("Showing logs from last 1.5 days");
    expect(wrapper.text()).toContain("14d");

    await wrapper.get("input").setValue("7");
    await wrapper.setProps({ value: 7 });

    expect(wrapper.emitted("update:value")?.[0]).toEqual([7]);
    expect(wrapper.text()).toContain("Showing logs from last 7 days");
  });

  it("formats the minimum value as hours", () => {
    const wrapper = mount(LoggedTimeWindowBar, {
      props: {
        value: 0.5,
      },
    });

    expect(wrapper.text()).toContain("Showing logs from last 12 hours");
  });
});
