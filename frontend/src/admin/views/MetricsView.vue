<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Line, Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { getDailyVisitors, getDailyRequests, getApiCallStats, type DailyMetricPoint, type ApiProviderStat } from "@/admin/api";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

const days = ref(30);
const visitorsData = ref<DailyMetricPoint[]>([]);
const requestsData = ref<DailyMetricPoint[]>([]);
const apiStats = ref<ApiProviderStat[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  try {
    [visitorsData.value, requestsData.value, apiStats.value] = await Promise.all([
      getDailyVisitors(days.value),
      getDailyRequests(days.value),
      getApiCallStats(7),
    ]);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load metrics";
  }
}

onMounted(load);

function toChartData(points: DailyMetricPoint[], label: string, color: string) {
  return {
    labels: points.map((p) => p.date),
    datasets: [{ label, data: points.map((p) => p.value), borderColor: color, backgroundColor: color + "33", tension: 0.3, fill: true }],
  };
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#94a3b8" } } },
  scales: {
    x: { ticks: { color: "#64748b" }, grid: { color: "#1e293b" } },
    y: { ticks: { color: "#64748b" }, grid: { color: "#1e293b" } },
  },
};
</script>

<template>
  <div class="flex-1 overflow-y-auto p-6">
    <div class="mb-6 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-slate-100">Visitor Metrics</h2>
      <div class="flex items-center gap-2 text-sm">
        <label class="text-slate-400">Period:</label>
        <select
          v-model="days"
          class="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-slate-200"
          @change="load"
        >
          <option :value="7">7 days</option>
          <option :value="14">14 days</option>
          <option :value="30">30 days</option>
          <option :value="90">90 days</option>
        </select>
      </div>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-400">{{ error }}</p>

    <div class="grid gap-6 lg:grid-cols-2">
      <!-- Daily Visitors -->
      <div class="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h3 class="mb-3 text-sm font-medium text-slate-400">Unique Visitors / Day</h3>
        <div class="h-52">
          <Line
            v-if="visitorsData.length"
            :data="toChartData(visitorsData, 'Visitors', '#38bdf8')"
            :options="chartOptions"
          />
          <p v-else class="flex h-full items-center justify-center text-xs text-slate-600">No data</p>
        </div>
      </div>

      <!-- Daily Requests -->
      <div class="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h3 class="mb-3 text-sm font-medium text-slate-400">HTTP Requests / Day</h3>
        <div class="h-52">
          <Bar
            v-if="requestsData.length"
            :data="toChartData(requestsData, 'Requests', '#818cf8')"
            :options="chartOptions"
          />
          <p v-else class="flex h-full items-center justify-center text-xs text-slate-600">No data</p>
        </div>
      </div>

      <!-- API Call Stats -->
      <div class="rounded-xl border border-slate-800 bg-slate-900 p-4 lg:col-span-2">
        <h3 class="mb-3 text-sm font-medium text-slate-400">External API Calls (last 7 days)</h3>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-800 text-left text-xs font-medium text-slate-500">
              <th class="pb-2">Provider</th>
              <th class="pb-2">Total</th>
              <th class="pb-2">Successes</th>
              <th class="pb-2">Errors</th>
              <th class="pb-2">Success %</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stat in apiStats" :key="stat.provider" class="border-b border-slate-800/50 text-slate-300">
              <td class="py-2 font-medium">{{ stat.provider }}</td>
              <td class="py-2">{{ stat.total }}</td>
              <td class="py-2 text-green-400">{{ stat.successes }}</td>
              <td class="py-2 text-red-400">{{ stat.errors }}</td>
              <td class="py-2">
                {{ stat.total > 0 ? ((stat.successes / stat.total) * 100).toFixed(1) : "—" }}%
              </td>
            </tr>
            <tr v-if="!apiStats.length">
              <td colspan="5" class="py-4 text-center text-xs text-slate-600">No data</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
