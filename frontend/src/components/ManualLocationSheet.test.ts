import { mount } from "@vue/test-utils";

import ManualLocationSheet from "@/components/ManualLocationSheet.vue";

function findButtonByText(wrapper: ReturnType<typeof mount>, label: string) {
  return wrapper
    .findAll("button")
    .find((button) => button.text().includes(label));
}

describe("ManualLocationSheet", () => {
  it("emits the current input coordinates when the user confirms", async () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        displayLocation: { lat: -37.8136, lon: 144.9631 },
        selectingOnMap: true,
        locationMode: "manual",
      },
    });

    await findButtonByText(wrapper, "Ok")!.trigger("click");

    expect(wrapper.emitted("submit")?.[0]).toEqual([
      {
        lat: -37.8136,
        lon: 144.9631,
      },
    ]);
  });

  it("emits typed coordinates as numbers in manual mode", async () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        displayLocation: null,
        selectingOnMap: false,
        locationMode: "manual",
      },
    });

    const inputs = wrapper.findAll("input");
    await inputs[0].setValue("-37.81");
    await inputs[1].setValue("144.97");
    await findButtonByText(wrapper, "Ok")!.trigger("click");

    expect(wrapper.emitted("submit")?.[0]).toEqual([
      {
        lat: -37.81,
        lon: 144.97,
      },
    ]);
  });

  it("does not show the old select my location action", () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        displayLocation: { lat: -37.8136, lon: 144.9631 },
        selectingOnMap: true,
        locationMode: "manual",
      },
    });

    expect(wrapper.text()).not.toContain("Select my location");
    expect(wrapper.text()).toContain("Ok");
    expect(wrapper.text()).toContain("Cancel");
  });

  it("emits location mode changes and disables manual inputs in auto mode", async () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        displayLocation: { lat: -37.8136, lon: 144.9631 },
        selectingOnMap: false,
        locationMode: "auto",
      },
    });

    await findButtonByText(wrapper, "Use Auto Location")!.trigger("click");

    const inputs = wrapper.findAll("input");
    expect(inputs[0].attributes("disabled")).toBeDefined();
    expect(inputs[1].attributes("disabled")).toBeDefined();
    expect(wrapper.emitted("updateLocationMode")?.[0]).toEqual(["auto"]);
  });

  it("syncs the input values from the displayed location while dragging on the map", async () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        displayLocation: { lat: -37.8136, lon: 144.9631 },
        selectingOnMap: true,
        locationMode: "manual",
      },
    });

    await wrapper.setProps({
      displayLocation: { lat: -37.70001, lon: 145.12345 },
    });

    const inputs = wrapper.findAll("input");
    expect((inputs[0].element as HTMLInputElement).value).toBe("-37.70001");
    expect((inputs[1].element as HTMLInputElement).value).toBe("145.12345");
  });

  it("pins the sheet to the bottom on large screens too", () => {
    const wrapper = mount(ManualLocationSheet, {
      props: {
        open: true,
        displayLocation: { lat: -37.8136, lon: 144.9631 },
        selectingOnMap: true,
        locationMode: "manual",
      },
    });

    expect(wrapper.get("div.absolute").classes()).toContain("items-end");
    expect(wrapper.get("div.absolute").classes()).not.toContain("md:items-center");
  });
});
