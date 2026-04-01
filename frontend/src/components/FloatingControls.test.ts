import { mount } from "@vue/test-utils";

import FloatingControls from "@/components/FloatingControls.vue";

describe("FloatingControls", () => {
  it("emits the location event from the target icon button", async () => {
    const wrapper = mount(FloatingControls, {
      props: {
        modeLabel: "Filters",
      },
    });

    await wrapper.get('button[aria-label="Location settings"]').trigger("click");

    expect(wrapper.emitted("location")?.[0]).toEqual([]);
  });
});
