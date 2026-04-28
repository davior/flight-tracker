<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  setUserPassword,
  sendPasswordReset,
  type AdminUser,
} from "@/admin/api";

const users = ref<AdminUser[]>([]);
const total = ref(0);
const page = ref(1);
const search = ref("");
const loading = ref(false);
const error = ref("");
const toast = ref("");

// Add/edit modal
const modal = ref<"create" | "edit" | "password" | null>(null);
const selected = ref<AdminUser | null>(null);

const form = ref({ email: "", username: "", password: "", is_admin: false });
const newPassword = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await getUsers(page.value, search.value);
    users.value = res.items;
    total.value = res.total;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load users";
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function showToast(msg: string) {
  toast.value = msg;
  setTimeout(() => (toast.value = ""), 3000);
}

function openCreate() {
  form.value = { email: "", username: "", password: "", is_admin: false };
  modal.value = "create";
}

function openEdit(user: AdminUser) {
  selected.value = user;
  form.value = { email: user.email, username: user.username, password: "", is_admin: user.is_admin };
  modal.value = "edit";
}

function openPassword(user: AdminUser) {
  selected.value = user;
  newPassword.value = "";
  modal.value = "password";
}

async function submitCreate() {
  try {
    await createUser({ email: form.value.email, username: form.value.username, password: form.value.password, is_admin: form.value.is_admin });
    modal.value = null;
    showToast("User created");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Create failed";
  }
}

async function submitEdit() {
  if (!selected.value) return;
  try {
    await updateUser(selected.value.id, { email: form.value.email, username: form.value.username, is_admin: form.value.is_admin });
    modal.value = null;
    showToast("User updated");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Update failed";
  }
}

async function submitPassword() {
  if (!selected.value) return;
  try {
    await setUserPassword(selected.value.id, newPassword.value);
    modal.value = null;
    showToast("Password updated");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function toggleActive(user: AdminUser) {
  try {
    await updateUser(user.id, { is_active: !user.is_active });
    showToast(user.is_active ? "Account disabled" : "Account enabled");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function confirmDelete(user: AdminUser) {
  if (!confirm(`Delete user ${user.email}? This cannot be undone.`)) return;
  try {
    await deleteUser(user.id);
    showToast("User deleted");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Delete failed";
  }
}

async function triggerReset(user: AdminUser) {
  try {
    const res = await sendPasswordReset(user.id);
    showToast(res.message);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

function handleSearch() {
  page.value = 1;
  load();
}
</script>

<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-slate-800 px-6 py-4">
      <h2 class="text-lg font-semibold text-slate-100">Users</h2>
      <button
        class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500"
        @click="openCreate"
      >
        + Add User
      </button>
    </div>

    <!-- Search -->
    <div class="flex items-center gap-3 border-b border-slate-800 px-6 py-3">
      <input
        v-model="search"
        type="text"
        placeholder="Search by email or username…"
        class="w-72 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-blue-500"
        @keydown.enter="handleSearch"
      />
      <button class="text-xs text-slate-400 hover:text-slate-200" @click="handleSearch">Search</button>
    </div>

    <p v-if="error" class="mx-6 mt-3 text-xs text-red-400">{{ error }}</p>

    <!-- Table -->
    <div class="flex-1 overflow-y-auto">
      <table class="w-full text-sm">
        <thead class="sticky top-0 bg-slate-900">
          <tr class="border-b border-slate-800 text-left text-xs font-medium text-slate-500">
            <th class="px-4 py-3">ID</th>
            <th class="px-4 py-3">Email</th>
            <th class="px-4 py-3">Username</th>
            <th class="px-4 py-3">Verified</th>
            <th class="px-4 py-3">Admin</th>
            <th class="px-4 py-3">Active</th>
            <th class="px-4 py-3">Logs</th>
            <th class="px-4 py-3">Joined</th>
            <th class="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="user in users"
            :key="user.id"
            class="border-b border-slate-800/50 text-slate-300 hover:bg-slate-800/30"
          >
            <td class="px-4 py-2.5 text-slate-500">{{ user.id }}</td>
            <td class="px-4 py-2.5">{{ user.email }}</td>
            <td class="px-4 py-2.5">{{ user.username }}</td>
            <td class="px-4 py-2.5">
              <span :class="user.is_verified ? 'text-green-400' : 'text-slate-500'">
                {{ user.is_verified ? "✓" : "✗" }}
              </span>
            </td>
            <td class="px-4 py-2.5">
              <span :class="user.is_admin ? 'text-purple-400' : 'text-slate-500'">
                {{ user.is_admin ? "Admin" : "—" }}
              </span>
            </td>
            <td class="px-4 py-2.5">
              <span :class="user.is_active ? 'text-green-400' : 'text-red-400'">
                {{ user.is_active ? "Active" : "Disabled" }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-slate-400">{{ user.flight_log_count }}</td>
            <td class="px-4 py-2.5 text-slate-500 text-xs">{{ new Date(user.created_at).toLocaleDateString() }}</td>
            <td class="px-4 py-2.5">
              <div class="flex items-center gap-2">
                <button class="text-xs text-blue-400 hover:text-blue-300" @click="openEdit(user)">Edit</button>
                <button class="text-xs text-yellow-400 hover:text-yellow-300" @click="openPassword(user)">Password</button>
                <button class="text-xs text-slate-400 hover:text-slate-200" @click="triggerReset(user)">Reset Email</button>
                <button
                  class="text-xs hover:underline"
                  :class="user.is_active ? 'text-orange-400 hover:text-orange-300' : 'text-green-400 hover:text-green-300'"
                  @click="toggleActive(user)"
                >
                  {{ user.is_active ? "Disable" : "Enable" }}
                </button>
                <button class="text-xs text-red-400 hover:text-red-300" @click="confirmDelete(user)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="loading" class="py-6 text-center text-sm text-slate-500">Loading…</div>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-between border-t border-slate-800 px-6 py-3 text-xs text-slate-500">
      <span>{{ total }} total users</span>
      <div class="flex gap-2">
        <button :disabled="page <= 1" class="disabled:opacity-30 hover:text-slate-200" @click="page--; load()">← Prev</button>
        <span>Page {{ page }}</span>
        <button :disabled="users.length < 50" class="disabled:opacity-30 hover:text-slate-200" @click="page++; load()">Next →</button>
      </div>
    </div>

    <!-- Toast -->
    <div
      v-if="toast"
      class="fixed bottom-6 right-6 rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-100 shadow-xl"
    >
      {{ toast }}
    </div>

    <!-- Modal backdrop -->
    <div v-if="modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <!-- Create User -->
      <div v-if="modal === 'create'" class="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <h3 class="mb-4 text-base font-semibold text-slate-100">Add User</h3>
        <div class="space-y-3">
          <input v-model="form.email" type="email" placeholder="Email" class="admin-input" />
          <input v-model="form.username" type="text" placeholder="Username" class="admin-input" />
          <input v-model="form.password" type="password" placeholder="Password (min 8 chars)" class="admin-input" />
          <label class="flex items-center gap-2 text-sm text-slate-300">
            <input v-model="form.is_admin" type="checkbox" class="rounded" />
            Grant admin access
          </label>
        </div>
        <div class="mt-4 flex justify-end gap-2">
          <button class="admin-btn-secondary" @click="modal = null">Cancel</button>
          <button class="admin-btn-primary" @click="submitCreate">Create</button>
        </div>
      </div>

      <!-- Edit User -->
      <div v-else-if="modal === 'edit'" class="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <h3 class="mb-4 text-base font-semibold text-slate-100">Edit User</h3>
        <div class="space-y-3">
          <input v-model="form.email" type="email" placeholder="Email" class="admin-input" />
          <input v-model="form.username" type="text" placeholder="Username" class="admin-input" />
          <label class="flex items-center gap-2 text-sm text-slate-300">
            <input v-model="form.is_admin" type="checkbox" class="rounded" />
            Admin access
          </label>
        </div>
        <div class="mt-4 flex justify-end gap-2">
          <button class="admin-btn-secondary" @click="modal = null">Cancel</button>
          <button class="admin-btn-primary" @click="submitEdit">Save</button>
        </div>
      </div>

      <!-- Set Password -->
      <div v-else-if="modal === 'password'" class="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <h3 class="mb-4 text-base font-semibold text-slate-100">Set Password</h3>
        <input v-model="newPassword" type="password" placeholder="New password (min 8 chars)" class="admin-input" />
        <div class="mt-4 flex justify-end gap-2">
          <button class="admin-btn-secondary" @click="modal = null">Cancel</button>
          <button class="admin-btn-primary" @click="submitPassword">Set Password</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@reference "tailwindcss";

.admin-input {
  @apply w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500;
}
.admin-btn-primary {
  @apply rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-500;
}
.admin-btn-secondary {
  @apply rounded-lg bg-slate-800 px-4 py-1.5 text-sm text-slate-300 hover:bg-slate-700;
}
</style>
