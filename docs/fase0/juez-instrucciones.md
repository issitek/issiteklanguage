# Instrucciones para etiquetar (jueces 1 y 2)

**Qué estás anotando:** en qué palabras el evaluador automático puede estar equivocado. NO se trata de juzgar tu español, sino de marcar si la palabra suena **bien, mejorable o mal** tal como la dijo el hablante (en inglés mexicano, con acento propio aceptable).

**Criterios:**
- `ok` = pronunciada correcta (sonoridad, acento, duración); la marcación del sistema es falsa alarma
- `mejorable` = se entiende pero suena raro o con desviación clara
- `mal` = ininteligible o sustitución de fonema (p. ej. /θ/→/t/, /ɪ/ vs /iː/)
- `no-aplica` = ruido/sin señal útil (p. ej. `s06` es silencio; todos sus flags se consideran `no-aplica`)

**Método:**
1. Abre `labels/judgeN.csv` en un editor de texto/Excel.
2. Escucha el audio de la frase (están en `audio/<speaker>/NN.wav`), localiza la palabra, escribe `ok`/`mejorable`/`mal`/`no-aplica` en `verdict` y una nota breve en `notes`.
3. Mantén el resto de columnas intactas.

**Distribución de trabajo:**
- `judge1.csv` lo hace persona 1; `judge2.csv` lo hace persona 2.
- s06 todos `no-aplica` (es silencio); el resto ~30-60 min entre ambos.

**Qué hacer al terminar:** avisa que los audios estén etiquetados; se calcula F1/precisión/recall/falsos positivos entre las dos marcas.
