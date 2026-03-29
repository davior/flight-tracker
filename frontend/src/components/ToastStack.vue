<script setup lang="ts">
defineProps<{
  message: string | null;
}>();
</script>

<template>
  <div v-if="message" class="pointer-events-none absolute left-1/2 top-20 z-[990] -translate-x-1/2">
    <div class="glass-panel rounded-full px-4 py-2 text-sm font-semibold text-[var(--ink)]">
      {{ message }}
    </div>
  </div>
</template>
