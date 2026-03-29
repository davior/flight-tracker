import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { ApiError, fetchLiveFlights } from "@/lib/api";
import type { ApiLiveFlight } from "@/types/api";
import { useMapStore } from "./map";

const DEFAULT_POLL_INTERVAL_MS = 30_000;
const RATE_LIMIT_BACKOFF_STEPS_MS = [60_000, 120_000, 300_000, 600_000] as const;

export const useFlightsStore = defineStore("flights", () => {
  const liveFlights = ref<ApiLiveFlight[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const pollingHandle = ref<number | null>(null);
  const pollingEnabled = ref(false);
  const isWindowActive = ref(true);
  const consecutiveRateLimitFailures = ref(0);
  const nextAllowedPollAt = ref<number | null>(null);
  const lastRateLimitAt = ref<number | null>(null);
  let activeRequest: Promise<void> | null = null;

  const sortedFlights = computed(() =>
    [...liveFlights.value].sort((left, right) => left.distance_km - right.distance_km),
  );

  function clearPollingTimer(): void {
    if (pollingHandle.value !== null) {
      window.clearTimeout(pollingHandle.value);
      pollingHandle.value = null;
    }
  }

  function shouldPollNow(): boolean {
    if (!pollingEnabled.value || !isWindowActive.value) {
      return false;
    }
    if (nextAllowedPollAt.value === null) {
      return true;
    }
    return Date.now() >= nextAllowedPollAt.value;
  }

  function scheduleNextPoll(delayMs = DEFAULT_POLL_INTERVAL_MS): void {
    clearPollingTimer();
    if (!pollingEnabled.value || !isWindowActive.value) {
      return;
    }

    const waitMs =
      nextAllowedPollAt.value !== null ? Math.max(nextAllowedPollAt.value - Date.now(), delayMs) : delayMs;

    pollingHandle.value = window.setTimeout(() => {
      pollingHandle.value = null;
      void refresh();
    }, waitMs);
  }

  function resetRateLimitBackoff(): void {
    consecutiveRateLimitFailures.value = 0;
    nextAllowedPollAt.value = null;
    lastRateLimitAt.value = null;
  }

  function isOpenSkyRateLimitError(nextError: unknown): nextError is ApiError {
    return (
      nextError instanceof ApiError &&
      nextError.status === 502 &&
      typeof nextError.detail === "object" &&
      nextError.detail !== null &&
      "code" in nextError.detail &&
      nextError.detail.code === "opensky_unavailable" &&
      "message" in nextError.detail &&
      typeof nextError.detail.message === "string" &&
      nextError.detail.message.includes("status 429")
    );
  }

  function handleRateLimitFailure(): void {
    consecutiveRateLimitFailures.value += 1;
    lastRateLimitAt.value = Date.now();
    const backoffIndex = Math.min(consecutiveRateLimitFailures.value - 1, RATE_LIMIT_BACKOFF_STEPS_MS.length - 1);
    nextAllowedPollAt.value = Date.now() + RATE_LIMIT_BACKOFF_STEPS_MS[backoffIndex];
  }

  async function refresh(): Promise<void> {
    if (activeRequest) {
      return activeRequest;
    }

    const mapStore = useMapStore();
    if (!mapStore.query || !shouldPollNow()) {
      return;
    }

    const query = mapStore.query;
    if (!query) {
      return;
    }

    activeRequest = (async () => {
      isLoading.value = true;
      error.value = null;
      try {
        liveFlights.value = await fetchLiveFlights({
          lat: query.center.lat,
          lon: query.center.lon,
          radiusKm: query.radiusKm,
        });
        resetRateLimitBackoff();
        if (pollingEnabled.value && isWindowActive.value) {
          scheduleNextPoll(DEFAULT_POLL_INTERVAL_MS);
        }
      } catch (nextError) {
        error.value = nextError instanceof Error ? nextError.message : "Unable to fetch live flights";
        if (isOpenSkyRateLimitError(nextError)) {
          handleRateLimitFailure();
          if (pollingEnabled.value && isWindowActive.value) {
            scheduleNextPoll();
          }
        } else if (pollingEnabled.value && isWindowActive.value) {
          scheduleNextPoll(DEFAULT_POLL_INTERVAL_MS);
        }
      } finally {
        isLoading.value = false;
        activeRequest = null;
      }
    })();

    return activeRequest;
  }

  function startPolling(): void {
    pollingEnabled.value = true;
    clearPollingTimer();
    if (isWindowActive.value) {
      scheduleNextPoll(0);
    }
  }

  function stopPolling(): void {
    pollingEnabled.value = false;
    clearPollingTimer();
  }

  function setWindowActive(active: boolean): void {
    isWindowActive.value = active;
    if (!active) {
      clearPollingTimer();
      return;
    }
    if (pollingEnabled.value) {
      scheduleNextPoll(0);
    }
  }

  return {
    consecutiveRateLimitFailures,
    error,
    isLoading,
    isWindowActive,
    liveFlights,
    nextAllowedPollAt,
    pollingHandle,
    pollingEnabled,
    refresh,
    resetRateLimitBackoff,
    scheduleNextPoll,
    setWindowActive,
    shouldPollNow,
    sortedFlights,
    startPolling,
    stopPolling,
  };
});
