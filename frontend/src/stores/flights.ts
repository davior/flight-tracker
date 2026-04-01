import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { ApiError, fetchLiveFlights } from "@/lib/api";
import type { ApiLiveFlight } from "@/types/api";
import { useMapStore } from "./map";

const DEFAULT_POLL_INTERVAL_MS = 30_000;
const RATE_LIMIT_BACKOFF_STEPS_MS = [60_000, 120_000, 300_000, 600_000] as const;

type RefreshReason = "poll" | "viewport" | "manual";

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
  let queuedRefreshReason: RefreshReason | null = null;

  const sortedFlights = computed(() =>
    [...liveFlights.value].sort((left, right) => left.distance_km - right.distance_km),
  );
  const coverageMessage = computed(() => {
    const mapStore = useMapStore();
    return mapStore.liveQuery?.isClamped
      ? "Showing live flights for the highlighted area. Zoom in to cover more of the visible map."
      : null;
  });

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

  function isBackoffExpired(): boolean {
    return nextAllowedPollAt.value === null || Date.now() >= nextAllowedPollAt.value;
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
      void refresh("poll");
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

  function canRefresh(reason: RefreshReason): boolean {
    if (!isWindowActive.value) {
      return false;
    }
    if (reason === "poll") {
      return shouldPollNow();
    }
    return isBackoffExpired();
  }

  function queueRefresh(reason: RefreshReason): void {
    if (queuedRefreshReason === "manual") {
      return;
    }
    if (queuedRefreshReason === "viewport" && reason === "poll") {
      return;
    }
    queuedRefreshReason = reason;
  }

  async function refresh(reason: RefreshReason = "manual"): Promise<void> {
    if (activeRequest) {
      queueRefresh(reason);
      return activeRequest;
    }

    const mapStore = useMapStore();
    if (!mapStore.liveQuery || !canRefresh(reason)) {
      return;
    }

    const query = mapStore.liveQuery;
    if (!query) {
      return;
    }

    activeRequest = (async () => {
      isLoading.value = true;
      error.value = null;
      try {
        liveFlights.value = await fetchLiveFlights({
          bounds: query.queryBounds,
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
        if (queuedRefreshReason) {
          const nextReason = queuedRefreshReason;
          queuedRefreshReason = null;
          void refresh(nextReason);
        }
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
    coverageMessage,
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
