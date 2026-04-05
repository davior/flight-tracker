<script setup lang="ts">
const props = defineProps<{
  value: number;
}>();

const emit = defineEmits<{
  "update:value": [value: number];
}>();

function handleInput(event: Event): void {
  const target = event.target as HTMLInputElement;
  emit("update:value", Number(target.value));
}

function formatWindowLabel(value: number): string {
  if (value === 0.5) {
    return "Showing logs from last 12 hours";
  }
  if (value === 1) {
    return "Showing logs from last 1 day";
  }
  if (Number.isInteger(value)) {
    return `Showing logs from last ${value} days`;
  }
  return `Showing logs from last ${value} days`;
}

const tickLabels = [
  { value: 0.5, label: "0.5d" },
  { value: 7, label: "7d" },
  { value: 14, label: "14d" },
  { value: 21, label: "21d" },
  { value: 28, label: "28d" },
];
</script>

<template>
  <section
    class="glass-panel time-shift-panel safe-bottom absolute ml-3 mr-3 inset-x-0 bottom-21 z-[900] rounded-[1.75rem] px-4 py-3 md:left-[25px] md:right-[25px] md:px-5 md:py-2.5"
  >
    <div>
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Time Window</p>
      <p class="text-sm font-semibold text-[var(--ink)]">
        {{ formatWindowLabel(props.value) }}
      </p>
    </div>

    <label class="sr-only" for="logged-time-window">Logged flight time window</label>
    <input
      id="logged-time-window"
      class="time-shift-slider mt-3 w-full"
      type="range"
      min="0.5"
      max="28"
      step="0.5"
      :value="props.value"
      @input="handleInput"
    />

    <div class="mt-1.5 grid grid-cols-5 text-[11px] font-medium text-[var(--muted)]">
      <span
        v-for="tick in tickLabels"
        :key="tick.value"
        :class="tick.value === 0.5 ? 'text-left' : tick.value === 28 ? 'text-right' : 'text-center'"
      >
        {{ tick.label }}
      </span>
    </div>
  </section>
</template>
