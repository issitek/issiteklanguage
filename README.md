# talkdrill.com

Plataforma SaaS de aprendizaje de inglés para México: un profesor virtual 3D
que conversa por voz con estudiantes mexicanos y adapta las clases a su nivel.
Web (Vue 3) + Android/iOS (Capacitor) · ia híbrida (Qwen local + API externa)
· **WebRTC-first** (aiortc + coturn, sin SFU) desde el día 1.

## Estado: Fase 0 — Laboratorio de validación

Regla de ingeniería: **no se construye el producto completo hasta demostrar
el ciclo WebRTC → STT → LLM → TTS → RTP de regreso → sincronización de visemas
en dispositivos reales.**

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/DOCUMENTO_MAESTRO.md`](docs/DOCUMENTO_MAESTRO.md) | Visión, ADRs, arquitectura, contratos API, esquema SQL, Fases 0–6 |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | 85 items `TD-F<fase>-<nnn>` con criterios de aceptación |
| [`lab/README.md`](lab/README.md) | Cómo arrancar y verificar el laboratorio |

## Estructura (en construcción)

```
docs/    Documento maestro, backlog, informe de laboratorio
lab/     Laboratorio de validación de IA (Fase 0)
apps/    Vue 3 + Capacitor (Fase 1+, aún no creado)
services/ api · voice · worker (Fase 1+, aún no creado)
infra/   Docker Compose, nginx, coturn (Fase 1+, aún no creado)
```

## Principios clave

1. La app nunca habla directamente con un proveedor de IA: todo pasa por el AI Router.
2. El audio viaja por WebRTC (Opus/DTLS-SRTP); DataChannel para eventos y visemas.
3. El avatar se renderiza en el dispositivo (Three.js + VRM); no se genera video.
4. Este repo es independiente del monorepo padre `/home/dev/share`.
