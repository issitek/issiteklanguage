<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, type AttemptResult, type Exercise, type Lesson } from "../api";
import Recorder from "../components/Recorder.vue";

const route = useRoute();
const router = useRouter();

const lesson = ref<Lesson | null>(null);
const loading = ref(true);
const error = ref("");
const attempts = ref<Record<string, AttemptResult>>({});
const feedback = ref<Record<string, string>>({});
const answers = ref<Record<string, string>>({});
const submitting = ref<Record<string, boolean>>({});
const completing = ref(false);
const lessonCompleted = ref(false);

const allAttempted = computed(() =>
  Boolean(lesson.value?.exercises.length) &&
  (lesson.value?.exercises ?? []).every((exercise) => attempts.value[exercise.id]),
);
const completed = computed(() => lessonCompleted.value);

function isChoice(exercise: Exercise) {
  return exercise.type === "multiple_choice";
}
function isText(exercise: Exercise) {
  return ["translate", "fill_blank", "short_answer"].includes(exercise.type);
}
function isRepeat(exercise: Exercise) {
  return exercise.type === "listen_repeat";
}
function options(exercise: Exercise): string[] {
  const value = exercise.payload.options;
  return Array.isArray(value) ? value.map(String) : [];
}
function word(exercise: Exercise): string {
  return String(exercise.payload.word ?? exercise.prompt);
}
function translation(exercise: Exercise): string {
  return String(exercise.payload.translation ?? "");
}
function ipa(exercise: Exercise): string {
  return String(exercise.payload.ipa ?? "");
}
function voice(exercise: Exercise): string | undefined {
  const value = exercise.payload.voice_id;
  return typeof value === "string" ? value : undefined;
}

function feedbackClass(exercise: Exercise) {
  const attempt = attempts.value[exercise.id];
  if (!attempt) return "feedback";
  if (attempt.is_correct === true) return "feedback ok";
  if (attempt.is_correct === false) return "feedback err";
  return "feedback warn";
}

onMounted(async () => {
  try {
    lesson.value = await api.lesson(String(route.params.id));
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos cargar la lección.";
  } finally {
    loading.value = false;
  }
});

async function submitChoice(exercise: Exercise) {
  submitting.value[exercise.id] = true;
  try {
    const selected = answers.value[exercise.id];
    const attempt = await api.submitAttempt(exercise.id, {
      response: { answer: Number(selected) },
    });
    attempts.value[exercise.id] = attempt;
    feedback.value[exercise.id] = attempt.feedback ?? "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos guardar tu respuesta.";
  } finally {
    submitting.value[exercise.id] = false;
  }
}

async function submitText(exercise: Exercise) {
  submitting.value[exercise.id] = true;
  try {
    const attempt = await api.submitAttempt(exercise.id, {
      response: { text: answers.value[exercise.id] ?? "" },
    });
    attempts.value[exercise.id] = attempt;
    feedback.value[exercise.id] = attempt.feedback ?? "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos guardar tu respuesta.";
  } finally {
    submitting.value[exercise.id] = false;
  }
}

function onRecorded(exercise: Exercise, attempt: AttemptResult) {
  attempts.value[exercise.id] = attempt;
  feedback.value[exercise.id] = attempt.feedback ?? "Grabación guardada.";
}

async function completeLesson() {
  if (!lesson.value) return;
  completing.value = true;
  try {
    await api.completeLesson(lesson.value.id);
    lessonCompleted.value = true;
    await router.push({ name: "progress" });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos completar la lección.";
  } finally {
    completing.value = false;
  }
}
</script>

<template>
  <section>
    <RouterLink to="/" class="muted">← Volver a cursos</RouterLink>

    <p v-if="loading" class="muted">Cargando lección…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else-if="lesson">
      <div class="exercise-head" style="margin-top: 0.8rem">
        <h1 style="margin: 0">{{ lesson.title }}</h1>
        <span class="chip">A1</span>
      </div>
      <p class="lead">{{ lesson.description }}</p>

      <div class="feedback warn" style="margin-bottom: 1rem">
        Práctica libre: escucha, graba y compara. La evaluación fonética está
        desactivada; no hay puntaje.
      </div>

      <article
        v-for="(exercise, index) in lesson.exercises"
        :key="exercise.id"
        class="card exercise"
      >
        <div class="exercise-head">
          <span class="chip">Ejercicio {{ index + 1 }}</span>
          <span class="muted" style="font-size: 0.8rem">
            {{
              isRepeat(exercise)
                ? "Escuchar y repetir"
                : isChoice(exercise)
                  ? "Opción múltiple"
                  : "Traducción"
            }}
          </span>
        </div>
        <p class="prompt">{{ exercise.prompt }}</p>

        <template v-if="isRepeat(exercise)">
          <Recorder
            :exercise-id="exercise.id"
            :text="word(exercise)"
            :translation="translation(exercise)"
            :ipa="ipa(exercise)"
            :voice-id="voice(exercise)"
            @submitted="onRecorded(exercise, $event)"
          />
        </template>

        <template v-else-if="isChoice(exercise)">
          <div class="options">
            <label v-for="(option, optionIndex) in options(exercise)" :key="optionIndex" class="option">
              <input
                v-model="answers[exercise.id]"
                type="radio"
                :name="`exercise-${exercise.id}`"
                :value="String(optionIndex)"
              />
              {{ option }}
            </label>
          </div>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="submitting[exercise.id] || answers[exercise.id] === undefined"
            @click="submitChoice(exercise)"
          >
            {{ submitting[exercise.id] ? "Guardando…" : "Comprobar" }}
          </button>
        </template>

        <template v-else-if="isText(exercise)">
          <input
            v-model="answers[exercise.id]"
            class="input"
            :placeholder="'Escribe tu respuesta en inglés'"
            @keyup.enter="submitText(exercise)"
          />
          <button
            class="btn btn-primary"
            type="button"
            style="margin-top: 0.7rem"
            :disabled="submitting[exercise.id] || !answers[exercise.id]"
            @click="submitText(exercise)"
          >
            {{ submitting[exercise.id] ? "Guardando…" : "Comprobar" }}
          </button>
        </template>

        <p v-if="attempts[exercise.id]" :class="feedbackClass(exercise)">
          {{ feedback[exercise.id] }}
          <span v-if="attempts[exercise.id].is_correct === true">✓</span>
          <span v-else-if="attempts[exercise.id].is_correct === false">Revisa e inténtalo otra vez.</span>
        </p>
      </article>

      <div class="card" style="display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap">
        <div>
          <strong>¿Terminaste la lección?</strong>
          <p class="muted" style="margin: 0.2rem 0 0">
            {{ Object.keys(attempts).length }} de {{ lesson.exercises.length }} ejercicios
            practicados.
          </p>
        </div>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="!allAttempted || completing || completed"
          @click="completeLesson"
        >
          {{ completing ? "Guardando…" : completed ? "Lección completada" : "Completar lección" }}
        </button>
      </div>
    </template>
  </section>
</template>
