import { mount } from "@vue/test-utils";

import FloatingControls from "@/components/FloatingControls.vue";

describe("FloatingControls", () => {
  it("emits the location event from the target icon button", async () => {
    const wrapper = mount(FloatingControls, {
      props: {
        buttonLabel: "Filters",
        showFiltersButton: true,
      },
    });

    await wrapper.get('button[aria-label="Location settings"]').trigger("click");

    expect(wrapper.emitted("location")?.[0]).toEqual([]);
  });

  it("hides the filters button when disabled", () => {
    const wrapper = mount(FloatingControls, {
      props: {
        buttonLabel: "Filters",
        showFiltersButton: false,
      },
    });

    expect(wrapper.text()).not.toContain("Filters");
  });
});
