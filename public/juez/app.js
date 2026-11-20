/* talkdrill — etiquetado por jueces (juez1 / juez2) */
'use strict';

const state = {
  rows: [],        // lista de evaluaciones (de sheet.json)
  index: 0,
  verdicts: {},    // key → verdict string
  notes: {},       // key → nota
  judge: null,
};

const $ = (id) => document.getElementById(id);
const show = (id) => {
  document.querySelectorAll('.screen').forEach(s => s.classList.toggle('active', s.id === id));
};

function saveProgress() {
  if (!state.judge) return;
  state.seq = (state.seq || 0) + 1;
  // fire-and-forget CON keepalive: aunque se cierre la pestaña al instante, llega
  fetch('/juez/progress', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({index: state.index, verdicts: state.verdicts, notes: state.notes, seq: state.seq}),
    keepalive: true,
  }).catch((e) => console.warn('no se pudo guardar progreso:', e));
}
function queueSave() { saveProgress(); }  // guardado inmediato, sin retardo
// Red de seguridad: si el navegador se cierra/va a segundo plano, vuelve a enviar
window.addEventListener('pagehide', saveProgress);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') saveProgress(); });

async function init() {
  try {
    const r = await fetch('/juez/role');
    if (r.status === 401) throw new Error('sin autenticación');
    const d = await r.json();
    state.judge = d.judge;
  } catch {
    alert('No se pudo identificar tu sesión. Cierra y vuelve a abrir el enlace.');
    return;
  }
  $('judgeTag').textContent = state.judge ? state.judge.toUpperCase() : 'JUEZ';
  const sheet = await fetch('/juez/sheet.json').then(r => r.json());
  state.rows = sheet.map(r => ({ ...r, key: `${r.file}:${r.word}` }));
  // restaurar progreso del servidor (SQLite) — sin importar el dispositivo
  try {
    const resp = await fetch('/juez/progress');
    if (resp.ok) {
      const saved = await resp.json();
      state.index = Math.min(Math.max(0, saved.index | 0), state.rows.length - 1);
      state.verdicts = saved.verdicts || {};
      state.notes = saved.notes || {};
      state.seq = saved.seq || 0;
      console.log('progreso servidor: índice', saved.index, 'seq', state.seq);
      if (saved.index > 0) {
        const tag = $('resumeBanner') || document.createElement('p');
        tag.id = 'resumeBanner';
        tag.className = 'small';
        tag.style.color = '#9fe8b0';
        tag.textContent = `↩ Avance recuperado: ibas en la evaluación ${saved.index + 1} de ${state.rows.length}`;
        document.querySelector('#screen-welcome .card').appendChild(tag);
      }
    }
  } catch (e) { console.warn('no se pudo leer progreso del servidor:', e); }
  $('totalItems').textContent = state.rows.length;
  show('screen-welcome');
}

function current() {
  return state.rows[state.index];
}

function ttsEscape(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function escapedPhraseWithWord(p, w) {
  const safeWord = ttsEscape(w), safePh = ttsEscape(p);
  return safePh.replace(new RegExp(`(${safeWord})`, 'i'),
    `<span class="word-flag">$1</span>`);
}

function renderItem() {
  const r = current();
  if (!r) return;
  $('progressLabel').textContent = `Palabra ${state.index + 1} / ${state.rows.length}`;
  $('progressFill').style.width = `${((state.index + 1) / state.rows.length) * 100}%`;
  $('speakerTag').textContent = r.speaker;
  $('fileTag').textContent = `frase #${r.file_id} · score automático ${r.score.toFixed(1)}`;
  $('phraseText').innerHTML = escapedPhraseWithWord(r.text, r.word);
  $('phonesExpected').textContent = r.expected || '—';
  $('phonesActual').textContent = r.actual || '—';
  $('confBar').style.width = `${Math.round((r.confidence || 0) * 100)}%`;
  $('confText').textContent = `confianza: ${((r.confidence || 0) * 100).toFixed(0)}%`;
  // propiedades HTML escape-safe
  const audio = $('audio');
  audio.src = `/juez/audios/${r.file}`;  // ya viene tipo "s4ytvdu/01.wav"
  audio.load();
  $('notes').value = state.notes[r.key] || '';
  const chosen = state.verdicts[r.key];
  document.querySelectorAll('.verdict').forEach(b => b.classList.toggle('primary', b.dataset.v === chosen));
  $('btnPrev').disabled = state.index === 0;
  $('btnNext').textContent = state.index === state.rows.length - 1 ? 'Terminar →' : 'Siguiente →';
}

function commitVerdict(v) {
  state.verdicts[current().key] = v;
  queueSave();
  document.querySelectorAll('.verdict').forEach(b => b.classList.toggle('primary', b.dataset.v === v));
}

document.querySelectorAll('.verdict').forEach(b => {
  b.addEventListener('click', () => commitVerdict(b.dataset.v));
});
$('notes').addEventListener('input', e => {
  state.notes[current().key] = e.target.value;
  queueSave();
});

$('btnStart').addEventListener('click', () => {
  show('screen-task');
  renderItem();
});
$('btnPrev').addEventListener('click', () => {
  if (state.index > 0) { state.index -= 1; queueSave(); show('screen-task'); renderItem(); }
});
$('btnNext').addEventListener('click', () => {
  if (state.index < state.rows.length - 1) {
    state.index += 1; queueSave(); show('screen-task'); renderItem();
  } else {
    show('screen-done');
    $('doneCount').textContent = Object.keys(state.verdicts).length;
  }
});

$('btnSend').addEventListener('click', async () => {
  const btn = $('btnSend');
  btn.disabled = true;
  $('sendStatus').textContent = 'Enviando…';
  const rows = state.rows.map(r => ({
    speaker: r.speaker,
    file_id: r.file_id,
    file: r.file,
    word: r.word,
    expected: r.expected,
    actual: r.actual,
    verdict: state.verdicts[r.key] || null,
    notes: state.notes[r.key] || null,
  }));
  try {
    const resp = await fetch('/judge/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ judge: state.judge, rows }),
    });
    const txt = await resp.text();
    if (!resp.ok) throw new Error(txt);
    $('sendStatus').textContent = '✅ Enviado. Gracias.';
    btn.textContent = '✔ Enviado';
    await fetch('/juez/progress', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({index: 0, verdicts: {}, notes: {}, seq: (state.seq || 0) + 1})});
  } catch (err) {
    btn.disabled = false;
    $('sendStatus').textContent = 'No se pudo enviar. Intenta de nuevo o avísale al organizador.';
  }
});

init();
