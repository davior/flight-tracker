<script setup lang="ts">
defineProps<{
  modeLabel: string;
}>();

defineEmits<{
  center: [];
  manual: [];
  refresh: [];
  filters: [];
}>();
</script>

<template>
  <div class="absolute right-3 top-20 z-[900] flex flex-col gap-2">
    <button class="glass-panel rounded-2xl px-4 py-3 text-sm font-semibold" @click="$emit('center')">
      Center
    </button>
    <button class="glass-panel rounded-2xl px-4 py-3 text-sm font-semibold" @click="$emit('manual')">
      Manual
    </button>
    <button class="glass-panel rounded-2xl px-4 py-3 text-sm font-semibold" @click="$emit('refresh')">
      Refresh
    </button>
    <button class="glass-panel rounded-2xl px-4 py-3 text-sm font-semibold" @click="$emit('filters')">
      {{ modeLabel }}
    </button>
  </div>
</template>
