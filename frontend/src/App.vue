<script setup lang="ts">
import type { Map as LeafletMap } from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import BottomModeNav from "@/components/BottomModeNav.vue";
import FiltersSheet from "@/components/FiltersSheet.vue";
import FlightListPanel from "@/components/FlightListPanel.vue";
import FloatingControls from "@/components/FloatingControls.vue";
import LoggedFlightDetailDrawer from "@/components/LoggedFlightDetailDrawer.vue";
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
const { schedule } = useDebouncedTask(400);

const selectedLoggedFlight = computed(() => logsStore.byId(uiStore.selectedLogId));
const modeLabel = computed(() => (uiStore.mode === "live" ? "Filters" : "Time window"));
const manualLocationActive = computed(() => uiStore.manualLocationOpen && uiStore.view === "map");
const currentViewportCenter = computed(() => mapStore.viewportCenter ?? mapStore.center);

function syncWindowActivity(): void {
  flightsStore.setWindowActive(document.visibilityState === "visible" && document.hasFocus());
}

async function refreshCurrentMode(): Promise<void> {
  if (uiStore.mode === "live") {
    await flightsStore.refresh();
  } else {
    await logsStore.refresh();
  }
}

function scheduleRefresh(): void {
  schedule(() => {
    void refreshCurrentMode();
  });
}

function openManualLocation(): void {
  if (!mapStore.center) {
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });
  }
  uiStore.view = "map";
  uiStore.manualLocationOpen = true;
}

async function handleRecenter(): Promise<void> {
  try {
    await mapStore.requestUserLocation();
    scheduleRefresh();
  } catch (error) {
    uiStore.showToast(error instanceof Error ? error.message : "Unable to access your location");
    openManualLocation();
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
    await createFlightLog(
      {
        icao24: uiStore.reportFlight.icao24,
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

function handleManualLocation(payload: { lat: number; lon: number }): void {
  if (!Number.isFinite(payload.lat) || !Number.isFinite(payload.lon)) {
    uiStore.showToast("Please provide a valid latitude and longitude.");
    return;
  }
  mapStore.setUserLocation({ lat: payload.lat, lon: payload.lon });
  uiStore.manualLocationOpen = false;
  scheduleRefresh();
}

function handleManualLocationUseCenter(): void {
  if (!currentViewportCenter.value) {
    uiStore.showToast("Move the map until the red target is over your location.");
    return;
  }
  mapStore.setUserLocation(currentViewportCenter.value);
  uiStore.manualLocationOpen = false;
  scheduleRefresh();
}

function handleMapReady(map: LeafletMap): void {
  mapInstance.value = map;
}

function handleSelectLog(flightId: number): void {
  uiStore.selectedLogId = flightId;
  if (uiStore.view === "map") {
    const flight = logsStore.byId(flightId);
    if (flight?.aircraft_latitude !== null && flight?.aircraft_longitude !== null && mapInstance.value) {
      mapInstance.value.flyTo([flight.aircraft_latitude, flight.aircraft_longitude], Math.max(mapInstance.value.getZoom(), 12));
    }
  }
}

onMounted(async () => {
  identityStore.ensureIdentity();
  syncWindowActivity();
  window.addEventListener("focus", syncWindowActivity);
  window.addEventListener("blur", syncWindowActivity);
  document.addEventListener("visibilitychange", syncWindowActivity);
  try {
    await mapStore.requestUserLocation();
  } catch (error) {
    mapStore.setCenter({ lat: -37.8136, lon: 144.9631 });
    uiStore.showToast(error instanceof Error ? error.message : "Unable to access your location");
  }
  scheduleRefresh();
});

watch(
  () => uiStore.mode,
  (mode) => {
    if (mode === "live") {
      flightsStore.startPolling();
    } else {
      flightsStore.stopPolling();
    }
    scheduleRefresh();
  },
  { immediate: true },
);

watch(
  () => mapStore.query,
  () => {
    scheduleRefresh();
  },
  { deep: true },
);

watch(
  () => uiStore.timeWindow,
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
      :manual-location-active="manualLocationActive"
      @update-bounds="mapStore.setBounds"
      @report="uiStore.reportFlight = $event"
      @select-log="handleSelectLog"
      @ready="handleMapReady"
    />

    <section v-else class="absolute inset-0 overflow-hidden bg-slate-100/80">
      <div class="grid h-full md:grid-cols-[minmax(0,1fr)_24rem]">
        <FlightListPanel
          :mode="uiStore.mode"
          :live-flights="flightsStore.sortedFlights"
          :logged-flights="logsStore.sortedFlights"
          :selected-log-id="uiStore.selectedLogId"
          @report="uiStore.reportFlight = $event"
          @select-log="handleSelectLog"
        />
        <div class="hidden md:block">
          <LoggedFlightDetailDrawer :flight="selectedLoggedFlight" inline @close="uiStore.selectedLogId = null" />
        </div>
      </div>
    </section>

    <ViewToggle :view="uiStore.view" @update:view="uiStore.view = $event" />
    <FloatingControls
      :mode-label="modeLabel"
      @center="handleRecenter"
      @manual="openManualLocation"
      @refresh="refreshCurrentMode"
      @filters="uiStore.filtersOpen = true"
    />
    <ToastStack :message="uiStore.toast" />

    <LoggedFlightDetailDrawer
      v-if="uiStore.view === 'map'"
      :flight="selectedLoggedFlight"
      @close="uiStore.selectedLogId = null"
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
      :current-center="currentViewportCenter"
      @close="uiStore.manualLocationOpen = false"
      @submit="handleManualLocation"
      @use-center="handleManualLocationUseCenter"
    />

    <FiltersSheet
      :open="uiStore.filtersOpen"
      :value="uiStore.timeWindow"
      @close="uiStore.filtersOpen = false"
      @select="uiStore.timeWindow = $event; uiStore.filtersOpen = false"
    />
  </main>
</template>
