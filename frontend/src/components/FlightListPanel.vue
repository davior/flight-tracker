<script setup lang="ts">
import { formatAircraftCategory, getAircraftDisplayLabel } from "@/lib/aircraft";
import { formatTimestamp } from "@/lib/format";
import { formatDistance } from "@/lib/geo";
import type { ApiLiveFlight, ApiLoggedFlight, AppMode } from "@/types/api";

const props = defineProps<{
  mode: AppMode;
  liveFlights: ApiLiveFlight[];
  loggedFlights: ApiLoggedFlight[];
  selectedLogId: number | null;
}>();

defineEmits<{
  report: [flight: ApiLiveFlight];
  selectLog: [flightId: number];
}>();

</script>

<template>
  <section class="relative h-full overflow-y-auto px-4 pb-28 pt-20 md:px-6">
    <div class="mx-auto flex max-w-4xl flex-col gap-3">
      <template v-if="mode === 'live'">
        <article
          v-for="item in liveFlights"
          :key="item.icao24"
          class="glass-panel rounded-[1.75rem] p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Live Flight</p>
              <h3 class="text-lg font-bold">{{ item.callsign || item.icao24.toUpperCase() }}</h3>
              <p class="text-sm text-[var(--muted)]">{{ getAircraftDisplayLabel(item) || "Aircraft type unavailable" }}</p>
              <p v-if="formatAircraftCategory(item)" class="mt-1 text-xs text-[var(--muted)]">
                Category: {{ formatAircraftCategory(item) }}
              </p>
            </div>
            <span class="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
              {{ formatDistance(item.distance_km) }}
            </span>
          </div>
          <button
            class="mt-4 w-full rounded-2xl bg-[var(--live)] px-4 py-3 font-semibold text-white"
            @click="$emit('report', item)"
          >
            Report this flight
          </button>
        </article>
      </template>

      <template v-else>
        <article
          v-for="item in loggedFlights"
          :key="item.id"
          class="glass-panel rounded-[1.75rem] p-4"
          :class="item.id === selectedLogId ? 'ring-2 ring-[var(--logged)]' : ''"
        >
          <div class="flex gap-4">
            <img
              v-if="item.photos[0]"
              :src="item.photos[0].url"
              alt=""
              class="h-20 w-20 rounded-2xl object-cover"
            />
            <div class="min-w-0 flex-1">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Logged Flight</p>
                  <h3 class="truncate text-lg font-bold">{{ item.callsign || item.icao24.toUpperCase() }}</h3>
                  <p class="text-sm text-[var(--muted)]">{{ getAircraftDisplayLabel(item) || "Aircraft type unavailable" }}</p>
                  <p v-if="formatAircraftCategory(item)" class="mt-1 text-xs text-[var(--muted)]">
                    Category: {{ formatAircraftCategory(item) }}
                  </p>
                </div>
                <span class="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-[var(--logged)]">
                  {{ formatDistance(item.distance_km) }}
                </span>
              </div>
              <p class="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{{ item.note || "No note added." }}</p>
              <div class="mt-3 flex items-center justify-between text-xs text-[var(--muted)]">
                <span>{{ formatTimestamp(item.created_at) }}</span>
                <span>{{ item.is_owner ? "Your log" : "Community log" }}</span>
              </div>
            </div>
          </div>
          <button
            class="mt-4 w-full rounded-2xl bg-[var(--logged)] px-4 py-3 font-semibold text-white"
            @click="$emit('selectLog', item.id)"
          >
            View details
          </button>
        </article>
      </template>
    </div>
  </section>
</template>
