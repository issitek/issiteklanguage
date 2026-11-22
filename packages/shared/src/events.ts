/**
 * Contrato v1 del DataChannel `events` (ADR-004).
 *
 * El audio viaja por RTP; este canal solo lleva JSON pedagógico y de control.
 * El contrato se ampliará en F2/F3 sin romper `v: 1`.
 */

export type EventVersion = 1;

export interface EventEnvelope {
  type: string;
  v: EventVersion;
  session_id: string;
  /** ISO-8601 con zona horaria. */
  ts: string;
}

export type ListeningState = "listening" | "thinking" | "speaking";

export interface Viseme {
  /** Milisegundos desde el inicio del audio del turno. */
  t_ms: number;
  /** Identificador VRM/Mixamo: sil, B, AA, etc. */
  id: string;
  /** Peso 0..1. */
  weight: number;
}

export interface Correction {
  original: string;
  corrected: string;
  reason: string;
  error_type: string;
}

export interface AssistantResponseEvent extends EventEnvelope {
  type: "assistant_response";
  text: string;
  display_translation?: string | null;
  correction?: Correction | null;
  emotion?: string | null;
  visemes?: Viseme[];
  audio_seq?: number | null;
  model?: string | null;
}

export interface TurnEndEvent extends EventEnvelope {
  type: "turn_end";
}

export interface InterruptEvent extends EventEnvelope {
  type: "interrupt";
}

export interface ListeningStateEvent extends EventEnvelope {
  type: "listening_state";
  state: ListeningState;
}

export interface CorrectionHintEvent extends EventEnvelope {
  type: "correction_hint";
  text: string;
  error_type?: string | null;
}

export interface ErrorEvent extends EventEnvelope {
  type: "error";
  code: string;
  message: string;
}

export type ServerEvent =
  | AssistantResponseEvent
  | TurnEndEvent
  | InterruptEvent
  | ListeningStateEvent
  | CorrectionHintEvent
  | ErrorEvent;

export interface ClientHelloEvent extends EventEnvelope {
  type: "client_hello";
  client_version: string;
  capabilities: {
    visemes: boolean;
    audio_formats: string[];
  };
  locale: string;
}

export interface ClientInterruptEvent extends EventEnvelope {
  type: "interrupt";
}

export interface CaptionAckEvent extends EventEnvelope {
  type: "caption_ack";
  audio_seq: number;
}

export interface SessionMetricsEvent extends EventEnvelope {
  type: "session_metrics";
  rtt_ms: number;
  bytes_sent: number;
  bytes_received: number;
  candidate_type?: string | null;
}

export type ClientEvent =
  | ClientHelloEvent
  | ClientInterruptEvent
  | CaptionAckEvent
  | SessionMetricsEvent;

export function isServerEvent(value: unknown): value is ServerEvent {
  if (!value || typeof value !== "object") return false;
  const event = value as Partial<ServerEvent>;
  return event.v === 1 && typeof event.type === "string" && typeof event.session_id === "string";
}
