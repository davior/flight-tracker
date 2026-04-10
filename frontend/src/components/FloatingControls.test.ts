import { mount } from "@vue/test-utils";

import FloatingControls from "@/components/FloatingControls.vue";

describe("FloatingControls", () => {
  it("emits the location event when location button is clicked", async () => {
    const wrapper = mount(FloatingControls);

    await wrapper.get('button[aria-label="Location settings"]').trigger("click");

    expect(wrapper.emitted("location")?.[0]).toEqual([]);
  });

  it("emits the refresh event when refresh button is clicked", async () => {
    const wrapper = mount(FloatingControls);

    await wrapper.get('button[aria-label="Refresh"]').trigger("click");

    expect(wrapper.emitted("refresh")?.[0]).toEqual([]);
  });

  it("renders both location and refresh buttons", () => {
    const wrapper = mount(FloatingControls);

    expect(wrapper.find('button[aria-label="Location settings"]').exists()).toBe(true);
    expect(wrapper.find('button[aria-label="Refresh"]').exists()).toBe(true);
  });
});
