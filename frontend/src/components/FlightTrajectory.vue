<script setup lang="ts">
import { computed } from "vue";
import { LCircleMarker, LPolyline } from "@vue-leaflet/vue-leaflet";

import type { ApiTrajectoryPoint } from "@/types/api";

const props = defineProps<{
  points: ApiTrajectoryPoint[];
}>();

const latLngs = computed<[number, number][]>(() =>
  props.points.map((p) => [p.lat, p.lng]),
);
</script>

<template>
  <template v-if="points.length > 0">
    <LPolyline
      :lat-lngs="latLngs"
      color="#3b82f6"
      :weight="2"
      :opacity="0.75"
      :dash-array="'6 4'"
      :interactive="false"
    />
    <LCircleMarker
      v-for="(point, index) in points"
      :key="index"
      :lat-lng="[point.lat, point.lng]"
      :radius="3"
      color="#3b82f6"
      :fill-color="index === points.length - 1 ? '#3b82f6' : '#ffffff'"
      :fill-opacity="1"
      :weight="1.5"
      :interactive="false"
    />
  </template>
</template>
