<script setup lang="ts">
import { ref } from "vue";

import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
const resending = ref(false);
const resent = ref(false);
const error = ref("");

async function resend(): Promise<void> {
  error.value = "";
  resending.value = true;
  try {
    await authStore.resendVerification();
    resent.value = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to resend email";
  } finally {
    resending.value = false;
  }
}
</script>

<template>
  <div class="absolute inset-0 z-[2000] flex items-center justify-center p-4">
    <div class="glass-panel w-full max-w-sm rounded-[2rem] p-8 text-center">
      <!-- Icon -->
      <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--accent)]/15">
        <svg class="h-8 w-8 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
        </svg>
      </div>

      <h2 class="mb-2 text-lg font-bold">Check your email</h2>
      <p class="mb-1 text-sm text-[var(--muted)]">
        We sent a verification link to
      </p>
      <p class="mb-6 text-sm font-medium">{{ authStore.user?.email }}</p>
      <p class="mb-6 text-xs text-[var(--muted)]">
        Click the link in the email to verify your account and get started.
      </p>

      <p v-if="error" class="mb-4 rounded-xl bg-red-500/15 px-3 py-2 text-xs text-red-300">{{ error }}</p>

      <div v-if="resent" class="mb-4 rounded-xl bg-emerald-500/15 px-3 py-2 text-xs text-emerald-300">
        Verification email resent!
      </div>

      <button
        :disabled="resending || resent"
        class="mb-3 w-full rounded-xl bg-white/8 py-2.5 text-sm font-medium transition-colors hover:bg-white/12 disabled:opacity-50"
        @click="resend"
      >
        {{ resending ? "Sending…" : resent ? "Email sent" : "Resend verification email" }}
      </button>

      <button
        class="text-xs text-[var(--muted)] hover:text-white"
        @click="authStore.logout()"
      >
        Sign out
      </button>
    </div>
  </div>
</template>
