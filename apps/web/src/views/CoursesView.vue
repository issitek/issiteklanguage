<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, type Course, type Progress } from "../api";

const courses = ref<Course[]>([]);
const progress = ref<Progress | null>(null);
const loading = ref(true);
const error = ref("");

const statusByLesson = computed(() => {
  const map = new Map<string, string>();
  for (const item of progress.value?.items ?? []) map.set(item.lesson_id, item.status);
  return map;
});

function statusLabel(status: string | undefined) {
  if (status === "completed") return "Completada";
  if (status === "in_progress") return "En curso";
  return "Nueva";
}

function statusClass(status: string | undefined) {
  if (status === "completed") return "chip ok";
  if (status === "in_progress") return "chip warn";
  return "chip";
}

onMounted(async () => {
  try {
    const [courseList, progressData] = await Promise.all([api.courses(), api.progress()]);
    courses.value = courseList;
    progress.value = progressData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos cargar los cursos.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section>
    <h1>Tu curso de inglés</h1>
    <p class="lead">
      Diez lecciones A1 para empezar. Escucha, repite y avanza a tu ritmo.
    </p>

    <div v-if="progress" class="card" style="margin-bottom: 1.2rem">
      <div class="exercise-head">
        <strong>Progreso del curso</strong>
        <span class="chip">
          {{ progress.completed_lessons }} / {{ progress.total_lessons }} lecciones
        </span>
      </div>
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{
            width:
              (progress.total_lessons
                ? (progress.completed_lessons / progress.total_lessons) * 100
                : 0) + '%',
          }"
        ></div>
      </div>
      <p class="muted" style="margin: 0.6rem 0 0; font-size: 0.88rem">
        <template v-if="progress.pronunciation_eval_enabled">
          Evaluación fonética activa.
        </template>
        <template v-else>
          Práctica libre: escucha, graba y compara. La evaluación fonética está
          desactivada.
        </template>
      </p>
    </div>

    <p v-if="loading" class="muted">Cargando cursos…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else class="grid">
      <article v-for="course in courses" :key="course.id" class="card">
        <span class="chip">{{ course.level }}</span>
        <h2>{{ course.title }}</h2>
        <p class="muted">{{ course.description }}</p>

        <div class="lesson-list">
          <RouterLink
            v-for="lesson in course.lessons"
            :key="lesson.id"
            :to="{ name: 'lesson', params: { id: lesson.id } }"
            class="lesson-row"
          >
            <span>
              <strong>{{ lesson.position + 1 }}.</strong> {{ lesson.title }}
            </span>
            <span :class="statusClass(statusByLesson.get(lesson.id))">
              {{ statusLabel(statusByLesson.get(lesson.id)) }}
            </span>
          </RouterLink>
        </div>
      </article>
    </div>

    <p v-if="!loading && !error && courses.length === 0" class="muted">
      Todavía no hay cursos publicados.
    </p>
  </section>
</template>
