<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getMetricsOverview, type MetricsOverview } from "@/admin/api";

const data = ref<MetricsOverview | null>(null);
const error = ref("");

onMounted(async () => {
  try {
    data.value = await getMetricsOverview();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load metrics";
  }
});

const cards = [
  { key: "total_users" as const, label: "Total Users", color: "text-blue-400" },
  { key: "active_users" as const, label: "Active Users", color: "text-green-400" },
  { key: "admin_users" as const, label: "Admins", color: "text-purple-400" },
  { key: "total_flight_logs" as const, label: "Flight Logs", color: "text-sky-400" },
  { key: "requests_today" as const, label: "Requests Today", color: "text-yellow-400" },
  { key: "unique_visitors_today" as const, label: "Visitors Today", color: "text-orange-400" },
  { key: "requests_last_7_days" as const, label: "Requests (7d)", color: "text-teal-400" },
];
</script>

<template>
  <div class="flex-1 overflow-y-auto p-6">
    <h2 class="mb-6 text-lg font-semibold text-slate-100">Dashboard</h2>

    <p v-if="error" class="mb-4 text-sm text-red-400">{{ error }}</p>

    <div v-if="data" class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      <div
        v-for="card in cards"
        :key="card.key"
        class="rounded-xl border border-slate-800 bg-slate-900 p-4"
      >
        <p class="text-xs font-medium text-slate-500">{{ card.label }}</p>
        <p class="mt-1 text-3xl font-bold" :class="card.color">
          {{ data[card.key].toLocaleString() }}
        </p>
      </div>
    </div>
    <div v-else-if="!error" class="flex items-center gap-2 text-sm text-slate-500">
      <span class="animate-spin">⟳</span> Loading…
    </div>
  </div>
</template>
