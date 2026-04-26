<script setup lang="ts">
import ProviderStatusDot from "@/components/ProviderStatusDot.vue";
import type { ApiProviderStatus } from "@/types/api";

defineProps<{
  providerStatus: ApiProviderStatus | null;
}>();

defineEmits<{
  location: [];
  refresh: [];
  profile: [];
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
    <button
      class="glass-panel flex h-14 w-14 items-center justify-center rounded-2xl text-[var(--muted)]"
      aria-label="Account settings"
      title="Account settings"
      @click="$emit('profile')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
      </svg>
    </button>
    <button
      class="glass-panel flex h-14 w-14 items-center justify-center rounded-2xl text-[var(--accent)]"
      aria-label="Refresh"
      title="Refresh"
      @click="$emit('refresh')"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
      </svg>
    </button>
    <ProviderStatusDot :provider-status="providerStatus" />
  </div>
</template>
