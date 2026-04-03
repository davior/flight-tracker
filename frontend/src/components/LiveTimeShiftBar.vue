<script setup lang="ts">
const props = defineProps<{
  value: number;
  disabled: boolean;
  helperText: string;
}>();

const emit = defineEmits<{
  "update:value": [value: number];
}>();

function handleInput(event: Event): void {
  const target = event.target as HTMLInputElement;
  emit("update:value", Number(target.value));
}

const tickLabels = [
  { value: 0, label: "Now" },
  { value: 10, label: "10m" },
  { value: 20, label: "20m" },
  { value: 30, label: "30m" },
  { value: 40, label: "40m" },
  { value: 50, label: "50m" },
  { value: 60, label: "1h" },
];
</script>

<template>
  <section
    class="glass-panel time-shift-panel safe-bottom absolute inset-x-0 bottom-24 z-[900] rounded-[1.75rem] px-4 py-3 md:left-[25px] md:right-[25px] md:px-5 md:py-2.5"
    :class="disabled ? 'opacity-80' : ''"
  >
    <div class="flex items-center justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Time Shift</p>
        <p class="text-sm font-semibold text-[var(--ink)]">
          {{ props.value === 0 ? "Now" : `${props.value} min ago` }}
        </p>
      </div>
      <span
        class="rounded-full px-3 py-1 text-xs font-semibold"
        :class="disabled ? 'bg-slate-200 text-[var(--muted)]' : 'bg-[var(--accent-soft)] text-[var(--accent)]'"
      >
        {{ disabled ? "Unavailable" : "Live replay" }}
      </span>
    </div>

    <label class="sr-only" for="live-time-shift">Live time shift</label>
    <input
      id="live-time-shift"
      class="time-shift-slider mt-3 w-full"
      type="range"
      min="0"
      max="60"
      step="1"
      :value="props.value"
      :disabled="disabled"
      @input="handleInput"
    />

    <div class="mt-1.5 grid grid-cols-7 text-[11px] font-medium text-[var(--muted)]">
      <span
        v-for="tick in tickLabels"
        :key="tick.value"
        :class="tick.value === 0 ? 'text-left' : tick.value === 60 ? 'text-right' : 'text-center'"
      >
        {{ tick.label }}
      </span>
    </div>

    <p class="mt-2 text-xs text-[var(--muted)]">
      {{ helperText }}
    </p>
  </section>
</template>
