<script setup lang="ts">
import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";
import { formatTimestamp } from "@/lib/format";
import { formatDistance } from "@/lib/geo";
import type { ApiLoggedFlight } from "@/types/api";

function loggedByLine(flight: ApiLoggedFlight): string | null {
  if (!flight.owner_username) {
    return null;
  }
  return `Logged by ${flight.owner_username} at ${formatTimestamp(flight.created_at)}`;
}

defineProps<{
  flight: ApiLoggedFlight | null;
  inline?: boolean;
}>();

defineEmits<{
  close: [];
}>();
</script>

<template>
  <div
    v-if="flight && !inline"
    class="absolute inset-0 z-[1000] flex items-end bg-slate-950/40 p-3 md:items-center md:justify-center"
  >
    <div class="glass-panel w-full rounded-[2rem] p-5 md:max-w-xl">
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
          <p v-if="loggedByLine(flight)" class="mt-2 text-xs text-[var(--muted)]">
            {{ loggedByLine(flight) }}
          </p>
        </div>
        <button class="rounded-full bg-white/70 p-2 text-sm font-semibold hover:bg-white/90" @click="$emit('close')" aria-label="Close">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Distance</p>
          <p class="mt-1 font-semibold">{{ formatDistance(flight.distance_km) }}</p>
        </div>
        <div class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Flight Time</p>
          <p class="mt-1 font-semibold">{{ formatTimestamp(flight.flight_time) }}</p>
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
    </div>
  </div>
  <aside
    v-else-if="flight && inline"
    class="glass-panel rounded-[2rem] p-5 m-6 h-[calc(100%-9rem)] overflow-y-auto"
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
        <p v-if="loggedByLine(flight)" class="mt-2 text-xs text-[var(--muted)]">
          {{ loggedByLine(flight) }}
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
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Flight Time</p>
        <p class="mt-1 font-semibold">{{ formatTimestamp(flight.flight_time) }}</p>
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
