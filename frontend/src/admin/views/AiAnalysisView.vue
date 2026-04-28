<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Bar, Line, Pie, Doughnut } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { aiQuery, getAiProviders, type AiQueryResponse } from "@/admin/api";

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Title, Tooltip, Legend);

const question = ref("");
const loading = ref(false);
const history = ref<{ q: string; r: AiQueryResponse }[]>([]);
const providerInfo = ref<{ configured_provider: string; api_key_set: boolean } | null>(null);
const error = ref("");

const suggestedQuestions = [
  "How many users registered in the last 7 days?",
  "Which aircraft types are most frequently logged?",
  "What are the top 10 callsigns logged this month?",
  "Show the distribution of flight altitudes logged",
  "How many requests have been blocked in the last 24 hours?",
  "What is the success rate of each flight data provider?",
];

onMounted(async () => {
  try {
    providerInfo.value = await getAiProviders();
  } catch {
    // ignore
  }
});

async function submit() {
  if (!question.value.trim()) return;
  loading.value = true;
  error.value = "";
  const q = question.value;
  question.value = "";
  try {
    const result = await aiQuery(q);
    history.value.unshift({ q, r: result });
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Query failed";
  } finally {
    loading.value = false;
  }
}

function getChartComponent(type: string | null) {
  switch (type) {
    case "line": return Line;
    case "pie": return Pie;
    case "doughnut": return Doughnut;
    default: return Bar;
  }
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

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#94a3b8" } } },
};

function buildChartData(raw: NonNullable<AiQueryResponse["chart_data"]>) {
  const colors = ["#38bdf8", "#818cf8", "#34d399", "#fb923c", "#f472b6", "#a78bfa", "#fbbf24"];
  return {
    labels: raw.labels,
    datasets: raw.datasets.map((ds, i) => ({
      ...ds,
      backgroundColor: colors[i % colors.length] + "88",
      borderColor: colors[i % colors.length],
    })),
  };
}
</script>

<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <div class="border-b border-slate-800 px-6 py-4">
      <h2 class="text-lg font-semibold text-slate-100">AI Data Analysis</h2>
      <p v-if="providerInfo" class="mt-1 text-xs text-slate-500">
        Provider: {{ providerInfo.configured_provider }}
        <span v-if="!providerInfo.api_key_set" class="ml-2 text-yellow-500">⚠ API key not configured</span>
      </p>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <!-- Input -->
      <div class="mb-6 flex gap-2">
        <input
          v-model="question"
          type="text"
          placeholder="Ask anything about your data…"
          class="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-slate-100 outline-none focus:border-blue-500"
          :disabled="loading"
          @keydown.enter="submit"
        />
        <button
          class="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          :disabled="loading || !question.trim()"
          @click="submit"
        >
          {{ loading ? "…" : "Ask" }}
        </button>
      </div>

      <!-- Suggested questions -->
      <div v-if="!history.length" class="mb-6">
        <p class="mb-2 text-xs font-medium text-slate-500 uppercase tracking-wider">Suggested questions</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="sq in suggestedQuestions"
            :key="sq"
            class="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-400 hover:border-slate-600 hover:text-slate-200"
            @click="question = sq"
          >
            {{ sq }}
          </button>
        </div>
      </div>

      <p v-if="error" class="mb-4 text-sm text-red-400">{{ error }}</p>

      <!-- History -->
      <div class="space-y-6">
        <div
          v-for="(item, i) in history"
          :key="i"
          class="rounded-xl border border-slate-800 bg-slate-900 p-5"
        >
          <p class="mb-3 text-xs font-medium text-slate-500">Q: {{ item.q }}</p>
          <p class="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">{{ item.r.answer }}</p>

          <!-- Chart -->
          <div v-if="item.r.chart_data" class="mt-4 h-64">
            <component
              :is="getChartComponent(item.r.chart_type)"
              :data="buildChartData(item.r.chart_data)"
              :options="['pie', 'doughnut'].includes(item.r.chart_type ?? '') ? pieOptions : chartOptions"
            />
          </div>

          <p v-if="item.r.model_used" class="mt-3 text-xs text-slate-600">Model: {{ item.r.model_used }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
