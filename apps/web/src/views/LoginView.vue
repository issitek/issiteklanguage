<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../stores/auth";

const auth = useAuth();
const router = useRouter();

const mode = ref<"login" | "register">("login");
const email = ref("");
const password = ref("");
const displayName = ref("");
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    if (mode.value === "login") {
      await auth.login(email.value.trim(), password.value);
    } else {
      await auth.register(email.value.trim(), password.value, displayName.value.trim());
    }
    await router.push({ name: "courses" });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos iniciar sesión.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="auth-wrap">
    <div class="card auth-card">
      <span class="chip">Issitek Language · A1</span>
      <h1>{{ mode === "login" ? "Bienvenido de vuelta" : "Crea tu cuenta" }}</h1>
      <p class="lead">
        Aprende inglés con lecciones cortas y práctica de voz. En esta fase la
        evaluación fonética está desactivada.
      </p>

      <form @submit.prevent="submit">
        <div v-if="mode === 'register'" class="field">
          <label for="name">Nombre</label>
          <input id="name" v-model="displayName" class="input" autocomplete="name" required />
        </div>

        <div class="field">
          <label for="email">Correo</label>
          <input
            id="email"
            v-model="email"
            class="input"
            type="email"
            autocomplete="email"
            required
          />
        </div>

        <div class="field">
          <label for="password">Contraseña</label>
          <input
            id="password"
            v-model="password"
            class="input"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            minlength="8"
            required
          />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="btn btn-primary" type="submit" :disabled="loading" style="width: 100%">
          {{ loading ? "Entrando…" : mode === "login" ? "Entrar" : "Crear cuenta" }}
        </button>
      </form>

      <p class="switch">
        {{ mode === "login" ? "¿No tienes cuenta?" : "¿Ya tienes cuenta?" }}
        <a
          href="#"
          @click.prevent="
            mode = mode === 'login' ? 'register' : 'login';
            error = '';
          "
        >
          {{ mode === "login" ? "Regístrate" : "Inicia sesión" }}
        </a>
      </p>
    </div>
  </section>
</template>
