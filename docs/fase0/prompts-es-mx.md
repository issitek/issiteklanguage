# Set de prompts curados — es-MX → en (A1–A2)
**Uso:** evaluación pedagógica del LLM local (TD-F0-008) y set de regresión para Fases 2+.
El alumno produce la frase con error; Alex (profesor) debe corregir con amabilidad,
en español cuando sea necesario, devolviendo `correction` no nula y JSON válido.

| # | Frase del alumno (error típico) | Corrección esperada | Tipo de error |
|---|---|---|---|
| 1 | Yesterday I go to the school. | Yesterday I went to school. | past_simple (go→went) + artículo sobrante |
| 2 | I have saw that movie three times. | I have seen that movie three times. | present_perfect (saw→seen) |
| 3 | She don't like coffee. | She doesn't like coffee. | 3rd person singular (don't→doesn't) |
| 4 | I work in a office near downtown. | I work in an office near downtown. | artículo (a→an) |
| 5 | How many money do you need? | How much money do you need? | cuantificador con incontables |
| 6 | I am agree with you. | I agree with you. | calco del español (ser/estar + adjetivo) |
| 7 | I live here since 2019. | I have lived here since 2019. | present_perfect con since |
| 8 | I didn't understood the question. | I didn't understand the question. | did + base (understood→understand) |
| 9 | I like very much the food. | I like the food very much. | orden de adverbio (calco es-MX) |
| 10 | Yesterday, I have called him. | Yesterday, I called him. | past simple con marcador temporal (no present perfect) |
| 11 | I have 25 years. | I am 25 years old. | calco es-MX (tener→to be) |
| 12 | She works in the home. | She works at home. | preposición (in→at) |
| 13 | I am busy of work. | I am busy with work. | preposición (of→with) |
| 14 | He arrived at Monday. | He arrived on Monday. | preposición de tiempo (at→on) |
| 15 | I don't understand nothing. | I don't understand anything. | doble negación (calco es-MX) |
| 16 | I want practice English. | I want to practice English. | infinitivo con to |
| 17 | I suggest you to study more. | I suggest (that) you study more. | suggest + that-clause |
| 18 | I have breakfast at 7 o'clock in the morning, usually. | I usually have breakfast at 7 in the morning. | adverbio de frecuencia (posición) |
| 19 | I maked a cake yesterday. | I made a cake yesterday. | pasado irregular (maked→made) |
| 20 | I go often to the park. | I often go to the park. | orden de adverbio (often) |
| 21 | I am learning English for 2 years. | I have been learning English for 2 years. | present perfect continuous |
| 22 | The teacher explained us the lesson. | The teacher explained the lesson to us. | explained + to (no doble objeto) |
| 23 | I am interesting in music. | I am interested in music. | -ed vs -ing (calco es-MX) |
| 24 | Can you give me an advice? | Can you give me some advice? / Can you give me a piece of advice? | incontable (a→some) |
| 25 | I have worked here since 3 years. | I have worked here for 3 years. | since vs for |
| 26 | I don't know to swim. | I don't know how to swim. | know how to |
| 27 | My sister is more intelligenter than me. | My sister is more intelligent than me. / …cleverer… | comparativo doble (calco es-MX) |
| 28 | I am not sure if he comes tomorrow. | I am not sure if he will come tomorrow. | futuro en prótasis |
| 29 | I prefer tea than coffee. | I prefer tea to coffee. | prefer … to |
| 30 | It depends of the day. | It depends on the day. | preposición (of→on) |

## Criterios de evaluación del modelo

Para cada prompt se evalúa (pass/fail por ítem):
1. **JSON válido** (claves maestro §8.3: `reply_text`, `correction`, `emotion`).
2. **Corrección detectada**: `correction` no nula con `corrected` igual a la esperada
   (o equivalente correcto; revisión manual).
3. **Tono**: amable, español mexicano disponible, sin sarcasmo.
4. **Pedagogía**: no solo "correcto"; debe ofrecer por qué (o ejemplo) brevemente.

**Aprobación (TD-F0-008/020):** ≥ 80% (24/30) con la corrección esperada o
equivalente correcta. JSON válido en ≥ 95% (29/30). Este archivo se versiona como set de regresión.
