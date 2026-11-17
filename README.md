# Grabador web de frases — talkdrill (Fase 0b)

Página **estática** (HTML/CSS/JS vanilla, sin backend ni dependencias) para grabar
las 30 frases de calibración con voluntarios. Los audios salen del navegador **solo
si el participante los exporta** (ZIP o carpeta local). Nada se sube a ningún servidor.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | Pantallas: consentimiento + código → 30 frases → exportación |
| `app.js` | Lógica de grabación (16 kHz mono WAV), WAV/ZIP, progreso |
| `codec.js` | Codificadores puros (WAV, CRC32, ZIP store-only); testeable en node |
| `style.css` | Tema oscuro, botones grandes, responsive |

## Publicar en GitHub Pages

Sin servidor, sin build. Dos caminos:

**A (recomendado): repo propio mínimo.** Copia estos 4 archivos a un repo público
pequeño (p. ej. `talkdrill-grabador`), activa **Settings → Pages → Branch main /(root)**
y el enlace es `https://<tu-usuario>.github.io/talkdrill-grabador/`.

**B: este mismo repo.** Ajusta **Pages → main, `/`** no aplica a subcarpetas arbitrarias;
la opción práctica es `main` con `./lab/web-grabador` solo si reorganizas a `/docs`
(GitHub Pages solo publica `/` o `/docs`).

En ambos casos, comparte el enlace a los voluntarios. En Pages (HTTPS) el micrófono
funciona sin avisos.

## Guía para el voluntario

1. Abre el enlace. Lee y marca el consentimiento.
2. Escribe tu **código** asignado (p. ej. `s03`) — **nada de nombres**.
3. Pulsa **Grabar**, di la frase y pulsa **Detener** (o Espacio).
4. Repite para las 30 frases (↻ Reintentar si hace falta).
5. Al final:
   - **Descargar ZIP** (`s03.zip` con `s03/01.wav…30.wav`), envíalo como archivo
     (WhatsApp/email), o
   - **Guardar en carpeta…** (Chrome/Edge): elige la carpeta `audio/` destinataria;
     los archivos se escriben directamente como `s03/NN.wav`.

## Integración con el laboratorio

Al recibir un ZIP: `unzip s03.zip -d lab/data/pronunciation/audio/`
→ quedan en `lab/data/pronunciation/audio/s03/01.wav…30.wav` listos para calibrar
OpenPronounce (ver `docs/fase0/guion-pronunciacion.md` y `poc-pronunciacion.md`).

Datos de participantes (audios, consentimientos firmados, manifest) viven en
`lab/data/pronunciation/` — **fuera de git** (`lab/data/` ignorado).

## Verificado en este laboratorio (2026-11-16)

- Codificador WAV validado contra `wave` de Python; ZIP validado contra `zipfile`.
- Flujo UI verificado con navegador headless (consentimiento → código → frase 1/30).
- Compatibilidad OpenPronounce: los WAV generados (s16 16 kHz mono PCM) se abren con `wave` estándar y con el evaluador.
