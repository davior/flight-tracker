<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import type { ApiPhoto } from "@/types/api";

const props = defineProps<{
  media: ApiPhoto[];
  startIndex: number;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const currentIndex = ref(props.startIndex);

const current = computed(() => props.media[currentIndex.value]);

function prev() {
  if (currentIndex.value > 0) {
    currentIndex.value--;
  }
}

function next() {
  if (currentIndex.value < props.media.length - 1) {
    currentIndex.value++;
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape") emit("close");
  else if (e.key === "ArrowLeft") prev();
  else if (e.key === "ArrowRight") next();
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      currentIndex.value = props.startIndex;
      window.addEventListener("keydown", onKeyDown);
    } else {
      window.removeEventListener("keydown", onKeyDown);
    }
  },
);

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && current"
      class="fixed inset-0 z-[2000] flex flex-col bg-black/95"
      @click.self="$emit('close')"
    >
      <!-- Top bar -->
      <div class="flex shrink-0 items-center justify-between px-4 py-3">
        <span class="text-sm text-white/60">{{ currentIndex + 1 }} / {{ media.length }}</span>
        <button
          class="rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          aria-label="Close"
          @click="$emit('close')"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <!-- Media area -->
      <div class="relative flex min-h-0 flex-1 items-center justify-center px-14">
        <img
          v-if="current.media_type === 'image'"
          :src="current.url"
          alt=""
          class="max-h-full max-w-full object-contain"
          @click.stop
        />
        <video
          v-else
          :src="current.url"
          controls
          class="max-h-full max-w-full"
          @click.stop
        />

        <!-- Prev button -->
        <button
          v-if="currentIndex > 0"
          class="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
          aria-label="Previous"
          @click.stop="prev"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>

        <!-- Next button -->
        <button
          v-if="currentIndex < media.length - 1"
          class="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-3 text-white hover:bg-white/20"
          aria-label="Next"
          @click.stop="next"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>

      <!-- Bottom padding -->
      <div class="shrink-0 py-3" />
    </div>
  </Teleport>
</template>
