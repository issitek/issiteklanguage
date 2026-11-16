# Guion de grabación — PoC de pronunciación (Fase 0b)

**Objetivo:** 8–12 hablantes mexicanos leyendo 30 frases en inglés para calibrar
OpenPronounce (¿qué tan bien detecta errores /θ ð ɪ iː ɹ ʃ tʃ/ en learner-English es-MX?).
El humo con Kokoro (98.39/100) **no** es evidencia de es-MX — este dataset sí lo es.

**Requisitos:** cuarto silencioso (ventana cerrada, TV apagada), audífonos de locutor
(o micrófono a 15–20 cm), Chrome en la laptop del laboratorio o cualquier grabadora.
Formato **WAV 16 kHz mono** (aunque graben a 44.1 kHz, se convierte en el análisis).
Nombre de archivo: `<hablante>-<frase>.wav` — p. ej. `ana-12.wav`.

## Consentimiento (antes de grabar)

1. Entregar hoja de **consentimiento** (`consentimiento-plantilla.md`); firmar o grabar
   acuerdo verbal. Las firmas/archivos van a `lab/data/pronunciation/consent/` (**fuera de git**).
2. Se les explica: grabaciones para calibrar un sistema interno, no se publican,
   no se comparten con terceros, pueden pedir borrado en cualquier momento.
3. Asignar id de hablante (`s01`, `s02`, …) — los nombres reales van en
   `lab/data/pronunciation/manifest.json` (**fuera de git**), nunca en los archivos ni en git.

## Las 30 frases (A1–B1)

| # | Frase (EN) | Foco fonético |
|---|---|---|
| 1 | Good morning! How are you today? | warm-up general |
| 2 | Thank you very much. | /θ/ inicial |
| 3 | I think this is good. | /θ/, /ð/ |
| 4 | Three thin things are there. | /θ/ ×3-4 |
| 5 | My mother and father are together. | /ð/ ×2 |
| 6 | I went to the third floor. | /ð/, /θ/ |
| 7 | I usually go on the third of May. | /θ/ |
| 8 | This is the other one. | /ð/ |
| 9 | The weather is better in spring. | /ð/, /æ/ |
| 10 | There are three theaters in town. | /ð/, /θ/ ×2 |
| 11 | She thought about those things for a month. | /θ/, /ð/ |
| 12 | I see a sheep on the ship. | /iː/, /ɪ/ |
| 13 | Please sleep near the sink. | /iː/, /ɪ/ |
| 14 | He is living in a little house near the beach. | /ɪ/, /iː/ |
| 15 | Fit or feed, which do you need? | /ɪ/ vs /iː/ |
| 16 | I swim in the sea every summer. | /ɪ/, /iː/ |
| 17 | The list of seats is little. | /ɪ/, /iː/ |
| 18 | Red roses grow in the garden. | /ɹ/, /ɹ/, /ɹ/ |
| 19 | Rice is delicious with ripe tomatoes. | /ɹ/ ×2 |
| 20 | My brother runs every morning on the river road. | /ɹ/ ×4, /æ/ |
| 21 | The price of fresh fruit is really high. | /ɹ, ɹ, ɹ/, /aɪ/ |
| 22 | She sells fresh fish and chips. | /ʃ/, /ʃ/, /f/ |
| 23 | I watch TV on Sundays and shop on Friday. | /tʃ/, /ʃ/ |
| 24 | Chicken, cheese and churros, please! | /tʃ/ ×3 |
| 25 | The teacher teaches touch in class. | /tʃ/ ×3 |
| 26 | I bought a very cheap phone with cash. | /tʃ/, /ʃ/, /æ/ |
| 27 | She lives in a big apartment near the beach. | /ɪ/, /ɑ/, /iː/ |
| 28 | I drink tea every day at seven. | warm-up silábico |
| 29 | I would like a chicken sandwich and a drink. | /tʃ/, move-up |
| 30 | These three things are for them. | /ð/, /θ/ ×2, /ð/ |

## Instrucciones para el hablante

1. Repite la frase 1 vez de corrido. Si tropiezas, respira y haz TODA la frase de nuevo
   (la repetición sustituye la toma anterior).
2. Habla con naturalidad (ni susurro ni muy fuerte). No sobre-articula.
3. Entre frases, pausa ~1 segundo.
4. No leas el español; si no entiendes una palabra, te la explico en el momento.
5. Al terminar, guarda los archivos en `lab/data/pronunciation/audio/<hablante>/`.

## Etiquetado (2 jueces)

Plantilla CSV: `labels-template.csv` (copiar como `lab/data/pronunciation/labels/<juez>.csv`).
Por palabra: `ok` (correcto), `mejorable` (se entiende pero con desviación clara),
`mal` (incorrecto/ininteligible). Si es `mejorable/mal`, anotar el fonema sospechoso
(/θ/, /ð/, /ɪ/…) en `phoneme`. Es suficiente con marcar las palabras con problema;
el resto se asume `ok` — pero ante la duda, marca `mejorable`.

## Comprobación física por archivo

```bash
cd /home/dev/share/issitekLanguage/lab/data/pronunciation/audio/<hab>
ls *.wav | wc -l        # debe ser 30
file 01.wav             # WAV RIFF
```

Cuando estén las 10 grabaciones × 30 frases = 300 archivos (o menos con menos hablantes),
avisa y corro P2–P4 (bench, calibración y el informe).
