<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { LatLng } from "@/types/api";
import type { LocationMode } from "@/stores/ui";

const props = defineProps<{
  open: boolean;
  displayLocation: LatLng | null;
  selectingOnMap: boolean;
  locationMode: LocationMode;
}>();

const emit = defineEmits<{
  close: [];
  submit: [{ lat: number; lon: number }];
  updateLocationMode: [mode: LocationMode];
}>();

const lat = ref("");
const lon = ref("");
const helperText = computed(() => {
  if (props.locationMode === "auto") {
    return "Your current GPS location is shown below.";
  }
  return "Drag the map until the crosshairs are over your location, or type the coordinates directly.";
});

function syncFromDisplayLocation(): void {
  if (!props.displayLocation) {
    lat.value = "";
    lon.value = "";
    return;
  }
  lat.value = props.displayLocation.lat.toFixed(5);
  lon.value = props.displayLocation.lon.toFixed(5);
}

function submit(): void {
  emit("submit", {
    lat: Number(lat.value),
    lon: Number(lon.value),
  });
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      syncFromDisplayLocation();
      return;
    }
    lat.value = "";
    lon.value = "";
  },
  { immediate: true },
);

watch(
  () => props.locationMode,
  () => {
    if (props.open) {
      syncFromDisplayLocation();
    }
  },
);

watch(
  () => props.displayLocation,
  () => {
    if (!props.open) {
      return;
    }
    if (props.locationMode === "auto" || props.selectingOnMap) {
      syncFromDisplayLocation();
    }
  },
  { deep: true },
);
</script>

<template>
  <div
    v-if="open"
    class="pointer-events-none absolute inset-0 z-[980] flex items-end justify-center bg-slate-950/40 p-3"
  >
    <div class="glass-panel pointer-events-auto w-full rounded-[2rem] p-5 md:max-w-md">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Location</p>
          <h2 class="text-xl font-bold">Location Settings</h2>
        </div>
        <button class="rounded-full bg-white/70 px-3 py-1 text-sm font-semibold" @click="$emit('close')">Close</button>
      </div>
      <div class="mt-4 rounded-[1.5rem] border border-[var(--border)] bg-white/75 p-2">
        <div class="grid grid-cols-2 gap-2">
          <button
            class="rounded-[1.2rem] px-4 py-3 text-sm font-semibold transition"
            :class="
              locationMode === 'auto'
                ? 'bg-[var(--accent)] !text-white shadow-lg shadow-sky-200/50'
                : 'bg-white/70 text-[var(--muted)]'
            "
            @click="$emit('updateLocationMode', 'auto')"
          >
            Use Auto Location
          </button>
          <button
            class="rounded-[1.2rem] px-4 py-3 text-sm font-semibold transition"
            :class="
              locationMode === 'manual'
                ? 'bg-[var(--ink)] !text-white shadow-lg shadow-slate-300/50'
                : 'bg-white/70 text-[var(--muted)]'
            "
            @click="$emit('updateLocationMode', 'manual')"
          >
            Manually Select Location
          </button>
        </div>
      </div>
      <div
        class="mt-4 rounded-[1.5rem] border border-[var(--border)] bg-white/75 p-4 transition"
        :class="locationMode === 'auto' ? 'opacity-55 grayscale-[0.2]' : ''"
      >
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Map target</p>
        <p class="mt-2 text-sm text-[var(--muted)]">{{ helperText }}</p>
      </div>
      <div class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Coordinates</p>
      </div>
      <div class="mt-3 grid grid-cols-2 gap-3">
        <input
          v-model="lat"
          class="rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3 disabled:cursor-not-allowed disabled:bg-slate-100"
          placeholder="Latitude"
          :disabled="locationMode === 'auto'"
        />
        <input
          v-model="lon"
          class="rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3 disabled:cursor-not-allowed disabled:bg-slate-100"
          placeholder="Longitude"
          :disabled="locationMode === 'auto'"
        />
      </div>
      <div class="mt-4 grid grid-cols-2 gap-3">
        <button class="rounded-2xl bg-[var(--ink)] px-4 py-3 font-semibold !text-white" @click="submit">
          Ok
        </button>
        <button class="rounded-2xl bg-white/80 px-4 py-3 font-semibold text-[var(--ink)]" @click="$emit('close')">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>
