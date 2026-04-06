<script setup lang="ts">
import type { Map as LeafletMap } from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import BottomModeNav from "@/components/BottomModeNav.vue";
import FlightListPanel from "@/components/FlightListPanel.vue";
import FloatingControls from "@/components/FloatingControls.vue";
import LoggedFlightDetailDrawer from "@/components/LoggedFlightDetailDrawer.vue";
import LoggedTimeWindowBar from "@/components/LoggedTimeWindowBar.vue";
import LiveTimeShiftBar from "@/components/LiveTimeShiftBar.vue";
import ManualLocationSheet from "@/components/ManualLocationSheet.vue";
import MapShell from "@/components/MapShell.vue";
import ReportFlightModal from "@/components/ReportFlightModal.vue";
import ToastStack from "@/components/ToastStack.vue";
import ViewToggle from "@/components/ViewToggle.vue";
import { createFlightLog } from "@/lib/api";
import { useDebouncedTask } from "@/composables/useDebouncedTask";
import { useFlightsStore } from "@/stores/flights";
import { useIdentityStore } from "@/stores/identity";
import { useLogsStore } from "@/stores/logs";
import { useMapStore } from "@/stores/map";
import { useUiStore } from "@/stores/ui";

const identityStore = useIdentityStore();
const mapStore = useMapStore();
const flightsStore = useFlightsStore();
const logsStore = useLogsStore();
const uiStore = useUiStore();

const mapInstance = ref<LeafletMap | null>(null);
const reporting = ref(false);
const manualLocationSelecting = ref(false);
const { schedule } = useDebouncedTask(400);

const selectedLoggedFlight = computed(() => logsStore.byId(uiStore.selectedLogId));
const detailLoggedFlight = computed(() => logsStore.byId(uiStore.detailLogId));
const activeTrajectory = computed(() => {
  if (uiStore.mode === "live") return flightsStore.liveTrajectory;
  return selectedLoggedFlight.value?.trajectory ?? [];
});
const manualLocationActive = computed(() => uiStore.manualLocationOpen && uiStore.view === "map" && manualLocationSelecting.value);
const currentViewportCenter = computed(() => mapStore.viewportCenter ?? mapStore.center);
const liveTimeShiftDisabled = computed(() => !flightsStore.liveCapabilities.supports_history);
const liveTimeShiftHelperText = computed(() => {
  if (flightsStore.isLoadingCapabilities) {
    return "Checking time-shift availability...";
  }
  if (!flightsStore.liveCapabilities.supports_history) {
    return "Time shift unavailable for the current live provider.";
  }
  return `Showing flights from ${uiStore.liveTimeShiftMinutes === 0 ? "now" : `${uiStore.liveTimeShiftMinutes} min ago`}.`;
});
const locationSettingsDisplayLocation = computed(() => {
  if (uiStore.locationMode === "auto") {
    return mapStore.userLocation ?? mapStore.center;
  }
  if (manualLocationSelecting.value) {
    return currentViewportCenter.value;
  }
  return mapStore.userLocation ?? currentViewportCenter.value ?? mapStore.center;
});

function syncWindowActivity(): void {
  flightsStore.setWindowActive(document.visibilityState === "visible" && document.hasFocus());
}

async function refreshCurrentMode(reason: "poll" | "viewport" | "manual" = "manual"): Promise<void> {
  if (uiStore.mode === "live") {
    await flightsStore.refresh(reason);
  } else {
    await logsStore.refresh();
  }
}

function scheduleRefresh(reason: "poll" | "viewport" | "manual" = "manual"): void {
  schedule(() => {
    void refreshCurrentMode(reason);
  });
}

function scheduleViewportRefresh(): void {
  schedule(() => {
    if (uiStore.mode === "live") {
      void flightsStore.refresh("viewport");
      return;
    }
    void logsStore.refresh();
  });
}

function openLocationSettings(): void {
  if (!mapStore.center) {
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });
  }
  uiStore.view = "map";
  uiStore.manualLocationOpen = true;
  manualLocationSelecting.value = uiStore.locationMode === "manual";
}

function closeLocationSettings(): void {
  uiStore.manualLocationOpen = false;
  manualLocationSelecting.value = false;
}

function recenterMapOnLocation(location: { lat: number; lon: number }): void {
  if (!mapInstance.value) {
    return;
  }
  mapInstance.value.flyTo([location.lat, location.lon], Math.max(mapInstance.value.getZoom(), 12));
}

async function setLocationMode(mode: "auto" | "manual"): Promise<void> {
  uiStore.locationMode = mode;
  if (mode === "manual") {
    uiStore.view = "map";
    manualLocationSelecting.value = true;
    return;
  }

  manualLocationSelecting.value = false;

  try {
    const location = await mapStore.requestUserLocation();
    recenterMapOnLocation(location);
    scheduleRefresh("manual");
  } catch (error) {
    uiStore.locationMode = "manual";
    manualLocationSelecting.value = true;
    uiStore.showToast(error instanceof Error ? error.message : "Unable to access your location");
  }
}

async function handleReportSubmit(payload: { note: string; files: File[] }): Promise<void> {
  if (!uiStore.reportFlight) {
    return;
  }
  reporting.value = true;
  try {
    const currentUser = identityStore.ensureIdentity();
    const currentLocation = mapStore.userLocation ?? mapStore.center;
    const flightTime = uiStore.reportFlight.last_contact
      ? new Date(uiStore.reportFlight.last_contact * 1000).toISOString()
      : new Date(Date.now() - uiStore.liveTimeShiftMinutes * 60_000).toISOString();
    await createFlightLog(
      {
        icao24: uiStore.reportFlight.icao24,
        flight_time: flightTime,
        callsign: uiStore.reportFlight.callsign,
        aircraft_latitude: uiStore.reportFlight.latitude,
        aircraft_longitude: uiStore.reportFlight.longitude,
        altitude: uiStore.reportFlight.altitude,
        velocity: uiStore.reportFlight.velocity,
        heading: uiStore.reportFlight.heading,
        vertical_rate: uiStore.reportFlight.vertical_rate,
        owner_uuid: currentUser,
        logger_latitude: currentLocation?.lat ?? null,
        logger_longitude: currentLocation?.lon ?? null,
        note: payload.note,
      },
      payload.files,
    );
    uiStore.reportFlight = null;
    uiStore.showToast("Flight logged successfully.");
    await logsStore.refresh();
  } catch (error) {
    uiStore.showToast(error instanceof Error ? error.message : "Unable to submit report");
  } finally {
    reporting.value = false;
  }
}

function handleLocationSettingsSubmit(payload: { lat: number; lon: number }): void {
  if (uiStore.locationMode === "auto") {
    closeLocationSettings();
    return;
  }
  if (!Number.isFinite(payload.lat) || !Number.isFinite(payload.lon)) {
    uiStore.showToast("Please provide a valid latitude and longitude.");
    return;
  }
  mapStore.setUserLocation({ lat: payload.lat, lon: payload.lon });
  uiStore.locationMode = "manual";
  closeLocationSettings();
  scheduleRefresh("manual");
}

function handleMapReady(map: LeafletMap): void {
  mapInstance.value = map;
}

function handleSelectFlight(icao24: string): void {
  uiStore.selectedFlightIcao24 = icao24;
}

function handleHighlightLog(flightId: number): void {
  uiStore.selectedLogId = flightId;
}

function handleSelectLog(flightId: number): void {
  uiStore.detailLogId = flightId;
}

function handleLiveTimeShiftUpdate(value: number): void {
  uiStore.liveTimeShiftMinutes = value;
  scheduleRefresh("manual");
}

function handleLoggedTimeWindowUpdate(value: number): void {
  uiStore.loggedTimeWindowDays = value;
  scheduleRefresh("manual");
}

onMounted(async () => {
  identityStore.ensureIdentity();
  syncWindowActivity();
  window.addEventListener("focus", syncWindowActivity);
  window.addEventListener("blur", syncWindowActivity);
  document.addEventListener("visibilitychange", syncWindowActivity);
  await flightsStore.loadCapabilities();
  try {
    await mapStore.requestUserLocation();
    uiStore.locationMode = "auto";
  } catch (error) {
    uiStore.locationMode = "manual";
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });
    uiStore.showToast(error instanceof Error ? error.message : "Unable to access your location");
    openLocationSettings();
  }
  if (uiStore.mode === "logged") {
    scheduleRefresh("manual");
  }
});

watch(
  () => uiStore.mode,
  (mode) => {
    uiStore.selectedFlightIcao24 = null;
    if (mode === "live") {
      flightsStore.startPolling();
    } else {
      flightsStore.stopPolling();
      scheduleRefresh("manual");
    }
  },
  { immediate: true },
);

watch(
  () => mapStore.liveQuery,
  () => {
    if (uiStore.mode === "live") {
      scheduleViewportRefresh();
    }
  },
  { deep: true },
);

watch(
  () => mapStore.query,
  () => {
    if (uiStore.mode === "logged") {
      scheduleViewportRefresh();
    }
  },
  { deep: true },
);

watch(
  () => uiStore.loggedTimeWindowDays,
  () => {
    if (uiStore.mode === "logged") {
      scheduleRefresh();
    }
  },
);

onBeforeUnmount(() => {
  window.removeEventListener("focus", syncWindowActivity);
  window.removeEventListener("blur", syncWindowActivity);
  document.removeEventListener("visibilitychange", syncWindowActivity);
  flightsStore.stopPolling();
});
</script>

<template>
  <main class="relative h-screen overflow-hidden text-[var(--ink)]">
    <MapShell
      v-if="uiStore.view === 'map'"
      :center="mapStore.center"
      :zoom="mapStore.zoom"
      :mode="uiStore.mode"
      :live-flights="flightsStore.sortedFlights"
      :logged-flights="logsStore.sortedFlights"
      :selected-log-id="uiStore.selectedLogId"
      :user-location="mapStore.userLocation"
      :manual-location-selecting="manualLocationActive"
      :live-coverage-bounds="mapStore.liveQuery?.queryBounds ?? null"
      :live-coverage-clamped="uiStore.mode === 'live' && Boolean(mapStore.liveQuery?.isClamped)"
      :trajectory="activeTrajectory"
      @update-bounds="mapStore.setBounds"
      @report="uiStore.reportFlight = $event"
      @select-flight="handleSelectFlight"
      @highlight-log="handleHighlightLog"
      @select-log="handleSelectLog"
      @ready="handleMapReady"
    />

    <section v-else class="absolute inset-0 overflow-hidden bg-slate-100/80">
      <div class="grid h-full md:grid-cols-[minmax(0,1fr)_24rem]">
        <FlightListPanel
          :mode="uiStore.mode"
          :live-flights="flightsStore.sortedFlights"
          :logged-flights="logsStore.sortedFlights"
          :selected-log-id="uiStore.detailLogId"
          @report="uiStore.reportFlight = $event"
          @select-log="handleSelectLog"
        />
        <div class="hidden md:block">
          <LoggedFlightDetailDrawer :flight="detailLoggedFlight" inline @close="uiStore.detailLogId = null" />
        </div>
      </div>
    </section>

    <ViewToggle :view="uiStore.view" @update:view="uiStore.view = $event" />
    <FloatingControls
      :show-filters-button="uiStore.mode === 'live'"
      button-label="Filters"
      @location="openLocationSettings"
      @refresh="refreshCurrentMode('manual')"
    />
    <div
      v-if="uiStore.mode === 'live' && uiStore.view === 'map' && flightsStore.coverageMessage"
      class="glass-panel absolute left-1/2 top-4 z-[900] max-w-sm -translate-x-1/2 rounded-2xl px-4 py-3 text-center text-sm font-medium text-[var(--muted)]"
    >
      {{ flightsStore.coverageMessage }}
    </div>
    <ToastStack :message="uiStore.toast" />

    <LoggedFlightDetailDrawer
      v-if="uiStore.view === 'map'"
      :flight="detailLoggedFlight"
      @close="uiStore.detailLogId = null"
    />

    <LiveTimeShiftBar
      v-if="uiStore.mode === 'live'"
      :value="uiStore.liveTimeShiftMinutes"
      :disabled="liveTimeShiftDisabled"
      :helper-text="liveTimeShiftHelperText"
      @update:value="handleLiveTimeShiftUpdate"
    />

    <LoggedTimeWindowBar
      v-if="uiStore.mode === 'logged'"
      :value="uiStore.loggedTimeWindowDays"
      @update:value="handleLoggedTimeWindowUpdate"
    />

    <BottomModeNav :mode="uiStore.mode" @update:mode="uiStore.mode = $event" />

    <ReportFlightModal
      :open="Boolean(uiStore.reportFlight)"
      :flight="uiStore.reportFlight"
      :submitting="reporting"
      @close="uiStore.reportFlight = null"
      @submit="handleReportSubmit"
      @invalid="uiStore.showToast($event)"
    />

    <ManualLocationSheet
      :open="uiStore.manualLocationOpen"
      :display-location="locationSettingsDisplayLocation"
      :selecting-on-map="manualLocationSelecting"
      :location-mode="uiStore.locationMode"
      @close="closeLocationSettings"
      @submit="handleLocationSettingsSubmit"
      @update-location-mode="setLocationMode"
    />
  </main>
</template>
