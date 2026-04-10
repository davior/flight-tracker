import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { deleteLog as apiDeleteLog, fetchLoggedFlights, patchLog as apiPatchLog } from "@/lib/api";
import { deriveRadiusFromBounds } from "@/lib/geo";
import { sortLoggedFlightsNearestFirst } from "@/lib/logs";
import type { ApiLoggedFlight } from "@/types/api";
import { useMapStore } from "./map";
import { useUiStore } from "./ui";

const MAX_QUERY_RADIUS_KM = 500;

export const useLogsStore = defineStore("logs", () => {
  const loggedFlights = ref<ApiLoggedFlight[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const sortedFlights = computed(() => sortLoggedFlightsNearestFirst(loggedFlights.value));

  async function refresh(): Promise<void> {
    const mapStore = useMapStore();
    const uiStore = useUiStore();
    if (!mapStore.query) {
      return;
    }

    const query = mapStore.query;
    if (!query) {
      return;
    }
    if (deriveRadiusFromBounds(query.bounds) > MAX_QUERY_RADIUS_KM) {
      error.value = `Zoom in to load nearby logs within ${MAX_QUERY_RADIUS_KM} km.`;
      return;
    }

    isLoading.value = true;
    error.value = null;
    try {
      loggedFlights.value = await fetchLoggedFlights({
        bounds: query.bounds,
        timeWindowDays: uiStore.loggedTimeWindowDays,
      });
    } catch (nextError) {
      error.value = nextError instanceof Error ? nextError.message : "Unable to fetch logged flights";
    } finally {
      isLoading.value = false;
    }
  }

  function byId(id: number | null): ApiLoggedFlight | null {
    if (id === null) {
      return null;
    }
    return loggedFlights.value.find((flight) => flight.id === id) ?? null;
  }

  async function deleteLogById(id: number): Promise<void> {
    await apiDeleteLog(id);
    loggedFlights.value = loggedFlights.value.filter((f) => f.id !== id);
  }

  async function patchLogNote(id: number, note: string | null): Promise<void> {
    await apiPatchLog(id, note);
    const index = loggedFlights.value.findIndex((f) => f.id === id);
    if (index !== -1) {
      loggedFlights.value[index] = { ...loggedFlights.value[index], note };
    }
  }

  return {
    byId,
    deleteLogById,
    error,
    isLoading,
    loggedFlights,
    patchLogNote,
    refresh,
    sortedFlights,
  };
});
