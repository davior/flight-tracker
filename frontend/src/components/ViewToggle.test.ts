import { mount } from "@vue/test-utils";

import ViewToggle from "@/components/ViewToggle.vue";

describe("ViewToggle", () => {
  it("emits updates when the user switches view", async () => {
    const wrapper = mount(ViewToggle, {
      props: {
        view: "map",
      },
    });

    await wrapper.get("button:last-child").trigger("click");

    expect(wrapper.emitted("update:view")?.[0]).toEqual(["list"]);
  });
});
