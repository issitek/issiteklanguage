<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, type Progress } from "../api";

const progress = ref<Progress | null>(null);
const loading = ref(true);
const error = ref("");

const percent = computed(() => {
  if (!progress.value || progress.value.total_lessons === 0) return 0;
  return Math.round(
    (progress.value.completed_lessons / progress.value.total_lessons) * 100,
  );
});

function statusLabel(status: string) {
  if (status === "completed") return "Completada";
  if (status === "in_progress") return "En curso";
  return "Nueva";
}

function statusClass(status: string) {
  if (status === "completed") return "chip ok";
  if (status === "in_progress") return "chip warn";
  return "chip";
}

onMounted(async () => {
  try {
    progress.value = await api.progress();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos cargar tu progreso.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section>
    <h1>Tu progreso</h1>
    <p class="lead">Constancia corta y frecuente: diez minutos al día avanzan más que una hora el domingo.</p>

    <p v-if="loading" class="muted">Cargando progreso…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else-if="progress">
      <div class="stats">
        <div class="stat">
          <span class="muted">Lecciones completadas</span>
          <strong>{{ progress.completed_lessons }} / {{ progress.total_lessons }}</strong>
        </div>
        <div class="stat">
          <span class="muted">Intentos registrados</span>
          <strong>{{ progress.attempts }}</strong>
        </div>
        <div class="stat">
          <span class="muted">Avance</span>
          <strong>{{ percent }}%</strong>
        </div>
      </div>

      <div class="card" style="margin-bottom: 1.2rem">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: percent + '%' }"></div>
        </div>
        <p class="muted" style="margin: 0.7rem 0 0; font-size: 0.88rem">
          <template v-if="progress.pronunciation_eval_enabled">
            Evaluación fonética activa.
          </template>
          <template v-else>
            La evaluación fonética está desactivada. Tu práctica de voz se guarda
            como intento, sin puntaje, hasta que el motor supere la validación.
          </template>
        </p>
      </div>

      <article class="card">
        <h2>Lecciones</h2>
        <div class="lesson-list">
          <RouterLink
            v-for="item in progress.items"
            :key="item.lesson_id"
            :to="{ name: 'lesson', params: { id: item.lesson_id } }"
            class="lesson-row"
          >
            <span>
              <strong>{{ item.lesson_title }}</strong>
              <span class="muted" style="font-size: 0.82rem; display: block">
                {{ item.attempts }} intento{{ item.attempts === 1 ? "" : "s" }}
                <template v-if="item.score !== null"> · mejor puntaje {{ item.score }}</template>
              </span>
            </span>
            <span :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
          </RouterLink>
        </div>
      </article>
    </template>
  </section>
</template>
