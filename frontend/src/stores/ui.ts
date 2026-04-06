import { defineStore } from "pinia";
import { ref } from "vue";

import type { ApiLiveFlight, AppMode, AppView, LoggedTimeWindowDays } from "@/types/api";

export type LocationMode = "auto" | "manual";

export const useUiStore = defineStore("ui", () => {
  const mode = ref<AppMode>("live");
  const view = ref<AppView>("map");
  const liveTimeShiftMinutes = ref(0);
  const loggedTimeWindowDays = ref<LoggedTimeWindowDays>(1);
  const reportFlight = ref<ApiLiveFlight | null>(null);
  const selectedLogId = ref<number | null>(null);
  const selectedFlightIcao24 = ref<string | null>(null);
  const manualLocationOpen = ref(false);
  const locationMode = ref<LocationMode>("auto");
  const toast = ref<string | null>(null);

  function showToast(message: string): void {
    toast.value = message;
    window.setTimeout(() => {
      if (toast.value === message) {
        toast.value = null;
      }
    }, 2800);
  }

  return {
    liveTimeShiftMinutes,
    loggedTimeWindowDays,
    locationMode,
    manualLocationOpen,
    mode,
    reportFlight,
    selectedFlightIcao24,
    selectedLogId,
    showToast,
    toast,
    view,
  };
});
