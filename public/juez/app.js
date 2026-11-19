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

const STORAGE_KEY = 'talkdrill-judge-state';

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
  // restaurar progreso previo del mismo juez
  const saved = JSON.parse(localStorage.getItem(`${STORAGE_KEY}-${state.judge}`) || 'null');
  if (saved) {
    state.index = Math.min(Math.max(0, saved.index | 0), state.rows.length - 1);
    state.verdicts = saved.verdicts || {};
    state.notes = saved.notes || {};
  }
  $('totalItems').textContent = state.rows.length;
  show('screen-welcome');
}

function saveLocal() {
  localStorage.setItem(`${STORAGE_KEY}-${state.judge}`, JSON.stringify({
    index: state.index, verdicts: state.verdicts, notes: state.notes,
  }));
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
  saveLocal();
  document.querySelectorAll('.verdict').forEach(b => b.classList.toggle('primary', b.dataset.v === v));
}

document.querySelectorAll('.verdict').forEach(b => {
  b.addEventListener('click', () => commitVerdict(b.dataset.v));
});
$('notes').addEventListener('input', e => {
  state.notes[current().key] = e.target.value;
  saveLocal();
});

$('btnStart').addEventListener('click', () => {
  show('screen-task');
  renderItem();
});
$('btnPrev').addEventListener('click', () => {
  if (state.index > 0) { state.index -= 1; saveLocal(); show('screen-task'); renderItem(); }
});
$('btnNext').addEventListener('click', () => {
  if (state.index < state.rows.length - 1) {
    state.index += 1; saveLocal(); show('screen-task'); renderItem();
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
    localStorage.removeItem(`${STORAGE_KEY}-${state.judge}`);
  } catch (err) {
    btn.disabled = false;
    $('sendStatus').textContent = 'No se pudo enviar. Intenta de nuevo o avísale al organizador.';
  }
});

init();
