<script setup lang="ts">

defineEmits<{
  location: [];
  refresh: [];
  filters: [];
}>();
</script>

<template>
  <div class="absolute right-3 top-3 z-[900] flex flex-col gap-2">
    <button
      class="glass-panel flex h-14 w-14 items-center justify-center rounded-2xl"
      aria-label="Location settings"
      title="Location settings"
      @click="$emit('location')"
    >
      <span class="location-settings-icon" aria-hidden="true">
        <span class="location-settings-icon__ring"></span>
        <span class="location-settings-icon__dot"></span>
      </span>
    </button>
  </div>
</template>
