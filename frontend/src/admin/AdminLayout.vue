<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

const navItems = [
  { to: "/admin/dashboard", label: "Dashboard", icon: "⬛" },
  { to: "/admin/users", label: "Users", icon: "👥" },
  { to: "/admin/metrics", label: "Metrics", icon: "📊" },
  { to: "/admin/logs", label: "Logs", icon: "📋" },
  { to: "/admin/data-sync", label: "Data Sync", icon: "🔄" },
  { to: "/admin/ai", label: "AI Analysis", icon: "🤖" },
];

function logout() {
  auth.logout();
  router.push("/admin/login");
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
    <!-- Sidebar -->
    <aside class="flex w-56 flex-shrink-0 flex-col border-r border-slate-800 bg-slate-900">
      <div class="flex h-14 items-center gap-2 border-b border-slate-800 px-4">
        <span class="text-sm font-bold uppercase tracking-widest text-slate-400">Admin</span>
      </div>
      <nav class="flex-1 overflow-y-auto py-3">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100"
          active-class="bg-slate-800 text-slate-100"
        >
          <span class="w-5 text-center text-base leading-none">{{ item.icon }}</span>
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="border-t border-slate-800 p-4">
        <p class="truncate text-xs text-slate-500">{{ auth.user?.email }}</p>
        <button
          class="mt-2 w-full rounded-md bg-slate-800 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-slate-700"
          @click="logout"
        >
          Sign out
        </button>
      </div>
    </aside>

    <!-- Content -->
    <main class="flex flex-1 flex-col overflow-hidden">
      <RouterView />
    </main>
  </div>
</template>
