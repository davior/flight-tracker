<script setup lang="ts">
import { LCircleMarker, LPopup } from "@vue-leaflet/vue-leaflet";

import LiveFlightPopup from "@/components/LiveFlightPopup.vue";
import type { ApiLiveFlight } from "@/types/api";

defineProps<{
  flights: ApiLiveFlight[];
}>();

defineEmits<{
  report: [flight: ApiLiveFlight];
}>();
</script>

<template>
  <template v-for="flight in flights" :key="flight.icao24">
    <LCircleMarker
      :lat-lng="[flight.latitude, flight.longitude]"
      :radius="9"
      color="#1d7a5f"
      fill-color="#2ecc71"
      :fill-opacity="0.75"
      :weight="2"
    >
      <LPopup>
        <LiveFlightPopup :flight="flight" @report="$emit('report', $event)" />
      </LPopup>
    </LCircleMarker>
  </template>
</template>
