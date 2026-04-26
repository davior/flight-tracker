<script setup lang="ts">
import { ref } from "vue";

import { useAuthStore } from "@/stores/auth";

const props = defineProps<{ token: string }>();
const emit = defineEmits<{ done: [] }>();

const authStore = useAuthStore();
const newPassword = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const error = ref("");
const success = ref(false);

async function handleReset(): Promise<void> {
  error.value = "";
  if (!newPassword.value || !confirmPassword.value) {
    error.value = "Please fill in both fields.";
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = "Passwords do not match.";
    return;
  }
  if (newPassword.value.length < 8) {
    error.value = "Password must be at least 8 characters.";
    return;
  }
  loading.value = true;
  try {
    await authStore.resetPassword(props.token, newPassword.value);
    success.value = true;
    setTimeout(() => emit("done"), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Reset failed";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="absolute inset-0 z-[3000] flex items-center justify-center p-4">
    <div class="glass-panel w-full max-w-sm rounded-[2rem] p-8">
      <h2 class="mb-1 text-lg font-bold">Set new password</h2>
      <p class="mb-6 text-sm text-[var(--muted)]">Choose a strong password for your account.</p>

      <div v-if="success" class="rounded-xl bg-emerald-500/15 px-4 py-4 text-center text-sm text-emerald-300">
        Password updated! Signing you in…
      </div>

      <form v-else class="flex flex-col gap-3" @submit.prevent="handleReset">
        <p v-if="error" class="rounded-xl bg-red-500/15 px-4 py-2 text-sm text-red-300">{{ error }}</p>
        <input
          v-model="newPassword"
          type="password"
          placeholder="New password (min. 8 characters)"
          autocomplete="new-password"
          class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
        />
        <input
          v-model="confirmPassword"
          type="password"
          placeholder="Confirm new password"
          autocomplete="new-password"
          class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
        />
        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        >
          {{ loading ? "Updating…" : "Set Password" }}
        </button>
      </form>
    </div>
  </div>
</template>
