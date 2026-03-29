import { defineStore } from "pinia";
import { ref } from "vue";

import type { ApiLiveFlight, AppMode, AppView, TimeWindow } from "@/types/api";

export const useUiStore = defineStore("ui", () => {
  const mode = ref<AppMode>("live");
  const view = ref<AppView>("map");
  const reportFlight = ref<ApiLiveFlight | null>(null);
  const selectedLogId = ref<number | null>(null);
  const filtersOpen = ref(false);
  const manualLocationOpen = ref(false);
  const toast = ref<string | null>(null);
  const timeWindow = ref<TimeWindow>("1d");

  function showToast(message: string): void {
    toast.value = message;
    window.setTimeout(() => {
      if (toast.value === message) {
        toast.value = null;
      }
    }, 2800);
  }

  return {
    filtersOpen,
    manualLocationOpen,
    mode,
    reportFlight,
    selectedLogId,
    showToast,
    timeWindow,
    toast,
    view,
  };
});
