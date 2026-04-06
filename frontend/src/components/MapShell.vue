<script setup lang="ts">
import { LIcon, LMap, LMarker, LRectangle, LTileLayer } from "@vue-leaflet/vue-leaflet";
import type { Map as LeafletMap } from "leaflet";
import { computed, nextTick, ref, watch } from "vue";

import FlightTrajectory from "@/components/FlightTrajectory.vue";
import LoggedFlightMarkers from "@/components/LoggedFlightMarkers.vue";
import LiveFlightMarkers from "@/components/LiveFlightMarkers.vue";
import type { ApiLiveFlight, ApiLoggedFlight, ApiTrajectoryPoint, AppMode, LatLng, MapBounds } from "@/types/api";

const props = defineProps<{
  center: LatLng | null;
  zoom: number;
  mode: AppMode;
  liveFlights: ApiLiveFlight[];
  loggedFlights: ApiLoggedFlight[];
  selectedLogId: number | null;
  userLocation: LatLng | null;
  manualLocationSelecting: boolean;
  liveCoverageBounds: MapBounds | null;
  liveCoverageClamped: boolean;
  trajectory: ApiTrajectoryPoint[];
}>();

const emit = defineEmits<{
  report: [flight: ApiLiveFlight];
  selectFlight: [icao24: string];
  selectLog: [flightId: number];
  highlightLog: [flightId: number];
  updateBounds: [bounds: MapBounds];
  ready: [map: LeafletMap];
}>();

const mapInstance = ref<LeafletMap | null>(null);
const mapCenter = computed<[number, number]>(() => [
  props.center?.lat ?? -37.8136,
  props.center?.lon ?? 144.9631,
]);
const coverageBounds = computed<[[number, number], [number, number]] | null>(() => {
  if (!props.liveCoverageBounds) {
    return null;
  }

  return [
    [props.liveCoverageBounds.south, props.liveCoverageBounds.west],
    [props.liveCoverageBounds.north, props.liveCoverageBounds.east],
  ];
});
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
      <LRectangle
        v-if="mode === 'live' && liveCoverageClamped && coverageBounds"
        :bounds="coverageBounds"
        :color="'#1d7a5f'"
        :weight="2"
        :dash-array="'6 4'"
        :fill="true"
        :fill-opacity="0.08"
      />
      <LMarker
        v-if="userLocation"
        :lat-lng="[userLocation.lat, userLocation.lon]"
        :interactive="false"
      >
        <LIcon :icon-size="[42, 42]" :icon-anchor="[21, 21]" class-name="user-location-marker">
          <div class="location-target location-target--marker">
            <div class="location-target__ring"></div>
            <div class="location-target__dot"></div>
          </div>
        </LIcon>
      </LMarker>
      <template v-if="mode === 'live'">
        <FlightTrajectory v-if="trajectory.length > 0" :points="trajectory" />
        <LiveFlightMarkers
          :flights="liveFlights"
          @report="$emit('report', $event)"
          @select="$emit('selectFlight', $event)"
        />
      </template>
      <template v-else>
        <template v-for="flight in loggedFlights" :key="`trajectory-${flight.id}`">
          <FlightTrajectory
            v-if="flight.trajectory && flight.trajectory.length > 0"
            :points="flight.trajectory"
            :highlighted="flight.id === selectedLogId"
          />
        </template>
        <LoggedFlightMarkers
          :flights="loggedFlights"
          :selected-id="selectedLogId"
          @select="$emit('highlightLog', $event)"
          @open="$emit('selectLog', $event)"
        />
      </template>
    </LMap>
    <div v-if="manualLocationSelecting" class="pointer-events-none absolute inset-0 z-[850]">
      <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <div class="location-target location-target--selection">
          <div class="location-target__ring"></div>
          <div class="location-target__dot"></div>
        </div>
      </div>
    </div>
  </div>
</template>
