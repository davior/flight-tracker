<script setup lang="ts">
import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";
import { formatDistance } from "@/lib/geo";
import type { ApiLiveFlight } from "@/types/api";

defineProps<{
  flight: ApiLiveFlight;
}>();

defineEmits<{
  report: [flight: ApiLiveFlight];
}>();
</script>

<template>
  <div class="space-y-3 text-sm">
    <div>
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Live Flight</p>
      <h3 class="text-base font-bold">{{ flight.callsign || flight.icao24.toUpperCase() }}</h3>
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
    <dl class="grid grid-cols-2 gap-2 text-xs text-[var(--muted)]">
      <div>
        <dt>Distance</dt>
        <dd class="font-semibold text-[var(--ink)]">{{ formatDistance(flight.distance_km) }}</dd>
      </div>
      <div>
        <dt>Heading</dt>
        <dd class="font-semibold text-[var(--ink)]">{{ flight.heading ? `${Math.round(flight.heading)}°` : "n/a" }}</dd>
      </div>
      <div>
        <dt>Altitude</dt>
        <dd class="font-semibold text-[var(--ink)]">{{ flight.altitude ? `${Math.round(flight.altitude)} m` : "n/a" }}</dd>
      </div>
      <div>
        <dt>Speed</dt>
        <dd class="font-semibold text-[var(--ink)]">{{ flight.velocity ? `${Math.round(flight.velocity)} m/s` : "n/a" }}</dd>
      </div>
    </dl>
    <button
      class="w-full rounded-2xl bg-[var(--live)] px-4 py-3 font-semibold text-white"
      @click="$emit('report', flight)"
    >
      Report this flight
    </button>
  </div>
</template>
