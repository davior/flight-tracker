<script setup lang="ts">
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
        <p class="text-[var(--muted)]">{{ flight.display_type || "Aircraft type unavailable" }}</p>
      </div>
    </div>
    <p class="line-clamp-3 text-sm text-[var(--muted)]">{{ flight.note || "No note added." }}</p>
    <div class="flex items-center justify-between text-xs text-[var(--muted)]">
      <span>{{ formatDistance(flight.distance_km) }}</span>
      <span>{{ formatTimestamp(flight.created_at) }}</span>
    </div>
    <button
      class="w-full rounded-2xl bg-[var(--logged)] px-4 py-3 font-semibold text-white"
      @click="$emit('open', flight.id)"
    >
      View details
    </button>
  </div>
</template>
