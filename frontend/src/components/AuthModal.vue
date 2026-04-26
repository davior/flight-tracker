<script setup lang="ts">
import { ref } from "vue";

import { useAuthStore } from "@/stores/auth";

type Tab = "login" | "register" | "forgot";

const authStore = useAuthStore();

const activeTab = ref<Tab>("login");
const loginValue = ref("");
const loginPassword = ref("");
const registerEmail = ref("");
const registerUsername = ref("");
const registerPassword = ref("");
const registerConfirm = ref("");
const forgotEmail = ref("");

const loading = ref(false);
const error = ref("");
const registerSuccess = ref(false);
const forgotSuccess = ref(false);

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

function switchTab(tab: Tab): void {
  activeTab.value = tab;
  error.value = "";
  registerSuccess.value = false;
  forgotSuccess.value = false;
}

async function handleLogin(): Promise<void> {
  error.value = "";
  if (!loginValue.value || !loginPassword.value) {
    error.value = "Please enter your email/username and password.";
    return;
  }
  loading.value = true;
  try {
    await authStore.login(loginValue.value, loginPassword.value);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Login failed";
  } finally {
    loading.value = false;
  }
}

async function handleRegister(): Promise<void> {
  error.value = "";
  if (!registerEmail.value || !registerUsername.value || !registerPassword.value) {
    error.value = "Please fill in all fields.";
    return;
  }
  if (registerPassword.value !== registerConfirm.value) {
    error.value = "Passwords do not match.";
    return;
  }
  if (registerPassword.value.length < 8) {
    error.value = "Password must be at least 8 characters.";
    return;
  }
  loading.value = true;
  try {
    await authStore.register(registerEmail.value, registerUsername.value, registerPassword.value);
    registerSuccess.value = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Registration failed";
  } finally {
    loading.value = false;
  }
}

async function handleForgot(): Promise<void> {
  error.value = "";
  if (!forgotEmail.value) {
    error.value = "Please enter your email address.";
    return;
  }
  loading.value = true;
  try {
    await authStore.forgotPassword(forgotEmail.value);
    forgotSuccess.value = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Request failed";
  } finally {
    loading.value = false;
  }
}

function initGoogle(): void {
  if (!googleClientId || !window.google) return;
  window.google.accounts.id.initialize({
    client_id: googleClientId,
    callback: async (response: { credential: string }) => {
      error.value = "";
      loading.value = true;
      try {
        await authStore.loginWithGoogle(response.credential);
      } catch (e) {
        error.value = e instanceof Error ? e.message : "Google sign-in failed";
      } finally {
        loading.value = false;
      }
    },
  });
  window.google.accounts.id.prompt();
}
</script>

<template>
  <div class="absolute inset-0 z-[2000] flex items-end p-3 md:items-center md:justify-center">
    <div class="glass-panel w-full rounded-[2rem] p-6 md:max-w-md">
      <!-- Header -->
      <div class="mb-6 text-center">
        <div class="mb-2 flex items-center justify-center gap-2">
          <svg class="h-7 w-7 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
          <span class="text-xl font-bold tracking-tight">Chemtrail Tracker</span>
        </div>
        <p class="text-sm">Log chemtrails live (or up to one hour in the past) from anywhere</p>
      </div>

      <!-- Tabs (login/register) -->
      <div v-if="activeTab !== 'forgot'" class="mb-5 flex rounded-xl bg-white/5 p-1">
        <button
          class="flex-1 rounded-lg py-2 text-sm font-medium transition-colors"
          :class="activeTab === 'login' ? 'bg-white/10 text-white' : 'text-[var(--muted)] hover:text-white'"
          @click="switchTab('login')"
        >
          Log In
        </button>
        <button
          class="flex-1 rounded-lg py-2 text-sm font-medium transition-colors"
          :class="activeTab === 'register' ? 'bg-white/10 text-white' : 'text-[var(--muted)] hover:text-white'"
          @click="switchTab('register')"
        >
          Register
        </button>
      </div>

      <!-- Error -->
      <p v-if="error" class="mb-4 rounded-xl bg-red-500/15 px-4 py-2 text-sm text-red-300">{{ error }}</p>

      <!-- Login form -->
      <form v-if="activeTab === 'login'" class="flex flex-col gap-3" @submit.prevent="handleLogin">
        <input
          v-model="loginValue"
          type="text"
          placeholder="Email or username"
          autocomplete="username"
          class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          name="username"
        />
        <input
          v-model="loginPassword"
          type="password"
          placeholder="Password"
          autocomplete="current-password"
          class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          name="password"
        />
        <div class="text-right">
          <button type="button" class="text-xs text-[var(--muted)] hover:text-white" @click="switchTab('forgot')">
            Forgot password?
          </button>
        </div>
        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        >
          {{ loading ? "Signing in…" : "Log In" }}
        </button>
        <div v-if="googleClientId" class="mt-1">
          <div class="mb-3 flex items-center gap-3">
            <div class="h-px flex-1 bg-white/10"></div>
            <span class="text-xs text-[var(--muted)]">or</span>
            <div class="h-px flex-1 bg-white/10"></div>
          </div>
          <button
            type="button"
            :disabled="loading"
            class="flex w-full items-center justify-center gap-3 rounded-xl bg-white/8 py-3 text-sm font-medium transition-colors hover:bg-white/12 disabled:opacity-50"
            @click="initGoogle"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
        </div>
      </form>

      <!-- Register form -->
      <div v-else-if="activeTab === 'register'">
        <div v-if="registerSuccess" class="rounded-xl bg-emerald-500/15 px-4 py-4 text-sm text-emerald-300">
          <p class="font-semibold">Registration successful!</p>
          <p class="mt-1">Check your email for a verification link. You'll need to verify before logging in.</p>
        </div>
        <form v-else class="flex flex-col gap-3" @submit.prevent="handleRegister">
          <input
            v-model="registerEmail"
            type="email"
            placeholder="Email address"
            autocomplete="email"
            class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          />
          <input
            v-model="registerUsername"
            type="text"
            placeholder="Username (min. 3 characters)"
            autocomplete="username"
            class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          />
          <input
            v-model="registerPassword"
            type="password"
            placeholder="Password (min. 8 characters)"
            autocomplete="new-password"
            class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          />
          <input
            v-model="registerConfirm"
            type="password"
            placeholder="Confirm password"
            autocomplete="new-password"
            class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          />
          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
          >
            {{ loading ? "Creating account…" : "Create Account" }}
          </button>
          <div v-if="googleClientId" class="mt-1">
            <div class="mb-3 flex items-center gap-3">
              <div class="h-px flex-1 bg-white/10"></div>
              <span class="text-xs text-[var(--muted)]">or</span>
              <div class="h-px flex-1 bg-white/10"></div>
            </div>
            <button
              type="button"
              :disabled="loading"
              class="flex w-full items-center justify-center gap-3 rounded-xl bg-white/8 py-3 text-sm font-medium transition-colors hover:bg-white/12 disabled:opacity-50"
              @click="initGoogle"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign up with Google
            </button>
          </div>
        </form>
      </div>

      <!-- Forgot password form -->
      <div v-else-if="activeTab === 'forgot'">
        <button
          class="mb-4 flex items-center gap-1 text-xs text-[var(--muted)] hover:text-white"
          @click="switchTab('login')"
        >
          <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to login
        </button>
        <p class="mb-4 text-sm font-semibold">Reset your password</p>
        <div v-if="forgotSuccess" class="rounded-xl bg-emerald-500/15 px-4 py-4 text-sm text-emerald-300">
          If that email is registered, you'll receive a reset link shortly.
        </div>
        <form v-else class="flex flex-col gap-3" @submit.prevent="handleForgot">
          <input
            v-model="forgotEmail"
            type="email"
            placeholder="Email address"
            autocomplete="email"
            class="w-full rounded-xl bg-white/8 px-4 py-3 text-sm placeholder-[var(--muted)] outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
          />
          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
          >
            {{ loading ? "Sending…" : "Send Reset Link" }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
