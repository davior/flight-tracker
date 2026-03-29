import { onBeforeUnmount } from "vue";

export function useDebouncedTask(delayMs: number) {
  let timeoutId: number | null = null;

  function schedule(task: () => void): void {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
    timeoutId = window.setTimeout(() => {
      timeoutId = null;
      task();
    }, delayMs);
  }

  onBeforeUnmount(() => {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  });

  return { schedule };
}
