<script setup lang="ts">
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
      <p class="text-[var(--muted)]">{{ flight.display_type || "Aircraft type unavailable" }}</p>
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
