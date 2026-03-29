<script setup lang="ts">
import type { AppMode } from "@/types/api";

defineProps<{
  mode: AppMode;
}>();

defineEmits<{
  "update:mode": [mode: AppMode];
}>();
</script>

<template>
  <nav class="glass-panel safe-bottom absolute inset-x-3 bottom-3 z-[900] rounded-[2rem] px-2 py-2 md:left-1/2 md:max-w-sm md:-translate-x-1/2">
    <div class="grid grid-cols-2 gap-2">
      <button
        class="rounded-2xl px-4 py-3 text-sm font-semibold transition"
        :class="mode === 'live' ? 'bg-[var(--live)] text-white' : 'bg-white/70 text-[var(--muted)]'"
        @click="$emit('update:mode', 'live')"
      >
        Live Flights
      </button>
      <button
        class="rounded-2xl px-4 py-3 text-sm font-semibold transition"
        :class="mode === 'logged' ? 'bg-[var(--logged)] text-white' : 'bg-white/70 text-[var(--muted)]'"
        @click="$emit('update:mode', 'logged')"
      >
        Logged Flights
      </button>
    </div>
  </nav>
</template>
