import { defineStore } from "pinia";
import { ref } from "vue";

import { loadOrCreateIdentity } from "@/lib/identity";

export const useIdentityStore = defineStore("identity", () => {
  const userUuid = ref<string>("");

  function ensureIdentity(): string {
    if (!userUuid.value) {
      userUuid.value = loadOrCreateIdentity();
    }
    return userUuid.value;
  }

  return {
    userUuid,
    ensureIdentity,
  };
});
