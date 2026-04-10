<script setup lang="ts">
import { computed } from "vue";
import { LCircleMarker, LPolyline, LTooltip } from "@vue-leaflet/vue-leaflet";

import { formatTimestamp } from "@/lib/format";
import type { ApiTrajectoryPoint } from "@/types/api";

const props = withDefaults(
  defineProps<{
    points: ApiTrajectoryPoint[];
    highlighted?: boolean;
  }>(),
  {
    highlighted: false,
  },
);

const latLngs = computed<[number, number][]>(() =>
  props.points.map((p) => [p.lat, p.lng]),
);

const lineColor = computed(() => (props.highlighted ? "#f59e0b" : "#3b82f6"));
const lineWeight = computed(() => (props.highlighted ? 3 : 2));
const lineOpacity = computed(() => (props.highlighted ? 0.9 : 0.75));

function formatTrajectoryTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return formatTimestamp(date.toISOString());
}
</script>

<template>
  <template v-if="points.length > 0">
    <LPolyline
      :lat-lngs="latLngs"
      :color="lineColor"
      :weight="lineWeight"
      :opacity="lineOpacity"
      :dash-array="highlighted ? 'none' : '6 4'"
      :interactive="false"
    />
    <LCircleMarker
      v-for="(point, index) in points"
      :key="index"
      :lat-lng="[point.lat, point.lng]"
      :radius="highlighted ? 4 : 3"
      :color="lineColor"
      :fill-color="index === points.length - 1 ? lineColor : '#ffffff'"
      :fill-opacity="1"
      :weight="highlighted ? 2 : 1.5"
    >
      <LTooltip :options="{ permanent: false, direction: 'top' }">
        {{ formatTrajectoryTimestamp(point.timestamp) }}
      </LTooltip>
    </LCircleMarker>
  </template>
</template>
