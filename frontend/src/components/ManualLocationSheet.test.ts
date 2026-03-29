import { mount } from "@vue/test-utils";

import ManualLocationSheet from "@/components/ManualLocationSheet.vue";

describe("ManualLocationSheet", () => {
  it("emits the current map center when the user confirms the target", async () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        currentCenter: { lat: -37.8136, lon: 144.9631 },
      },
    });

    await wrapper.get("button.bg-\\[var\\(--accent\\)\\]").trigger("click");

    expect(wrapper.emitted("useCenter")?.[0]).toEqual([]);
    expect(wrapper.text()).toContain("-37.81360, 144.96310");
  });

  it("emits typed coordinates as numbers", async () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        currentCenter: null,
      },
    });

    const inputs = wrapper.findAll("input");
    await inputs[0].setValue("-37.81");
    await inputs[1].setValue("144.97");
    await wrapper.get("button.bg-\\[var\\(--ink\\)\\]").trigger("click");

    expect(wrapper.emitted("submit")?.[0]).toEqual([
      {
        lat: -37.81,
        lon: 144.97,
      },
    ]);
  });
});
