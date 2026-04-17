<script setup lang="ts">
import { ref } from "vue";

const emit = defineEmits<{ done: [] }>();

const step = ref(0);

const steps = [
  {
    title: "Set your location",
    description:
      "Tap the target icon in the top-right corner to choose between automatic GPS location or set your position manually on the map.",
    icon: "target",
  },
  {
    title: "Select a flight to log it",
    description:
      "Aircraft markers appear on the map in real time. Tap any aircraft to see its details, then tap \"Report this flight\" to log your sighting.",
    icon: "plane",
  },
  {
    title: "Document your sighting",
    description:
      "Add a personal note and upload up to 3 photos to capture the moment. Your location is automatically recorded.",
    icon: "camera",
  },
  {
    title: "Browse logged flights",
    description:
      "Switch to \"Logged Flights\" in the bottom navigation to see all recorded sightings on the map or in a list view.",
    icon: "list",
  },
] as const;

const isLast = () => step.value === steps.length - 1;

function next(): void {
  if (isLast()) {
    emit("done");
  } else {
    step.value++;
  }
}
</script>

<template>
  <div class="absolute inset-0 z-[2000] flex items-end bg-slate-950/60 p-3 md:items-center md:justify-center">
    <div class="glass-panel w-full rounded-[2rem] p-6 md:max-w-md">
      <!-- Progress dots -->
      <div class="mb-6 flex justify-center gap-2">
        <div
          v-for="(_, i) in steps"
          :key="i"
          class="h-1.5 rounded-full transition-all"
          :class="i === step ? 'w-6 bg-[var(--accent)]' : 'w-1.5 bg-white/20'"
        ></div>
      </div>

      <!-- Step content -->
      <div class="mb-6 text-center">
        <!-- Icons -->
        <div class="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-[var(--accent)]/15">
          <!-- Target icon -->
          <svg v-if="steps[step].icon === 'target'" class="h-10 w-10 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1.5M12 19.5V21M3 12H4.5M19.5 12H21M6.343 6.343l1.06 1.061M16.597 16.597l1.06 1.06M6.343 17.657l1.06-1.06M16.597 7.403l1.06-1.06M12 8.25a3.75 3.75 0 100 7.5 3.75 3.75 0 000-7.5z" />
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5" fill="none" />
          </svg>
          <!-- Plane icon -->
          <svg v-else-if="steps[step].icon === 'plane'" class="h-10 w-10 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
          <!-- Camera icon -->
          <svg v-else-if="steps[step].icon === 'camera'" class="h-10 w-10 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
          </svg>
          <!-- List icon -->
          <svg v-else-if="steps[step].icon === 'list'" class="h-10 w-10 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
        </div>

        <p class="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--muted)]">
          Step {{ step + 1 }} of {{ steps.length }}
        </p>
        <h2 class="mt-1 text-xl font-bold">{{ steps[step].title }}</h2>
        <p class="mt-3 text-sm leading-relaxed text-[var(--muted)]">{{ steps[step].description }}</p>
      </div>

      <button
        class="w-full rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-white transition-opacity"
        @click="next"
      >
        {{ isLast() ? "Get Started!" : "Next" }}
      </button>
    </div>
  </div>
</template>
