<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import type { ApiProviderStatus } from "@/types/api";

const props = defineProps<{
  providerStatus: ApiProviderStatus | null;
}>();

const open = ref(false);
const containerRef = ref<HTMLElement | null>(null);

const activeProvider = computed(() =>
  props.providerStatus?.providers.find((p) => p.is_active) ?? null,
);

const dotColor = computed(() => {
  if (!props.providerStatus) return "bg-[var(--muted)] opacity-50";
  return activeProvider.value?.is_healthy ? "bg-green-500" : "bg-red-500";
});

const dotTitle = computed(() => {
  if (!props.providerStatus) return "Provider status loading…";
  const p = activeProvider.value;
  if (!p) return "No active provider";
  return p.is_healthy ? `${p.name} — healthy` : `${p.name} — last request failed`;
});

function formatUsage(p: NonNullable<typeof activeProvider.value>): string {
  const count = p.requests_in_period;
  const max = p.max_requests;
  const period = p.period_seconds;
  const periodLabel = period ? formatPeriod(period) : null;
  if (max !== null && periodLabel) return `${count} / ${max} requests (last ${periodLabel})`;
  if (max !== null) return `${count} / ${max} requests`;
  return `${count} requests`;
}

function formatPeriod(seconds: number): string {
  if (seconds >= 86400) return `${seconds / 86400}d`;
  if (seconds >= 3600) return `${seconds / 3600}h`;
  return `${seconds}s`;
}

function formatRateLimitUntil(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function handleClickOutside(e: MouseEvent): void {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener("mousedown", handleClickOutside));
onUnmounted(() => document.removeEventListener("mousedown", handleClickOutside));
</script>

<template>
  <div ref="containerRef" class="relative">
    <button
      class="glass-panel flex h-14 w-14 items-center justify-center rounded-2xl"
      :aria-label="dotTitle"
      :title="dotTitle"
      @click="open = !open"
    >
      <span
        class="block h-3 w-3 rounded-full transition-colors duration-300"
        :class="dotColor"
        aria-hidden="true"
      />
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="open && providerStatus"
        class="glass-panel absolute right-16 top-0 z-[1000] w-64 origin-top-right rounded-2xl p-4 text-sm"
      >
        <p class="mb-3 font-semibold text-[var(--fg)]">Live data providers</p>

        <div
          v-for="provider in providerStatus.providers"
          :key="provider.name"
          class="mb-3 last:mb-0"
        >
          <div class="flex items-center gap-2">
            <span
              class="block h-2.5 w-2.5 shrink-0 rounded-full"
              :class="provider.is_healthy ? 'bg-green-500' : 'bg-red-500'"
            />
            <span class="font-medium capitalize text-[var(--fg)]">
              {{ provider.name }}
              <span
                v-if="provider.is_active"
                class="ml-1 rounded-full bg-[var(--accent-soft)] px-1.5 py-0.5 text-xs font-semibold text-[var(--accent)]"
              >active</span>
            </span>
          </div>

          <div class="ml-4.5 mt-1 space-y-0.5 text-xs text-[var(--muted)]">
            <p>{{ formatUsage(provider) }}</p>
            <p v-if="provider.rate_limited_until">
              Rate limited until {{ formatRateLimitUntil(provider.rate_limited_until) }}
            </p>
            <p v-if="provider.last_error_code && !provider.is_healthy">
              Last error: {{ provider.last_error_code }}
            </p>
            <p>
              Time-shift:
              <span :class="provider.supports_time_shift ? 'text-green-600' : 'text-[var(--muted)]'">
                {{ provider.supports_time_shift ? "✓" : "✗" }}
              </span>
              &nbsp;Trajectory:
              <span :class="provider.supports_trajectory ? 'text-green-600' : 'text-[var(--muted)]'">
                {{ provider.supports_trajectory ? "✓" : "✗" }}
              </span>
            </p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
