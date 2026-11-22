<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "./stores/auth";

const auth = useAuth();
const router = useRouter();

onMounted(() => {
  void auth.bootstrap();
});

async function signOut() {
  await auth.logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <RouterLink to="/" class="brand">
        <span class="brand-mark">IL</span>
        <span>Issitek <strong>Language</strong></span>
      </RouterLink>
      <nav v-if="auth.user" class="nav">
        <RouterLink to="/">Cursos</RouterLink>
        <RouterLink to="/progress">Progreso</RouterLink>
        <span class="who">{{ auth.user.display_name }}</span>
        <button class="ghost" type="button" @click="signOut">Salir</button>
      </nav>
    </header>

    <main class="content">
      <RouterView />
    </main>

    <footer class="footer">
      <span>talkdrill.com</span>
      <span>Práctica libre · La evaluación fonética está desactivada</span>
    </footer>
  </div>
</template>
