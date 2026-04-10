import { defineStore } from "pinia";
import { computed } from "vue";

import { useAuthStore } from "@/stores/auth";

// This store now delegates to the auth store.
// It remains for backwards-compatibility with any code that still calls ensureIdentity().
export const useIdentityStore = defineStore("identity", () => {
  const authStore = useAuthStore();

  const userUuid = computed(() => (authStore.user ? String(authStore.user.id) : ""));

  function ensureIdentity(): string {
    return userUuid.value;
  }

  return {
    userUuid,
    ensureIdentity,
  };
});
