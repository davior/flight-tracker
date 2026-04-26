<script setup lang="ts">
import { ref } from "vue";
import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";
import { formatTimestamp } from "@/lib/format";
import { formatDistance } from "@/lib/geo";
import type { ApiLoggedFlight } from "@/types/api";
import { useLogsStore } from "@/stores/logs";
import { useUiStore } from "@/stores/ui";
import MediaViewer from "@/components/MediaViewer.vue";

function loggedByLine(flight: ApiLoggedFlight): string | null {
  if (!flight.owner_username) {
    return null;
  }
  return `Logged by ${flight.owner_username} at ${formatTimestamp(flight.created_at)}`;
}

const props = defineProps<{
  flight: ApiLoggedFlight | null;
  inline?: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const logsStore = useLogsStore();
const uiStore = useUiStore();

const isEditing = ref(false);
const editNote = ref("");
const isSaving = ref(false);
const isDeleting = ref(false);
const confirmingDelete = ref(false);

const viewerOpen = ref(false);
const viewerStartIndex = ref(0);

function openViewer(index: number) {
  viewerStartIndex.value = index;
  viewerOpen.value = true;
}

function startEdit() {
  editNote.value = props.flight?.note ?? "";
  isEditing.value = true;
}

function cancelEdit() {
  isEditing.value = false;
}

async function saveEdit() {
  if (!props.flight) return;
  isSaving.value = true;
  try {
    await logsStore.patchLogNote(props.flight.id, editNote.value.trim() || null);
    isEditing.value = false;
  } catch {
    uiStore.showToast("Failed to update note.");
  } finally {
    isSaving.value = false;
  }
}

async function confirmDelete() {
  if (!props.flight) return;
  isDeleting.value = true;
  try {
    await logsStore.deleteLogById(props.flight.id);
    emit("close");
  } catch {
    uiStore.showToast("Failed to delete log.");
    confirmingDelete.value = false;
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div
    v-if="flight && !inline"
    class="absolute inset-0 z-[1000] flex items-end bg-slate-950/40 p-3 md:items-center md:justify-center"
  >
    <div class="glass-panel w-full rounded-[2rem] p-5 md:max-w-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Flight detail</p>
          <h2 class="text-xl font-bold">{{ flight.callsign || flight.icao24.toUpperCase() }}</h2>
          <p class="text-sm text-[var(--muted)]">{{ getAircraftDisplayLabel(flight) || "Aircraft type unavailable" }}</p>
          <p v-if="flight.operator" class="mt-1 text-xs text-[var(--muted)]">
            {{ flight.operator }}<span v-if="flight.operator_icao"> ({{ flight.operator_icao }})</span>
          </p>
          <p v-if="flight.owner && flight.owner !== flight.operator" class="mt-0.5 text-xs text-[var(--muted)]">
            Owner: {{ flight.owner }}
          </p>
          <p v-if="loggedByLine(flight)" class="mt-2 text-xs text-[var(--muted)]">
            {{ loggedByLine(flight) }}
          </p>
        </div>
        <button class="rounded-full bg-white/70 p-2 text-sm font-semibold hover:bg-white/90" @click="$emit('close')" aria-label="Close">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Distance</p>
          <p class="mt-1 font-semibold">{{ formatDistance(flight.distance_km) }}</p>
        </div>
        <div class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Flight Time</p>
          <p class="mt-1 font-semibold">{{ formatTimestamp(flight.flight_time) }}</p>
        </div>
        <div v-if="flight.icao24" class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">ICAO24</p>
          <p class="mt-1 font-semibold font-mono">{{ flight.icao24.toUpperCase() }}</p>
        </div>
        <div v-if="flight.aircraft_registry?.registration" class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Registration</p>
          <p class="mt-1 font-semibold">{{ flight.aircraft_registry.registration }}</p>
        </div>
        <div v-if="flight.serial_number" class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Serial (MSN)</p>
          <p class="mt-1 font-semibold">{{ flight.serial_number }}</p>
        </div>
        <div v-if="flight.year_built" class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Year Built</p>
          <p class="mt-1 font-semibold">{{ flight.year_built }}</p>
        </div>
        <div v-if="flight.engines" class="rounded-2xl bg-white/70 p-3 col-span-2">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Engines</p>
          <p class="mt-1 font-semibold">{{ flight.engines }}</p>
        </div>
        <div v-if="formatAircraftCategory(flight)" class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Category</p>
          <p class="mt-1 font-semibold">{{ formatAircraftCategory(flight) }}</p>
        </div>
        <div v-if="flight.icao_aircraft_type" class="rounded-2xl bg-white/70 p-3">
          <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">ICAO Type</p>
          <p class="mt-1 font-semibold font-mono">{{ flight.icao_aircraft_type }}</p>
        </div>
      </div>

      <template v-if="isEditing">
        <textarea
          v-model="editNote"
          class="mt-4 w-full rounded-3xl bg-white/70 p-4 text-sm text-[var(--ink)] resize-none focus:outline-none"
          rows="3"
          placeholder="Add a note…"
        />
        <div class="mt-2 flex gap-2">
          <button
            class="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            :disabled="isSaving"
            @click="saveEdit"
          >{{ isSaving ? "Saving…" : "Save" }}</button>
          <button
            class="rounded-full bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white/90"
            :disabled="isSaving"
            @click="cancelEdit"
          >Cancel</button>
        </div>
      </template>
      <p v-else class="mt-4 rounded-3xl bg-white/70 p-4 text-sm text-[var(--muted)]">{{ flight.note || "No note added." }}</p>

      <div v-if="flight.photos.length" class="mt-4 grid grid-cols-3 gap-3">
        <button
          v-for="(photo, index) in flight.photos"
          :key="photo.id"
          class="relative cursor-pointer overflow-hidden rounded-2xl"
          @click="openViewer(index)"
        >
          <video
            v-if="photo.media_type === 'video'"
            :src="photo.url"
            class="h-24 w-full object-cover"
            muted
            playsinline
          />
          <img v-else :src="photo.url" alt="" class="h-24 w-full object-cover" />
          <div
            v-if="photo.media_type === 'video'"
            class="absolute inset-0 flex items-center justify-center bg-black/20"
          >
            <svg class="h-8 w-8 text-white drop-shadow-lg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        </button>
      </div>

      <template v-if="flight.is_owner && !isEditing">
        <div v-if="confirmingDelete" class="mt-4 rounded-2xl bg-red-50/80 p-3 text-sm">
          <p class="font-semibold text-red-700">Delete this log?</p>
          <p class="mt-1 text-red-600">This cannot be undone.</p>
          <div class="mt-3 flex gap-2">
            <button
              class="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              :disabled="isDeleting"
              @click="confirmDelete"
            >{{ isDeleting ? "Deleting…" : "Yes, delete" }}</button>
            <button
              class="rounded-full bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white/90"
              :disabled="isDeleting"
              @click="confirmingDelete = false"
            >Cancel</button>
          </div>
        </div>
        <div v-else class="mt-4 flex gap-2">
          <button
            class="rounded-full bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white/90"
            @click="startEdit"
          >Edit note</button>
          <button
            class="rounded-full bg-red-100/80 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-200/80"
            @click="confirmingDelete = true"
          >Delete</button>
        </div>
      </template>
    </div>
  </div>
  <aside
    v-else-if="flight && inline"
    class="glass-panel rounded-[2rem] p-5 m-6 h-[calc(100%-9rem)] overflow-y-auto"
  >
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Flight detail</p>
        <h2 class="text-xl font-bold">{{ flight.callsign || flight.icao24.toUpperCase() }}</h2>
        <p class="text-sm text-[var(--muted)]">{{ getAircraftDisplayLabel(flight) || "Aircraft type unavailable" }}</p>
        <p v-if="flight.operator" class="mt-1 text-xs text-[var(--muted)]">
          {{ flight.operator }}<span v-if="flight.operator_icao"> ({{ flight.operator_icao }})</span>
        </p>
        <p v-if="flight.owner && flight.owner !== flight.operator" class="mt-0.5 text-xs text-[var(--muted)]">
          Owner: {{ flight.owner }}
        </p>
        <p v-if="loggedByLine(flight)" class="mt-2 text-xs text-[var(--muted)]">
          {{ loggedByLine(flight) }}
        </p>
      </div> 
        <button
          class="rounded-full bg-white/70 p-2 hover:bg-white/90"
          aria-label="Close"
          @click="$emit('close')"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
      <div class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Distance</p>
        <p class="mt-1 font-semibold">{{ formatDistance(flight.distance_km) }}</p>
      </div>
      <div class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Flight Time</p>
        <p class="mt-1 font-semibold">{{ formatTimestamp(flight.flight_time) }}</p>
      </div>
      <div v-if="flight.icao24" class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">ICAO24</p>
        <p class="mt-1 font-semibold font-mono">{{ flight.icao24.toUpperCase() }}</p>
      </div>
      <div v-if="flight.aircraft_registry?.registration" class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Registration</p>
        <p class="mt-1 font-semibold">{{ flight.aircraft_registry.registration }}</p>
      </div>
      <div v-if="flight.serial_number" class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Serial (MSN)</p>
        <p class="mt-1 font-semibold">{{ flight.serial_number }}</p>
      </div>
      <div v-if="flight.year_built" class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Year Built</p>
        <p class="mt-1 font-semibold">{{ flight.year_built }}</p>
      </div>
      <div v-if="flight.engines" class="rounded-2xl bg-white/70 p-3 col-span-2">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Engines</p>
        <p class="mt-1 font-semibold">{{ flight.engines }}</p>
      </div>
      <div v-if="formatAircraftCategory(flight)" class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Category</p>
        <p class="mt-1 font-semibold">{{ formatAircraftCategory(flight) }}</p>
      </div>
      <div v-if="flight.icao_aircraft_type" class="rounded-2xl bg-white/70 p-3">
        <p class="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">ICAO Type</p>
        <p class="mt-1 font-semibold font-mono">{{ flight.icao_aircraft_type }}</p>
      </div>
    </div>

    <template v-if="isEditing">
      <textarea
        v-model="editNote"
        class="mt-4 w-full rounded-3xl bg-white/70 p-4 text-sm text-[var(--ink)] resize-none focus:outline-none"
        rows="3"
        placeholder="Add a note…"
      />
      <div class="mt-2 flex gap-2">
        <button
          class="rounded-full bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          :disabled="isSaving"
          @click="saveEdit"
        >{{ isSaving ? "Saving…" : "Save" }}</button>
        <button
          class="rounded-full bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white/90"
          :disabled="isSaving"
          @click="cancelEdit"
        >Cancel</button>
      </div>
    </template>
    <p v-else class="mt-4 rounded-3xl bg-white/70 p-4 text-sm text-[var(--muted)]">{{ flight.note || "No note added." }}</p>

    <div v-if="flight.photos.length" class="mt-4 grid grid-cols-3 gap-3">
      <button
        v-for="(photo, index) in flight.photos"
        :key="photo.id"
        class="relative cursor-pointer overflow-hidden rounded-2xl"
        @click="openViewer(index)"
      >
        <video
          v-if="photo.media_type === 'video'"
          :src="photo.url"
          class="h-24 w-full object-cover"
          muted
          playsinline
        />
        <img v-else :src="photo.url" alt="" class="h-24 w-full object-cover" />
        <div
          v-if="photo.media_type === 'video'"
          class="absolute inset-0 flex items-center justify-center bg-black/20"
        >
          <svg class="h-8 w-8 text-white drop-shadow-lg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </button>
    </div>

    <template v-if="flight.is_owner && !isEditing">
      <div v-if="confirmingDelete" class="mt-4 rounded-2xl bg-red-50/80 p-3 text-sm">
        <p class="font-semibold text-red-700">Delete this log?</p>
        <p class="mt-1 text-red-600">This cannot be undone.</p>
        <div class="mt-3 flex gap-2">
          <button
            class="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            :disabled="isDeleting"
            @click="confirmDelete"
          >{{ isDeleting ? "Deleting…" : "Yes, delete" }}</button>
          <button
            class="rounded-full bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white/90"
            :disabled="isDeleting"
            @click="confirmingDelete = false"
          >Cancel</button>
        </div>
      </div>
      <div v-else class="mt-4 flex gap-2">
        <button
          class="rounded-full bg-white/70 px-4 py-2 text-sm font-semibold hover:bg-white/90"
          @click="startEdit"
        >Edit note</button>
        <button
          class="rounded-full bg-red-100/80 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-200/80"
          @click="confirmingDelete = true"
        >Delete</button>
      </div>
    </template>
  </aside>

  <MediaViewer
    v-if="flight"
    :media="flight.photos"
    :start-index="viewerStartIndex"
    :open="viewerOpen"
    @close="viewerOpen = false"
  />
</template>
