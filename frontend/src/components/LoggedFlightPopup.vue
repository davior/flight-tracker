<script setup lang="ts">
import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";
import { formatTimestamp } from "@/lib/format";
import { formatDistance } from "@/lib/geo";
import type { ApiLoggedFlight } from "@/types/api";

defineProps<{
  flight: ApiLoggedFlight;
}>();

defineEmits<{
  open: [flightId: number];
}>();
</script>

<template>
  <div class="space-y-3 text-sm">
    <div class="flex items-start gap-3">
      <img
        v-if="flight.photos[0]"
        :src="flight.photos[0].url"
        alt=""
        class="h-16 w-16 rounded-2xl object-cover"
      />
      <div class="min-w-0">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Logged Flight</p>
        <h3 class="truncate text-base font-bold">{{ flight.callsign || flight.icao24.toUpperCase() }}</h3>
        <p class="text-[var(--muted)]">{{ getAircraftDisplayLabel(flight) || "Aircraft type unavailable" }}</p>
        <p v-if="flight.operator" class="mt-1 text-xs text-[var(--muted)]">
          {{ flight.operator }}<span v-if="flight.operator_icao"> ({{ flight.operator_icao }})</span>
        </p>
        <p v-if="flight.owner && flight.owner !== flight.operator" class="mt-0.5 text-xs text-[var(--muted)]">
          Owner: {{ flight.owner }}
        </p>
        <p v-if="formatAircraftCategory(flight)" class="mt-1 text-xs text-[var(--muted)]">
          Category: {{ formatAircraftCategory(flight) }}
        </p>
      </div>
    </div>
    <p class="line-clamp-3 text-sm text-[var(--muted)]">{{ flight.note || "No note added." }}</p>
    <div class="flex items-center justify-between text-xs text-[var(--muted)]">
      <span>{{ formatDistance(flight.distance_km) }}</span>
      <span>{{ formatTimestamp(flight.flight_time) }}</span>
    </div>
    <button
      class="w-full rounded-2xl bg-[var(--logged)] px-4 py-3 font-semibold text-white"
      @click="$emit('open', flight.id)"
    >
      View details
    </button>
  </div>
</template>
