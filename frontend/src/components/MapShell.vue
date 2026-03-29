<script setup lang="ts">
import { LMap, LTileLayer } from "@vue-leaflet/vue-leaflet";
import type { Map as LeafletMap } from "leaflet";
import { computed, nextTick, ref, watch } from "vue";

import LoggedFlightMarkers from "@/components/LoggedFlightMarkers.vue";
import LiveFlightMarkers from "@/components/LiveFlightMarkers.vue";
import type { ApiLiveFlight, ApiLoggedFlight, AppMode, LatLng, MapBounds } from "@/types/api";

const props = defineProps<{
  center: LatLng | null;
  zoom: number;
  mode: AppMode;
  liveFlights: ApiLiveFlight[];
  loggedFlights: ApiLoggedFlight[];
  selectedLogId: number | null;
  manualLocationActive: boolean;
}>();

const emit = defineEmits<{
  report: [flight: ApiLiveFlight];
  selectLog: [flightId: number];
  updateBounds: [bounds: MapBounds];
  ready: [map: LeafletMap];
}>();

const mapInstance = ref<LeafletMap | null>(null);
const mapCenter = computed<[number, number]>(() => [
  props.center?.lat ?? -37.8136,
  props.center?.lon ?? 144.9631,
]);
const CENTER_EPSILON = 0.00001;

function emitBounds(map?: LeafletMap): void {
  const leafletMap = map ?? mapInstance.value;
  if (!leafletMap) {
    return;
  }
  const bounds = leafletMap.getBounds();
  emit("updateBounds", {
    north: bounds.getNorth(),
    south: bounds.getSouth(),
    east: bounds.getEast(),
    west: bounds.getWest(),
  });
}

function handleViewportChanged(): void {
  emitBounds();
}

function syncMapLayout(map: LeafletMap): void {
  window.requestAnimationFrame(() => {
    map.invalidateSize(false);
    emitBounds(map);
  });
}

function handleReady(map: LeafletMap): void {
  mapInstance.value = map;
  emit("ready", map);
  map.whenReady(() => {
    void nextTick(() => {
      syncMapLayout(map);
    });
  });
}

function hasMeaningfulCenterChange(map: LeafletMap, nextCenter: LatLng): boolean {
  const currentCenter = map.getCenter();
  return (
    Math.abs(currentCenter.lat - nextCenter.lat) > CENTER_EPSILON ||
    Math.abs(currentCenter.lng - nextCenter.lon) > CENTER_EPSILON
  );
}

watch(
  () => props.center,
  (nextCenter) => {
    const leafletMap = mapInstance.value;
    if (!leafletMap || !nextCenter) {
      return;
    }
    if (!hasMeaningfulCenterChange(leafletMap, nextCenter)) {
      return;
    }
    leafletMap.setView([nextCenter.lat, nextCenter.lon], leafletMap.getZoom(), { animate: true });
  },
  { deep: true },
);
</script>

<template>
  <div class="absolute inset-0">
    <LMap
      class="h-full w-full"
      :use-global-leaflet="false"
      :zoom="zoom"
      :center="mapCenter"
      :zoom-control="false"
      @ready="handleReady"
      @moveend="handleViewportChanged"
      @zoomend="handleViewportChanged"
    >
      <LTileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        layer-type="base"
        name="OpenStreetMap"
        attribution="&copy; OpenStreetMap contributors"
      />
      <LiveFlightMarkers
        v-if="mode === 'live'"
        :flights="liveFlights"
        @report="$emit('report', $event)"
      />
      <LoggedFlightMarkers
        v-else
        :flights="loggedFlights"
        :selected-id="selectedLogId"
        @open="$emit('selectLog', $event)"
      />
    </LMap>
    <div v-if="manualLocationActive" class="pointer-events-none absolute inset-0 z-[850]">
      <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <div class="manual-location-target">
          <div class="manual-location-target__ring"></div>
          <div class="manual-location-target__dot"></div>
        </div>
      </div>
    </div>
  </div>
</template>
