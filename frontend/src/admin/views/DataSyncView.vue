<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getDataSyncStatus, triggerSync, type DataSyncStatus } from "@/admin/api";

const statuses = ref<DataSyncStatus[]>([]);
const loading = ref(false);
const triggering = ref<string | null>(null);
const toast = ref("");
const error = ref("");

function showToast(msg: string) {
  toast.value = msg;
  setTimeout(() => (toast.value = ""), 3000);
}

async function load() {
  loading.value = true;
  try {
    statuses.value = await getDataSyncStatus();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  } finally {
    loading.value = false;
  }
}

async function trigger(source: string) {
  triggering.value = source;
  try {
    const res = await triggerSync(source);
    showToast(res.message);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  } finally {
    triggering.value = null;
  }
}

onMounted(load);

function statusBadge(status: string | null) {
  if (status === "ok") return "text-green-400";
  if (status === "error") return "text-red-400";
  if (status === "running") return "text-yellow-400";
  return "text-slate-500";
}

const SOURCE_LABELS: Record<string, string> = {
  opensky_aircraft: "OpenSky Aircraft Registry",
  faa_aircraft: "FAA Aircraft Registry",
  ourairports: "OurAirports",
  opensky_routes: "OpenSky Routes",
  openflights_routes: "OpenFlights Routes",
};
</script>

<template>
  <div class="flex-1 overflow-y-auto p-6">
    <div class="mb-6 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-slate-100">Data Sync Status</h2>
      <button class="text-xs text-slate-400 hover:text-slate-200" @click="load">↻ Refresh</button>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-400">{{ error }}</p>

    <div class="space-y-3">
      <div
        v-for="s in statuses"
        :key="s.source"
        class="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 p-4"
      >
        <div>
          <p class="text-sm font-medium text-slate-200">{{ SOURCE_LABELS[s.source] ?? s.source }}</p>
          <p class="mt-0.5 text-xs text-slate-500">
            Last sync: {{ s.last_synced_at ? new Date(s.last_synced_at).toLocaleString() : "Never" }}
            <span v-if="s.row_count !== null"> · {{ s.row_count.toLocaleString() }} rows</span>
          </p>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs font-medium uppercase" :class="statusBadge(s.last_sync_status)">
            {{ s.last_sync_status ?? "Unknown" }}
          </span>
          <button
            class="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50"
            :disabled="triggering === s.source"
            @click="trigger(s.source)"
          >
            {{ triggering === s.source ? "Triggering…" : "Sync Now" }}
          </button>
        </div>
      </div>
      <div v-if="loading" class="py-6 text-center text-sm text-slate-500">Loading…</div>
      <div v-if="!loading && !statuses.length" class="py-6 text-center text-sm text-slate-600">
        No sync records found
      </div>
    </div>

    <div v-if="toast" class="fixed bottom-6 right-6 rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-100 shadow-xl">
      {{ toast }}
    </div>
  </div>
</template>
