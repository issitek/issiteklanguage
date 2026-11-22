import { createRouter, createWebHistory } from "vue-router";
import { hasToken } from "./api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("./views/LoginView.vue"),
      meta: { public: true },
    },
    {
      path: "/",
      name: "courses",
      component: () => import("./views/CoursesView.vue"),
    },
    {
      path: "/lessons/:id",
      name: "lesson",
      component: () => import("./views/LessonView.vue"),
    },
    {
      path: "/progress",
      name: "progress",
      component: () => import("./views/ProgressView.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  const authed = hasToken();
  if (!to.meta.public && !authed) return { name: "login" };
  if (to.name === "login" && authed) return { name: "courses" };
  return true;
});

export default router;
