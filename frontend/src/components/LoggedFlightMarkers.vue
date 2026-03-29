<script setup lang="ts">
import { LCircleMarker, LPopup } from "@vue-leaflet/vue-leaflet";

import LoggedFlightPopup from "@/components/LoggedFlightPopup.vue";
import { resolveLoggedFlightPoint } from "@/lib/geo";
import type { ApiLoggedFlight } from "@/types/api";

defineProps<{
  flights: ApiLoggedFlight[];
  selectedId: number | null;
}>();

defineEmits<{
  open: [flightId: number];
}>();
</script>

<template>
  <template v-for="flight in flights" :key="flight.id">
    <LCircleMarker
      v-if="resolveLoggedFlightPoint(flight)"
      :lat-lng="[resolveLoggedFlightPoint(flight)!.lat, resolveLoggedFlightPoint(flight)!.lon]"
      :radius="selectedId === flight.id ? 10 : 8"
      color="#d9730d"
      fill-color="#f59e0b"
      :fill-opacity="0.82"
      :weight="selectedId === flight.id ? 3 : 2"
    >
      <LPopup>
        <LoggedFlightPopup :flight="flight" @open="$emit('open', $event)" />
      </LPopup>
    </LCircleMarker>
  </template>
</template>
