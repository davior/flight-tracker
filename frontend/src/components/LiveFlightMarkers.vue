<script setup lang="ts">
import { LIcon, LMarker, LPopup } from "@vue-leaflet/vue-leaflet";

import LiveFlightPopup from "@/components/LiveFlightPopup.vue";
import type { ApiLiveFlight } from "@/types/api";

defineProps<{
  flights: ApiLiveFlight[];
}>();

const emit = defineEmits<{
  report: [flight: ApiLiveFlight];
  select: [icao24: string];
}>();
</script>

<template>
  <template v-for="flight in flights" :key="flight.icao24">
    <LMarker
      :lat-lng="[flight.latitude, flight.longitude]"
      @click="emit('select', flight.icao24)"
    >
      <LIcon :icon-size="[34, 34]" :icon-anchor="[17, 17]" class-name="live-flight-marker-icon">
        <div class="live-flight-marker">
          <svg
            class="live-flight-marker__aircraft"
            :style="{ '--flight-heading': `${flight.heading ?? 0}deg` }"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path d="M12 1L14.6 8.4L20 10.2V12.2L14.25 11.85L13.4 23H10.6L9.75 11.85L4 12.2V10.2L9.4 8.4L12 1Z" />
          </svg>
        </div>
      </LIcon>
      <LPopup>
        <LiveFlightPopup :flight="flight" @report="emit('report', $event)" />
      </LPopup>
    </LMarker>
  </template>
</template>
