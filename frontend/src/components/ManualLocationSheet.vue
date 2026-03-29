<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { LatLng } from "@/types/api";

const props = defineProps<{
  open: boolean;
  currentCenter: LatLng | null;
}>();

const emit = defineEmits<{
  close: [];
  submit: [{ lat: number; lon: number }];
  useCenter: [];
}>();

const lat = ref("");
const lon = ref("");
const centerLabel = computed(() => {
  if (!props.currentCenter) {
    return "Move the map until the red target is over your location.";
  }
  return `${props.currentCenter.lat.toFixed(5)}, ${props.currentCenter.lon.toFixed(5)}`;
});

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      lat.value = "";
      lon.value = "";
    }
  },
);

function submit(): void {
  emit("submit", {
    lat: Number(lat.value),
    lon: Number(lon.value),
  });
}
</script>

<template>
  <div v-if="open" class="absolute inset-0 z-[980] flex items-end bg-slate-950/40 p-3 md:items-center md:justify-center">
    <div class="glass-panel w-full rounded-[2rem] p-5 md:max-w-md">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Manual location</p>
          <h2 class="text-xl font-bold">Set current location</h2>
        </div>
        <button class="rounded-full bg-white/70 px-3 py-1 text-sm font-semibold" @click="$emit('close')">Close</button>
      </div>
      <div class="mt-4 rounded-[1.5rem] border border-[var(--border)] bg-white/75 p-4">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Map target</p>
        <p class="mt-2 text-sm text-[var(--muted)]">Drag the map until the red target sits over your location.</p>
        <p class="mt-3 font-semibold text-[var(--ink)]">{{ centerLabel }}</p>
        <button
          class="mt-4 w-full rounded-2xl bg-[var(--accent)] px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          :disabled="!currentCenter"
          @click="$emit('useCenter')"
        >
          Set current location
        </button>
      </div>
      <div class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Or enter coordinates</p>
      </div>
      <div class="mt-3 grid grid-cols-2 gap-3">
        <input v-model="lat" class="rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3" placeholder="Latitude" />
        <input v-model="lon" class="rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3" placeholder="Longitude" />
      </div>
      <button class="mt-4 w-full rounded-2xl bg-[var(--ink)] px-4 py-3 font-semibold text-white" @click="submit">
        Use typed coordinates
      </button>
    </div>
  </div>
</template>
