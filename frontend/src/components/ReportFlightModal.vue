<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { formatAircraftCategory, getAircraftCategoryDescription, getAircraftDisplayLabel } from "@/lib/aircraft";
import type { ApiLiveFlight } from "@/types/api";

const props = defineProps<{
  open: boolean;
  flight: ApiLiveFlight | null;
  submitting: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [{ note: string; files: File[] }];
  invalid: [message: string];
}>();

const note = ref("");
const files = ref<File[]>([]);
const previews = ref<string[]>([]);

function resetForm(): void {
  previews.value.forEach((url) => URL.revokeObjectURL(url));
  previews.value = [];
  files.value = [];
  note.value = "";
}

function syncPreviews(): void {
  previews.value.forEach((url) => URL.revokeObjectURL(url));
  previews.value = files.value.map((file) => URL.createObjectURL(file));
}

function appendFiles(fileList: FileList | null): void {
  if (!fileList) {
    return;
  }
  const nextFiles = [...files.value, ...Array.from(fileList)].slice(0, 3);
  if (nextFiles.length < files.value.length + fileList.length) {
    emit("invalid", "You can upload a maximum of 3 files.");
  }
  files.value = nextFiles;
  syncPreviews();
}

function removeFile(index: number): void {
  files.value.splice(index, 1);
  syncPreviews();
}

function submit(): void {
  emit("submit", { note: note.value, files: files.value });
}

const title = computed(() => props.flight?.callsign || props.flight?.icao24.toUpperCase() || "Report flight");

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      resetForm();
    }
  },
);

onBeforeUnmount(() => {
  resetForm();
});
</script>

<template>
  <div
    v-if="open && flight"
    class="absolute inset-0 z-[1000] flex items-end bg-slate-950/40 p-3 md:items-center md:justify-center"
  >
    <div class="glass-panel w-full rounded-[2rem] p-5 md:max-w-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Report flight</p>
          <h2 class="text-xl font-bold">{{ title }}</h2>
          <p class="text-sm text-[var(--muted)]">{{ getAircraftDisplayLabel(flight) || "Aircraft type unavailable" }}</p>
          <p v-if="formatAircraftCategory(flight)" class="mt-1 text-xs text-[var(--muted)]">
            Category: {{ formatAircraftCategory(flight) }}
          </p>
          <p v-if="getAircraftCategoryDescription(flight)" class="mt-1 text-xs text-[var(--muted)]">
            {{ getAircraftCategoryDescription(flight) }}
          </p>
        </div>
        <button class="rounded-full bg-white/70 p-2 text-sm font-semibold hover:bg-white/90" @click="$emit('close')" aria-label="Close">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <label class="mt-4 block text-sm font-semibold">Comment</label>
      <textarea
        v-model="note"
        rows="4"
        class="mt-2 w-full rounded-3xl border border-[var(--border)] bg-white/70 px-4 py-3 text-sm outline-none"
        placeholder="What made this sighting worth logging?"
      />

      <div class="mt-4 flex flex-col gap-3 md:flex-row">
        <label class="flex-1 cursor-pointer rounded-3xl border border-dashed border-[var(--border)] bg-white/70 px-4 py-4 text-center text-sm font-semibold">
          Take photo
          <input class="hidden" type="file" accept="image/*" capture="environment" @change="appendFiles(($event.target as HTMLInputElement).files)" />
        </label>
        <label class="flex-1 cursor-pointer rounded-3xl border border-dashed border-[var(--border)] bg-white/70 px-4 py-4 text-center text-sm font-semibold">
          Upload photos / video
          <input class="hidden" type="file" accept="image/png,image/jpeg,video/mp4,video/quicktime,video/webm" multiple @change="appendFiles(($event.target as HTMLInputElement).files)" />
        </label>
      </div>

      <div v-if="previews.length" class="mt-4 grid grid-cols-3 gap-3">
        <div v-for="(preview, index) in previews" :key="preview" class="relative">
          <video
            v-if="files[index]?.type.startsWith('video/')"
            :src="preview"
            class="h-24 w-full rounded-2xl object-cover"
            muted
            playsinline
          />
          <img v-else :src="preview" alt="" class="h-24 w-full rounded-2xl object-cover" />
          <div
            v-if="files[index]?.type.startsWith('video/')"
            class="absolute inset-0 flex items-center justify-center pointer-events-none"
          >
            <svg class="h-8 w-8 text-white drop-shadow-lg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <button
            class="absolute right-2 top-2 rounded-full bg-slate-950/70 px-2 py-1 text-xs font-semibold text-white"
            @click="removeFile(index)"
          >
            Remove
          </button>
        </div>
      </div>

      <button
        class="mt-5 w-full rounded-2xl bg-[var(--accent)] px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="submitting"
        @click="submit"
      >
        {{ submitting ? "Submitting..." : "Submit report" }}
      </button>
    </div>
  </div>
</template>
