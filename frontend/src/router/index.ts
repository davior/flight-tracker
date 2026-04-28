import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: () => import("@/AppShell.vue"),
    },
    {
      path: "/admin/login",
      component: () => import("@/admin/views/AdminLoginView.vue"),
      meta: { adminPublic: true },
    },
    {
      path: "/admin",
      component: () => import("@/admin/AdminLayout.vue"),
      meta: { requiresAdmin: true },
      children: [
        { path: "", redirect: "/admin/dashboard" },
        { path: "dashboard", component: () => import("@/admin/views/DashboardView.vue") },
        { path: "users", component: () => import("@/admin/views/UsersView.vue") },
        { path: "metrics", component: () => import("@/admin/views/MetricsView.vue") },
        { path: "logs", component: () => import("@/admin/views/LogsView.vue") },
        { path: "data-sync", component: () => import("@/admin/views/DataSyncView.vue") },
        { path: "ai", component: () => import("@/admin/views/AiAnalysisView.vue") },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();

  // Admin subdomain: treat all paths as under /admin
  if (typeof window !== "undefined" && window.location.hostname.startsWith("admin.")) {
    const adminPath = "/admin" + (to.path === "/" ? "/dashboard" : to.path);
    if (!to.path.startsWith("/admin")) {
      return adminPath;
    }
  }

  if (to.meta.requiresAdmin) {
    if (!auth.isAuthenticated) return "/admin/login";
    if (!auth.user?.is_admin) return "/admin/login";
  }
});

export { router };
