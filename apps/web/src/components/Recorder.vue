<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { api, type AttemptResult } from "../api";

const props = defineProps<{
  exerciseId: string;
  text: string;
  translation?: string;
  ipa?: string;
  voiceId?: string;
}>();

const emit = defineEmits<{ submitted: [attempt: AttemptResult] }>();

const hasConsent = ref(false);
const showConsent = ref(false);
const consentBusy = ref(false);
const consentError = ref("");
const referenceBusy = ref(false);
const recording = ref(false);
const uploading = ref(false);
const error = ref("");
const elapsed = ref(0);
const mineUrl = ref<string | null>(null);
const done = ref(false);

let stream: MediaStream | null = null;
let recorder: MediaRecorder | null = null;
let chunks: Blob[] = [];
let startedAt = 0;
let timer: number | undefined;
let mimeType = "audio/webm";

onMounted(async () => {
  try {
    const consents = await api.consents();
    hasConsent.value = consents.some((c) => c.kind === "recording" && c.active);
  } catch {
    // Si falla, se pedirá consentimiento al intentar grabar.
  }
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  stream?.getTracks().forEach((track) => track.stop());
});

function pickMime(): string {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg",
  ];
  for (const candidate of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }
  return "";
}

async function playReference() {
  referenceBusy.value = true;
  error.value = "";
  try {
    const reference = await api.ttsReference(props.text, props.voiceId);
    const audio = new Audio(reference.url);
    await audio.play();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "No pudimos reproducir el audio de referencia.";
  } finally {
    referenceBusy.value = false;
  }
}

function requestRecording() {
  error.value = "";
  if (!hasConsent.value) {
    showConsent.value = true;
    return;
  }
  void startRecording();
}

async function acceptConsent() {
  consentBusy.value = true;
  consentError.value = "";
  try {
    await api.grantConsent("recording");
    hasConsent.value = true;
    showConsent.value = false;
    await startRecording();
  } catch (err) {
    consentError.value =
      err instanceof Error ? err.message : "No se pudo guardar el consentimiento.";
  } finally {
    consentBusy.value = false;
  }
}

async function startRecording() {
  if (recording.value) return;
  error.value = "";
  mineUrl.value = null;
  done.value = false;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chosen = pickMime();
    mimeType = chosen || "audio/webm";
    recorder = chosen ? new MediaRecorder(stream, { mimeType: chosen }) : new MediaRecorder(stream);
    chunks = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    recorder.onstop = () => {
      void handleStop();
    };
    startedAt = Date.now();
    elapsed.value = 0;
    recorder.start();
    recording.value = true;
    timer = window.setInterval(() => {
      elapsed.value = (Date.now() - startedAt) / 1000;
      if (elapsed.value >= 15) stopRecording();
    }, 200);
  } catch {
    error.value = "No pudimos acceder al micrófono. Revisa el permiso del navegador.";
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
  }
}

function stopRecording() {
  if (!recording.value) return;
  recording.value = false;
  if (timer) {
    clearInterval(timer);
    timer = undefined;
  }
  recorder?.stop();
  stream?.getTracks().forEach((track) => track.stop());
  stream = null;
}

async function handleStop() {
  const type = mimeType.split(";")[0];
  const blob = new Blob(chunks, { type });
  mineUrl.value = URL.createObjectURL(blob);
  uploading.value = true;
  try {
    const durationMs = Math.max(300, Date.now() - startedAt);
    const presign = await api.presignRecording(props.exerciseId, durationMs, mimeType);
    const recordingId = await api.uploadRecording(presign, blob, mimeType);
    const attempt = await api.submitAttempt(props.exerciseId, {
      response: { word: props.text },
      recording_id: recordingId,
      time_ms: Math.round(durationMs),
    });
    done.value = true;
    emit("submitted", attempt);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "No pudimos guardar la grabación.";
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <div>
    <div class="word-card">
      <div>
        <div class="word">{{ text }}</div>
        <div v-if="translation" class="muted">{{ translation }}</div>
        <div v-if="ipa" class="ipa">/{{ ipa }}/</div>
      </div>
      <button class="btn btn-secondary" type="button" :disabled="referenceBusy" @click="playReference">
        {{ referenceBusy ? "Cargando…" : "🔊 Escuchar" }}
      </button>
    </div>

    <div class="recorder">
      <button
        v-if="!recording"
        class="btn btn-rec"
        type="button"
        :disabled="uploading"
        @click="requestRecording"
      >
        ● Grabar
      </button>
      <button v-else class="btn btn-stop" type="button" @click="stopRecording">
        ■ Detener
      </button>

      <span v-if="recording" class="timer">{{ elapsed.toFixed(1) }} s</span>
      <span v-if="uploading" class="muted">Subiendo y verificando…</span>
      <span v-if="done" class="chip ok">Intento guardado</span>
    </div>

    <div v-if="mineUrl" style="margin-top: 0.7rem">
      <p class="muted" style="margin: 0 0 0.3rem; font-size: 0.85rem">Tu grabación:</p>
      <audio :src="mineUrl" controls style="width: 100%"></audio>
    </div>

    <p v-if="error" class="feedback err">{{ error }}</p>

    <Teleport to="body">
      <div v-if="showConsent" class="modal-backdrop" @click.self="showConsent = false">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="consent-title">
          <h2 id="consent-title">Permiso para grabar tu voz</h2>
          <p class="muted">
            Para practicar pronunciación necesitamos guardar tu grabación. Este permiso
            es independiente de cualquier envío a proveedores externos.
          </p>
          <ul>
            <li>Solo se guarda el audio del ejercicio, no el audio ambiente.</li>
            <li>La grabación se elimina a los 30 días o antes si lo solicitas.</li>
            <li>Puedes revocar el permiso en cualquier momento.</li>
            <li>En esta fase no se muestra ningún puntaje fonético.</li>
          </ul>
          <p v-if="consentError" class="error">{{ consentError }}</p>
          <div class="actions">
            <button class="btn btn-secondary" type="button" @click="showConsent = false">
              Cancelar
            </button>
            <button class="btn btn-primary" type="button" :disabled="consentBusy" @click="acceptConsent">
              {{ consentBusy ? "Guardando…" : "Acepto y grabo" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
