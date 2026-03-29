<script setup lang="ts">
import type { TimeWindow } from "@/types/api";

const options: Array<{ value: TimeWindow; label: string }> = [
  { value: "3h", label: "3 hours" },
  { value: "6h", label: "6 hours" },
  { value: "12h", label: "12 hours" },
  { value: "1d", label: "1 day" },
  { value: "3d", label: "3 days" },
  { value: "7d", label: "1 week" },
  { value: "14d", label: "2 weeks" },
  { value: "30d", label: "1 month" },
];

defineProps<{
  open: boolean;
  value: TimeWindow;
}>();

defineEmits<{
  close: [];
  select: [value: TimeWindow];
}>();
</script>

<template>
  <div v-if="open" class="absolute inset-0 z-[980] flex items-end bg-slate-950/40 p-3 md:items-center md:justify-center">
    <div class="glass-panel w-full rounded-[2rem] p-5 md:max-w-md">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Logged flight filter</p>
          <h2 class="text-xl font-bold">Time window</h2>
        </div>
        <button class="rounded-full bg-white/70 px-3 py-1 text-sm font-semibold" @click="$emit('close')">Close</button>
      </div>
      <div class="mt-4 space-y-2">
        <button
          v-for="option in options"
          :key="option.value"
          class="flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left"
          :class="value === option.value ? 'bg-[var(--accent)] text-white' : 'bg-white/70 text-[var(--ink)]'"
          @click="$emit('select', option.value)"
        >
          <span>{{ option.label }}</span>
          <span class="text-xs uppercase">{{ option.value }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
