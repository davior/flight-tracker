<script setup lang="ts">
import { LIcon, LMarker, LPopup } from "@vue-leaflet/vue-leaflet";

import LoggedFlightPopup from "@/components/LoggedFlightPopup.vue";
import { resolveLoggedFlightPoint } from "@/lib/geo";
import type { ApiLoggedFlight } from "@/types/api";

defineProps<{
  flights: ApiLoggedFlight[];
  selectedId: number | null;
}>();

const emit = defineEmits<{
  open: [flightId: number];
  select: [flightId: number];
}>();
</script>

<template>
  <template v-for="flight in flights" :key="flight.id">
    <LMarker
      v-if="resolveLoggedFlightPoint(flight)"
      :lat-lng="[resolveLoggedFlightPoint(flight)!.lat, resolveLoggedFlightPoint(flight)!.lon]"
      @click="emit('select', flight.id)"
    >
      <LIcon :icon-size="[34, 34]" :icon-anchor="[17, 17]" class-name="logged-flight-marker-icon">
        <div class="logged-flight-marker">
          <svg
            class="logged-flight-marker__aircraft"
            :style="{ '--flight-heading': `${flight.heading ?? 0}deg` }"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path d="M12 1L14.6 8.4L20 10.2V12.2L14.25 11.85L13.4 23H10.6L9.75 11.85L4 12.2V10.2L9.4 8.4L12 1Z" />
          </svg>
        </div>
      </LIcon>
      <LPopup>
        <LoggedFlightPopup :flight="flight" @open="emit('open', $event)" />
      </LPopup>
    </LMarker>
  </template>
</template>
