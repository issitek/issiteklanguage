# Issitek Language

**Issitek Language** es una plataforma SaaS de aprendizaje de inglés para México:
un profesor virtual 3D que conversa por voz con estudiantes mexicanos y adapta
las clases a su nivel. Dominio comercial: **talkdrill.com**.

Web (Vue 3) + Android/iOS (Capacitor) · IA híbrida (Qwen local + API externa)
· **WebRTC-first** (aiortc + coturn, sin SFU) desde el día 1.

## Estado: Fase 1 — Fundamentos

- **Fase 0 (voz): cerrada y aprobada.** Ciclo WebRTC → STT → LLM → TTS → RTP →
  visemas validado en laboratorio ([`docs/LABORATORIO_FASE0.md`](docs/LABORATORIO_FASE0.md)).
- **Fase 0b (evaluación fonética): investigación paralela, no bloqueante.**
  El puntaje de pronunciación permanece desactivado
  (`PRONUNCIATION_EVAL_ENABLED=false`) hasta superar su gate de validación.
- **Fase 1 en curso:** plataforma base, contrato del evaluador, modelo de voz y
  consentimientos, TTS de referencia y la primera vertical slice funcional.

Regla de producto: mientras el evaluador no esté validado, el alumno puede
**escuchar, grabar, repetir y autocomparar**, pero **no se le muestra un puntaje**.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/DOCUMENTO_MAESTRO.md`](docs/DOCUMENTO_MAESTRO.md) | Visión, ADRs, arquitectura, contratos API, esquema SQL, fases 0–6 |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Items `TD-F<fase>-<nnn>` con prioridad, estimación y criterios de aceptación |
| [`docs/fase1/plan-fase1.md`](docs/fase1/plan-fase1.md) | Alcance, orden de trabajo y vertical slice de Fase 1 |
| [`docs/fase1/contrato-evaluador.md`](docs/fase1/contrato-evaluador.md) | Puerto `PronunciationEvaluator`, resultado normalizado y adaptadores |
| [`docs/fase1/modelo-datos-voz.md`](docs/fase1/modelo-datos-voz.md) | Consentimientos, grabaciones, TTS de referencia y retención |
| [`docs/LABORATORIO_FASE0.md`](docs/LABORATORIO_FASE0.md) | Informe go/no-go de Fase 0 (voz) |
| [`docs/fase0/poc-pronunciacion.md`](docs/fase0/poc-pronunciacion.md) | Estado de la investigación fonética (Fase 0b) |
| [`lab/README.md`](lab/README.md) | Cómo arrancar y verificar el laboratorio |

## Estructura

```
docs/     Documento maestro, backlog, informes y planes de fase
lab/      Laboratorio de validación de IA (voz y pronunciación)
apps/     Vue 3 + Capacitor            (Fase 1+)
services/ api · voice · worker · tts   (Fase 1+)
infra/    Docker Compose propio, nginx, coturn (Fase 1+)
```

## Primer recorrido (vertical slice de Fase 1)

1. Un alumno inicia sesión.
2. Accede a un curso A1.
3. Abre una lección.
4. Escucha una palabra mediante Kokoro (audio de referencia cacheado).
5. Graba su pronunciación con `MediaRecorder`.
6. El audio se almacena en MinIO con URL firmada y verificación SHA-256.
7. Se registra el intento educativo (`exercise_attempts`).
8. El sistema muestra su progreso.
9. La evaluación fonética permanece desactivada.

## Principios clave

1. La app nunca habla directamente con un proveedor de IA: todo pasa por el AI Router.
2. El audio conversacional viaja por WebRTC (Opus/DTLS-SRTP); DataChannel para eventos y visemas.
3. La grabación de ejercicios usa `MediaRecorder` + subida firmada; WebRTC es solo conversación.
4. El evaluador fonético es un puerto intercambiable; el motor pedagógico decide la corrección.
5. La puntuación educativa (`exercise_attempts`) y la fonética (`pronunciation_attempts`) están separadas.
6. El avatar se renderiza en el dispositivo (Three.js + VRM); no se genera video.
7. Este repo es independiente del monorepo padre `/home/dev/share`.
