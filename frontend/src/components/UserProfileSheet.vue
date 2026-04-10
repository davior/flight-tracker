<script setup lang="ts">
import { ref, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const authStore = useAuthStore();
const uiStore = useUiStore();

const username = ref("");
const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const isSaving = ref(false);
const activeTab = ref<"profile" | "password">("profile");

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      username.value = authStore.user?.username ?? "";
      currentPassword.value = "";
      newPassword.value = "";
      confirmPassword.value = "";
      activeTab.value = "profile";
    }
  },
);

async function saveProfile() {
  const payload: Record<string, string> = {};
  const trimmedUsername = username.value.trim();

  if (activeTab.value === "profile") {
    if (trimmedUsername && trimmedUsername !== authStore.user?.username) {
      if (trimmedUsername.length < 3) {
        uiStore.showToast("Username must be at least 3 characters.");
        return;
      }
      payload.username = trimmedUsername;
    }
  } else {
    if (!currentPassword.value) {
      uiStore.showToast("Please enter your current password.");
      return;
    }
    if (newPassword.value.length < 8) {
      uiStore.showToast("New password must be at least 8 characters.");
      return;
    }
    if (newPassword.value !== confirmPassword.value) {
      uiStore.showToast("Passwords do not match.");
      return;
    }
    payload.current_password = currentPassword.value;
    payload.new_password = newPassword.value;
  }

  if (Object.keys(payload).length === 0) {
    emit("close");
    return;
  }

  isSaving.value = true;
  try {
    await authStore.updateProfile(payload);
    uiStore.showToast("Profile updated.");
    emit("close");
  } catch (error) {
    uiStore.showToast(error instanceof Error ? error.message : "Failed to update profile.");
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <div
    v-if="open"
    class="absolute inset-0 z-[1000] flex items-end bg-slate-950/40 p-3 md:items-center md:justify-center"
  >
    <div class="glass-panel w-full rounded-[2rem] p-5 md:max-w-sm">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-bold">Account settings</h2>
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

      <p class="mt-1 text-sm text-[var(--muted)]">{{ authStore.user?.email }}</p>

      <!-- Tab switcher -->
      <div class="mt-4 flex gap-2 rounded-2xl bg-white/50 p-1 text-sm font-semibold">
        <button
          class="flex-1 rounded-xl py-2 transition-colors"
          :class="activeTab === 'profile' ? 'bg-white shadow-sm text-[var(--ink)]' : 'text-[var(--muted)]'"
          @click="activeTab = 'profile'"
        >Username</button>
        <button
          class="flex-1 rounded-xl py-2 transition-colors"
          :class="activeTab === 'password' ? 'bg-white shadow-sm text-[var(--ink)]' : 'text-[var(--muted)]'"
          @click="activeTab = 'password'"
        >Password</button>
      </div>

      <!-- Username tab -->
      <div v-if="activeTab === 'profile'" class="mt-4 flex flex-col gap-3">
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Username</label>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            class="mt-1 w-full rounded-2xl bg-white/70 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40"
          />
        </div>
      </div>

      <!-- Password tab -->
      <div v-else class="mt-4 flex flex-col gap-3">
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Current password</label>
          <input
            v-model="currentPassword"
            type="password"
            autocomplete="current-password"
            class="mt-1 w-full rounded-2xl bg-white/70 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40"
          />
        </div>
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">New password</label>
          <input
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            class="mt-1 w-full rounded-2xl bg-white/70 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40"
          />
        </div>
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Confirm new password</label>
          <input
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            class="mt-1 w-full rounded-2xl bg-white/70 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40"
          />
        </div>
      </div>

      <div class="mt-5 flex gap-2">
        <button
          class="flex-1 rounded-full bg-[var(--accent)] py-3 text-sm font-semibold text-white disabled:opacity-50"
          :disabled="isSaving"
          @click="saveProfile"
        >{{ isSaving ? "Saving…" : "Save" }}</button>
        <button
          class="rounded-full bg-white/70 px-5 py-3 text-sm font-semibold hover:bg-white/90"
          :disabled="isSaving"
          @click="$emit('close')"
        >Cancel</button>
      </div>

      <div class="mt-4 border-t border-[var(--border)] pt-4">
        <button
          class="w-full rounded-full bg-white/70 py-3 text-sm font-semibold text-[var(--muted)] hover:bg-white/90"
          @click="authStore.logout(); $emit('close')"
        >Sign out</button>
      </div>
    </div>
  </div>
</template>
