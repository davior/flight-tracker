<script setup lang="ts">
import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";
import { formatTimestamp } from "@/lib/format";
import { formatDistance } from "@/lib/geo";
import type { ApiLoggedFlight } from "@/types/api";

defineProps<{
  flight: ApiLoggedFlight | null;
  inline?: boolean;
}>();

defineEmits<{
  close: [];
}>();
</script>

<template>
  <aside
    class="glass-panel rounded-[2rem] p-5"
    :class="
      inline
        ? 'm-6 h-[calc(100%-3rem)] overflow-y-auto'
        : 'absolute inset-x-0 bottom-24 z-[850] mx-3 md:bottom-6 md:left-auto md:right-6 md:top-24 md:w-[24rem] md:overflow-y-auto'
    "
    v-if="flight"
  >
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Flight detail</p>
        <h2 class="text-xl font-bold">{{ flight.callsign || flight.icao24.toUpperCase() }}</h2>
        <p class="text-sm text-[var(--muted)]">{{ getAircraftDisplayLabel(flight) || "Aircraft type unavailable" }}</p>
        <p v-if="formatAircraftCategory(flight)" class="mt-1 text-xs text-[var(--muted)]">
          Category: {{ formatAircraftCategory(flight) }}
        </p>
        <p v-if="getAircraftCategoryDescription(flight)" class="mt-1 text-xs text-[var(--muted)]">
          {{ getAircraftCategoryDescription(flight) }}
        </p>
      </div>
      <button class="rounded-full bg-white/70 px-3 py-1 text-sm font-semibold" @click="$emit('close')">Close</button>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
      <div class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Distance</p>
        <p class="mt-1 font-semibold">{{ formatDistance(flight.distance_km) }}</p>
      </div>
      <div class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Logged</p>
        <p class="mt-1 font-semibold">{{ formatTimestamp(flight.created_at) }}</p>
      </div>
      <div class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Category</p>
        <p class="mt-1 font-semibold">{{ formatAircraftCategory(flight) || "n/a" }}</p>
      </div>
    </div>

    <p class="mt-4 rounded-3xl bg-white/70 p-4 text-sm text-[var(--muted)]">{{ flight.note || "No note added." }}</p>

    <div v-if="flight.photos.length" class="mt-4 grid grid-cols-3 gap-3">
      <img
        v-for="photo in flight.photos"
        :key="photo.id"
        :src="photo.url"
        alt=""
        class="h-24 w-full rounded-2xl object-cover"
      />
    </div>
  </aside>
</template>
