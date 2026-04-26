import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

import { ApiError, fetchFlightTrajectory, fetchLiveFlightCapabilities, fetchLiveFlights, fetchProviderStatus } from "@/lib/api";
import type { ApiLiveFlight, ApiLiveFlightCapabilities, ApiProviderStatus, ApiTrajectoryPoint } from "@/types/api";
import { useMapStore } from "./map";
import { useUiStore } from "./ui";

const DEFAULT_POLL_INTERVAL_MS = 30_000;
const RATE_LIMIT_BACKOFF_STEPS_MS = [60_000, 120_000, 300_000, 600_000] as const;

type RefreshReason = "poll" | "viewport" | "manual";

export const useFlightsStore = defineStore("flights", () => {
  const liveFlights = ref<ApiLiveFlight[]>([]);
  const liveTrajectory = ref<ApiTrajectoryPoint[]>([]);
  const isLoadingTrajectory = ref(false);
  const liveCapabilities = ref<ApiLiveFlightCapabilities>({
    provider: "unknown",
    supports_history: false,
    max_history_minutes: 0,
    history_step_minutes: 1,
    supports_trajectory: false,
  });
  const providerStatus = ref<ApiProviderStatus | null>(null);
  const isLoading = ref(false);
  const isLoadingCapabilities = ref(false);
  const error = ref<string | null>(null);
  const capabilitiesError = ref<string | null>(null);
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
  const effectiveTimeShiftMinutes = computed(() => {
    const uiStore = useUiStore();
    return liveCapabilities.value.supports_history ? uiStore.liveTimeShiftMinutes : 0;
  });
  const coverageMessage = computed(() => {
    const mapStore = useMapStore();
    return mapStore.liveQuery?.isClamped
      ? "Showing live flights for the highlighted area. Visible coverage is limited to 500 km."
      : null;
  });

  async function loadCapabilities(): Promise<void> {
    isLoadingCapabilities.value = true;
    capabilitiesError.value = null;

    try {
      liveCapabilities.value = await fetchLiveFlightCapabilities();
      if (!liveCapabilities.value.supports_history) {
        const uiStore = useUiStore();
        uiStore.liveTimeShiftMinutes = 0;
      }
    } catch (nextError) {
      capabilitiesError.value = nextError instanceof Error ? nextError.message : "Unable to load live-flight capabilities";
      liveCapabilities.value = {
        provider: "unknown",
        supports_history: false,
        max_history_minutes: 0,
        history_step_minutes: 1,
      };
      const uiStore = useUiStore();
      uiStore.liveTimeShiftMinutes = 0;
    } finally {
      isLoadingCapabilities.value = false;
    }
  }

  async function loadProviderStatus(): Promise<void> {
    try {
      providerStatus.value = await fetchProviderStatus();
    } catch {
      // Status is best-effort — don't surface errors to the user
    }
  }

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

  function isLiveProviderRateLimitError(nextError: unknown): nextError is ApiError {
    return (
      nextError instanceof ApiError &&
      nextError.status === 502 &&
      typeof nextError.detail === "object" &&
      nextError.detail !== null &&
      "code" in nextError.detail &&
      nextError.detail.code === "live_provider_unavailable" &&
      "reason" in nextError.detail &&
      nextError.detail.reason === "rate_limited"
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
          timeShiftMinutes: effectiveTimeShiftMinutes.value,
        });
        resetRateLimitBackoff();
        void loadProviderStatus();
        if (pollingEnabled.value && isWindowActive.value) {
          scheduleNextPoll(DEFAULT_POLL_INTERVAL_MS);
        }
      } catch (nextError) {
        error.value = nextError instanceof Error ? nextError.message : "Unable to fetch live flights";
        void loadProviderStatus();
        if (isLiveProviderRateLimitError(nextError)) {
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

  async function loadTrajectory(icao24: string | null): Promise<void> {
    if (!icao24 || !liveCapabilities.value.supports_trajectory) {
      liveTrajectory.value = [];
      return;
    }
    isLoadingTrajectory.value = true;
    try {
      const result = await fetchFlightTrajectory(icao24);
      const points = result.supports_trajectory ? [...result.points] : [];

      // Inject current position from live data — no extra API call needed
      const currentFlight = liveFlights.value.find((f) => f.icao24 === icao24);
      if (currentFlight) {
        points.push({
          lat: currentFlight.latitude,
          lng: currentFlight.longitude,
          altitude: currentFlight.altitude,
          heading: currentFlight.heading,
          velocity: currentFlight.velocity,
          timestamp: currentFlight.last_contact ?? Math.floor(Date.now() / 1000),
        });
      }

      points.sort((left, right) => left.timestamp - right.timestamp);
      liveTrajectory.value = points;
    } catch {
      liveTrajectory.value = [];
    } finally {
      isLoadingTrajectory.value = false;
    }
  }

  // Watch for flight selection changes and fetch trajectory
  watch(
    () => useUiStore().selectedFlightIcao24,
    (icao24) => {
      void loadTrajectory(icao24);
    },
  );

  return {
    consecutiveRateLimitFailures,
    coverageMessage,
    capabilitiesError,
    error,
    effectiveTimeShiftMinutes,
    isLoading,
    isLoadingCapabilities,
    isLoadingTrajectory,
    isWindowActive,
    liveCapabilities,
    liveFlights,
    liveTrajectory,
    loadCapabilities,
    loadProviderStatus,
    loadTrajectory,
    nextAllowedPollAt,
    pollingHandle,
    pollingEnabled,
    providerStatus,
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
