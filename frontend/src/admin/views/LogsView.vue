<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  getRequestLogs,
  getBlockedIps,
  blockIp,
  unblockIp,
  analyzeThreats,
  type RequestLogItem,
  type IpBlock,
  type AiQueryResponse,
} from "@/admin/api";

const tab = ref<"requests" | "blocked" | "threats">("requests");

// Request logs
const logs = ref<RequestLogItem[]>([]);
const logsTotal = ref(0);
const logsPage = ref(1);
const filterIp = ref("");
const filterPath = ref("");
const filterStatus = ref(0);
const logsLoading = ref(false);

// Blocked IPs
const blocked = ref<IpBlock[]>([]);
const blockForm = ref({ ip: "", reason: "", hours: "24" });
const showBlockForm = ref(false);

// Threats
const threatResult = ref<AiQueryResponse | null>(null);
const threatLoading = ref(false);

const toast = ref("");
const error = ref("");

function showToast(msg: string) {
  toast.value = msg;
  setTimeout(() => (toast.value = ""), 3000);
}

async function loadLogs() {
  logsLoading.value = true;
  try {
    const res = await getRequestLogs(logsPage.value, filterIp.value, filterPath.value, filterStatus.value);
    logs.value = res.items;
    logsTotal.value = res.total;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  } finally {
    logsLoading.value = false;
  }
}

async function loadBlocked() {
  try {
    blocked.value = await getBlockedIps();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function doBlock() {
  try {
    const hours = parseInt(blockForm.value.hours) || undefined;
    await blockIp(blockForm.value.ip, blockForm.value.reason || undefined, hours);
    showToast("IP blocked");
    showBlockForm.value = false;
    blockForm.value = { ip: "", reason: "", hours: "24" };
    await loadBlocked();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function doUnblock(ip: string) {
  if (!confirm(`Unblock ${ip}?`)) return;
  try {
    await unblockIp(ip);
    showToast("IP unblocked");
    await loadBlocked();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function runThreatAnalysis() {
  threatLoading.value = true;
  threatResult.value = null;
  try {
    threatResult.value = await analyzeThreats();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "AI analysis failed";
  } finally {
    threatLoading.value = false;
  }
}

onMounted(() => {
  loadLogs();
  loadBlocked();
});

function statusColor(code: number) {
  if (code < 300) return "text-green-400";
  if (code < 400) return "text-yellow-400";
  if (code < 500) return "text-orange-400";
  return "text-red-400";
}
</script>

<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Header -->
    <div class="border-b border-slate-800 px-6 py-4">
      <h2 class="text-lg font-semibold text-slate-100">Logs</h2>
      <div class="mt-3 flex gap-4 border-b border-slate-800 -mb-4">
        <button
          v-for="t in ['requests', 'blocked', 'threats'] as const"
          :key="t"
          class="pb-3 text-sm capitalize transition-colors"
          :class="tab === t ? 'border-b-2 border-blue-500 text-blue-400' : 'text-slate-500 hover:text-slate-300'"
          @click="tab = t"
        >
          {{ t === "requests" ? "Request Logs" : t === "blocked" ? "Blocked IPs" : "Threat Analysis" }}
        </button>
      </div>
    </div>

    <p v-if="error" class="mx-6 mt-3 text-xs text-red-400">{{ error }}</p>

    <!-- Request Logs Tab -->
    <div v-if="tab === 'requests'" class="flex flex-1 flex-col overflow-hidden">
      <div class="flex flex-wrap gap-2 border-b border-slate-800 px-6 py-3">
        <input v-model="filterIp" type="text" placeholder="Filter IP" class="admin-input w-36" @keydown.enter="loadLogs" />
        <input v-model="filterPath" type="text" placeholder="Filter path" class="admin-input w-48" @keydown.enter="loadLogs" />
        <input v-model.number="filterStatus" type="number" placeholder="Status code" class="admin-input w-28" @keydown.enter="loadLogs" />
        <button class="text-xs text-blue-400 hover:text-blue-300" @click="logsPage = 1; loadLogs()">Apply</button>
      </div>
      <div class="flex-1 overflow-y-auto">
        <table class="w-full text-xs">
          <thead class="sticky top-0 bg-slate-900">
            <tr class="border-b border-slate-800 text-left font-medium text-slate-500">
              <th class="px-4 py-2">Time</th>
              <th class="px-4 py-2">IP</th>
              <th class="px-4 py-2">Method</th>
              <th class="px-4 py-2">Path</th>
              <th class="px-4 py-2">Status</th>
              <th class="px-4 py-2">ms</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="log in logs"
              :key="log.id"
              class="border-b border-slate-800/40 text-slate-300 hover:bg-slate-800/20"
            >
              <td class="px-4 py-1.5 text-slate-500">{{ new Date(log.requested_at).toLocaleTimeString() }}</td>
              <td class="px-4 py-1.5 font-mono">{{ log.ip_address }}</td>
              <td class="px-4 py-1.5">{{ log.method }}</td>
              <td class="max-w-xs truncate px-4 py-1.5 font-mono">{{ log.path }}</td>
              <td class="px-4 py-1.5 font-mono" :class="statusColor(log.status_code)">{{ log.status_code }}</td>
              <td class="px-4 py-1.5 text-slate-500">{{ log.duration_ms }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="logsLoading" class="py-4 text-center text-xs text-slate-500">Loading…</div>
      </div>
      <div class="flex items-center justify-between border-t border-slate-800 px-6 py-2 text-xs text-slate-500">
        <span>{{ logsTotal }} total</span>
        <div class="flex gap-2">
          <button :disabled="logsPage <= 1" class="disabled:opacity-30" @click="logsPage--; loadLogs()">← Prev</button>
          <span>{{ logsPage }}</span>
          <button :disabled="logs.length < 100" class="disabled:opacity-30" @click="logsPage++; loadLogs()">Next →</button>
        </div>
      </div>
    </div>

    <!-- Blocked IPs Tab -->
    <div v-else-if="tab === 'blocked'" class="flex-1 overflow-y-auto p-6">
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-sm font-medium text-slate-300">Blocked IPs ({{ blocked.length }})</h3>
        <button class="admin-btn-primary text-xs" @click="showBlockForm = !showBlockForm">+ Block IP</button>
      </div>

      <div v-if="showBlockForm" class="mb-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
        <div class="flex flex-wrap gap-3">
          <input v-model="blockForm.ip" type="text" placeholder="IP address" class="admin-input w-44" />
          <input v-model="blockForm.reason" type="text" placeholder="Reason (optional)" class="admin-input flex-1" />
          <input v-model="blockForm.hours" type="number" placeholder="Hours (blank=permanent)" class="admin-input w-36" />
          <button class="admin-btn-primary text-xs" @click="doBlock">Block</button>
          <button class="admin-btn-secondary text-xs" @click="showBlockForm = false">Cancel</button>
        </div>
      </div>

      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-slate-800 text-left text-xs font-medium text-slate-500">
            <th class="pb-2">IP</th>
            <th class="pb-2">Reason</th>
            <th class="pb-2">Blocked</th>
            <th class="pb-2">Releases</th>
            <th class="pb-2">Type</th>
            <th class="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in blocked" :key="b.ip_address" class="border-b border-slate-800/50 text-slate-300">
            <td class="py-2 font-mono text-xs">{{ b.ip_address }}</td>
            <td class="py-2 text-xs text-slate-400">{{ b.reason ?? "—" }}</td>
            <td class="py-2 text-xs text-slate-500">{{ new Date(b.blocked_at).toLocaleString() }}</td>
            <td class="py-2 text-xs text-slate-500">{{ b.release_at ? new Date(b.release_at).toLocaleString() : "Permanent" }}</td>
            <td class="py-2 text-xs" :class="b.auto_blocked ? 'text-yellow-400' : 'text-blue-400'">
              {{ b.auto_blocked ? "Auto" : "Manual" }}
            </td>
            <td class="py-2">
              <button class="text-xs text-red-400 hover:text-red-300" @click="doUnblock(b.ip_address)">Unblock</button>
            </td>
          </tr>
          <tr v-if="!blocked.length">
            <td colspan="6" class="py-6 text-center text-xs text-slate-600">No blocked IPs</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Threat Analysis Tab -->
    <div v-else-if="tab === 'threats'" class="flex-1 overflow-y-auto p-6">
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-sm font-medium text-slate-300">AI Threat Analysis</h3>
        <button
          class="admin-btn-primary text-xs"
          :disabled="threatLoading"
          @click="runThreatAnalysis"
        >
          {{ threatLoading ? "Analysing…" : "Run Analysis" }}
        </button>
      </div>

      <div v-if="threatResult" class="rounded-xl border border-slate-700 bg-slate-900 p-5">
        <p class="whitespace-pre-wrap text-sm text-slate-300">{{ threatResult.answer }}</p>
        <p v-if="threatResult.model_used" class="mt-3 text-xs text-slate-600">Model: {{ threatResult.model_used }}</p>
      </div>
      <p v-else-if="!threatLoading" class="text-sm text-slate-500">
        Click "Run Analysis" to use AI to detect suspicious patterns in the request logs.
      </p>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="fixed bottom-6 right-6 rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-100 shadow-xl">
      {{ toast }}
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";

.admin-input {
  @apply rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-blue-500;
}
.admin-btn-primary {
  @apply rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50;
}
.admin-btn-secondary {
  @apply rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700;
}
</style>
