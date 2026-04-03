<script setup lang="ts">
import type { AppView } from "@/types/api";

defineProps<{
  view: AppView;
}>();

defineEmits<{
  "update:view": [view: AppView];
}>();
</script>

<template>
  <div class="glass-panel absolute left-3 top-3 z-[900] flex rounded-full p-1">
    <button
      class="rounded-full px-4 py-2 text-sm font-medium"
      :class="view === 'map' ? 'bg-[var(--ink)] !text-white' : 'text-[var(--muted)]'"
      @click="$emit('update:view', 'map')"
    >
      Map
    </button>
    <button
      class="rounded-full px-4 py-2 text-sm font-medium"
      :class="view === 'list' ? 'bg-[var(--ink)] !text-white' : 'text-[var(--muted)]'"
      @click="$emit('update:view', 'list')"
    >
      List
    </button>
  </div>
</template>
