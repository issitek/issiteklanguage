import type {
  AttemptResult,
  Consent,
  Course,
  Lesson,
  LessonComplete,
  Presign,
  Progress,
  Recording,
  Token,
  TtsReference,
  User,
} from "@issitek/shared";

export type * from "@issitek/shared";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const ACCESS_KEY = "issitek.access";
const REFRESH_KEY = "issitek.refresh";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "error") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function accessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function rawRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function hasToken(): boolean {
  return Boolean(accessToken());
}

let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refresh = rawRefreshToken();
  if (!refresh) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) {
        clearTokens();
        return false;
      }
      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = accessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401 && retry && rawRefreshToken()) {
    const ok = await refreshSession();
    if (ok) return request<T>(path, options, false);
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(
      data?.error?.message ?? "Ocurrió un error inesperado.",
      response.status,
      data?.error?.code ?? "error",
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * En desarrollo la API firma contra `localhost:8090/s3`. Si el navegador entró
 * por otro host (LAN, túnel, dominio), se reescribe al mismo origen para que el
 * proxy `/s3` siga siendo válido y no dependa del host de la API.
 */
export function signedUrl(url: string): string {
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.pathname.startsWith("/s3/")) {
      return `${window.location.origin}${parsed.pathname}${parsed.search}`;
    }
    return parsed.toString();
  } catch {
    return url;
  }
}

export const api = {
  login: (email: string, password: string) =>
    request<Token>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, display_name: string) =>
    request<Token>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    }),

  logout: (refresh_token: string) =>
    request<void>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  me: () => request<User>("/users/me"),

  courses: () => request<Course[]>("/courses"),

  lesson: (id: string) => request<Lesson>(`/lessons/${id}`),

  submitAttempt: (exerciseId: string, payload: Record<string, unknown>) =>
    request<AttemptResult>(`/exercises/${exerciseId}/attempts`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  completeLesson: (lessonId: string) =>
    request<LessonComplete>(`/lessons/${lessonId}/complete`, { method: "POST" }),

  progress: () => request<Progress>("/me/progress"),

  consents: () => request<Consent[]>("/consents"),

  grantConsent: (kind: string, version = "2026-11-01") =>
    request<Consent>("/consents", {
      method: "POST",
      body: JSON.stringify({ kind, version, granted: true }),
    }),

  ttsReference: async (text: string, voiceId?: string) => {
    const params = new URLSearchParams({ text });
    if (voiceId) params.set("voice_id", voiceId);
    const data = await request<TtsReference>(`/tts/reference?${params.toString()}`);
    return { ...data, url: signedUrl(data.url) };
  },

  presignRecording: async (exerciseId: string | null, durationMs: number, mime: string) => {
    const data = await request<Presign>("/recordings/presign", {
      method: "POST",
      body: JSON.stringify({
        exercise_id: exerciseId,
        duration_ms: Math.max(1, Math.round(durationMs)),
        mime,
      }),
    });
    return { ...data, url: signedUrl(data.url) };
  },

  completeRecording: (recordingId: string, sha256: string, bytes: number) =>
    request<Recording>(`/recordings/${recordingId}/complete`, {
      method: "POST",
      body: JSON.stringify({ sha256, bytes }),
    }),

  async uploadRecording(presign: Presign, blob: Blob, mime: string): Promise<string> {
    const upload = await fetch(signedUrl(presign.url), {
      method: presign.method || "PUT",
      headers: { "Content-Type": mime },
      body: blob,
    });
    if (!upload.ok) {
      throw new ApiError("No se pudo subir la grabación.", upload.status, "upload_failed");
    }
    const hash = await sha256Hex(blob);
    const completed = await api.completeRecording(presign.recording_id, hash, blob.size);
    return completed.id;
  },
};
