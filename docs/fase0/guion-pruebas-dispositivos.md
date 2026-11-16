# Guion de pruebas en dispositivos — talkdrill Fase 0
**Fecha:** 2026-11-16 · **Requisitos:** Android real (Chrome), iPhone real (Safari/WKWebView),
máquina Fedora con el lab corriendo, misma red Wi-Fi, datos móviles disponibles.

Objetivo: validar en dispositivos reales lo que el laboratorio ya verificó en frío:
conexión, audio bidireccional, permisos de micrófono, reconexión, suspensión/reanudación,
barge-in, y TURN relay forzado. Resultado esperado: matrices U11–U16 para `LABORATORIO_FASE0.md` §2.

> ⚠️ **Seguridad:** este guion expone el lab-server en la LAN (`192.168.1.42:9090`).
> Es HTTP sin TLS en red doméstica, con token. Al terminar, revertir el override
> (volver a levantar sin `docker-compose.lan.yml`).

## 0. Preparación (Fedora)

```bash
cd /home/dev/share/issitekLanguage/lab
ip -4 addr show enp8s0 | grep inet        # IP LAN (p. ej. 192.168.1.42)
grep LAB_TOKEN .env.lab                    # token del lab-server (pásalo al teléfono)
docker compose --env-file .env.lab -f docker-compose.yml -f docker-compose.lan.yml up -d lab-server
# abre el firewall solo si el teléfono no llega:
# sudo firewall-cmd --add-port=9090/tcp --zone=public   (revertir con --remove-port)
# Comprobar desde la Fedora: curl -s http://<IP-LAN>:9090/health
```

Desde el teléfono (mismo Wi-Fi):
`http://<IP-LAN>:9090/` → pegar el token → **Conectar**.

## 1. Checklist Android (Chrome) — TD-F0-014

| # | Paso | Resultado esperado |
|---|---|---|
| A1 | Abrir `http://<IP-LAN>:9090/` en Chrome Android | Carga la página; botón Conectar visible |
| A2 | Pulsar Conectar → conceder permiso de micrófono | Conexión establecida; estado "connected · host" o relay; RTT visible |
| A3 | Hablar: "Yesterday I go to the school" | El profesor (Alex, voz en-US) responde por el altavoz; en pantalla aparece `assistant_response` con la corrección (went/past simple); visemas en el canvas |
| A4 | Con permiso denegado → reconectar | Mensaje claro de error; la app no se rompe |
| A5 | Conectar con audífonos (con mic) | Sin eco ni bucle de audio |
| A6 | Durante la respuesta del profesor, hablar fuerte (barge-in) | El profesor se calla < 1 s; evento `interrupt` en el log; `listening` tras el corte |
| A7 | Cambiar a otra app 30 s y volver | Sesión viva o reconexión < 5 s; si cayó, el estado se muestra |
| A8 | Cortar Wi-Fi (modo avión) 10 s, restaurar | Reintentar / re-Conectar manual; sin perder el historial en logs |
| A9 | Reps: 5 frases seguidas | latencia estable; sin crecimiento de memoria (chrome://inspect opcional) |
| A10 | Telemetría: pulsar "Reportar ICE (getStats)" | Reporte en `GET /webrtc/ice-report/recent` (candidateType, RTT, bytes) |

## 2. Checklist iPhone (Safari/WKWebView) — TD-F0-015

Misma lista A1–A10 en Safari iOS. **Especial atención:**
- Safari iOS puede no sostener WebRTC bidireccional estable → si falla, anotar versión iOS y WebKit;
  plan B: documentar y evaluar `@capacitor-community/webrtc` o requisito Safari 16+.
- iOS exige interacción de usuario antes de reproducir audio remoto (el botón Conectar la satisface).

## 3. TURN relay forzado — TD-F0-016

En la página, marcar **"Forzar relay TURN"** y repetir A2–A3. El candidato ganador debe ser
`relay` y la conversación debe funcionar igual (más latencia). Telemetría confirma `candidateType: relay`.
Repetir con datos móviles (Wi-Fi off) para NAT realista.

## 4. Encuesta humana rápida (para el informe)

Por cada dispositivo: ¿El profesor se entendió? (1–5) · ¿Corrección percibida? (1–5) ·
¿Latencia molesta? (sí/no) · ¿Crash o corte? (detalle)

## 5. Volcado de evidencia

Anotar en `docs/LABORATORIO_FASE0.md` §2 una fila por dispositivo/red con el resultado
(pass/fail), y pegar RTT/candidateType/transcript de la sesión. Si iPhone falla:
marcar TD-F0-015 como no-go parcial y discutir plan B antes del go/no-go.

## 6. Limpieza

```bash
cd /home/dev/share/issitekLanguage/lab
docker compose --env-file .env.lab up -d lab-server   # vuelve a 127.0.0.1
sudo firewall-cmd --remove-port=9090/tcp --zone=public 2>/dev/null || true
```
