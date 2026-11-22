/* talkdrill — etiquetado por jueces (juez1 / juez2) */
'use strict';

const state = {
  rows: [],        // lista de evaluaciones (de sheet.json)
  index: 0,
  verdicts: {},    // key → verdict string
  notes: {},       // key → nota
  judge: null,
  blind: false,
  seq: 0,          // marca monotónica de guardado (server-side ordering)
};

const $ = (id) => document.getElementById(id);
const show = (id) => {
  document.querySelectorAll('.screen').forEach(s => s.classList.toggle('active', s.id === id));
};

function clampIndex(i) {
  return Math.min(Math.max(0, i | 0), Math.max(0, state.rows.length - 1));
}

function notice(text, color) {
  const card = document.querySelector('#screen-welcome .card');
  if (!card) return;
  let el = $('serverNotice');
  if (!el) {
    el = document.createElement('p');
    el.id = 'serverNotice';
    el.className = 'small';
    el.style.fontWeight = '600';
    card.appendChild(el);
  }
  el.style.color = color || '#9fe8b0';
  el.textContent = text;
}

/* Indicador visible de guardado (abajo a la derecha) */
function setSaveStatus(text, color) {
  let el = $('saveStatus');
  if (!el) {
    el = document.createElement('div');
    el.id = 'saveStatus';
    el.style.cssText = 'position:fixed;right:8px;bottom:8px;z-index:99;font:600 11px/1.3 system-ui,sans-serif;' +
      'padding:4px 8px;border-radius:8px;background:#0b1220cc;border:1px solid #2b3654;pointer-events:none;';
    document.body.appendChild(el);
  }
  el.style.color = color || '#9fe8b0';
  el.textContent = text;
}

/* Progreso guardado por versiones anteriores en este navegador (migración) */
function localBackup(judge) {
  try {
    const raw = localStorage.getItem(`talkdrill-judge-state-${judge}`);
    if (!raw) return null;
    const d = JSON.parse(raw);
    if (d && (Number(d.index) > 0 || Object.keys(d.verdicts || {}).length > 0)) return d;
  } catch (e) { /* ignora */ }
  return null;
}

async function postProgress(payload) {
  const r = await fetch('/juez/progress', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
    keepalive: true,
    cache: 'no-store',
  });
  if (r.status === 401) {
    notice('⚠ Sesión no autenticada: cierra y vuelve a abrir el enlace (o recarga con Ctrl+F5).', '#ffb4b4');
    setSaveStatus('sin sesión', '#ffb4b4');
    throw new Error('401');
  }
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json().catch(() => ({}));
}

function applyServerState(s) {
  if (!s) return;
  state.index = clampIndex(s.index | 0);
  state.verdicts = s.verdicts || state.verdicts;
  state.notes = s.notes || state.notes;
  state.seq = s.seq || state.seq;
}

function renderCurrentIfVisible() {
  const task = document.getElementById('screen-task');
  if (task && task.classList.contains('active') && state.rows.length) renderItem();
}

/* Guardados serializados: nunca llegan desordenados al servidor */
let saveChain = Promise.resolve();
function saveProgress() {
  if (!state.judge) return;
  const seq = (state.seq || 0) + 1;  // avanza desde el seq del servidor
  state.seq = seq;
  const payload = {index: state.index, verdicts: state.verdicts, notes: state.notes, seq};
  setSaveStatus('guardando…', '#ffd479');
  saveChain = saveChain.then(async () => {
    try {
      const d = await postProgress(payload);
      if (d.applied === false && d.server) {
        // otro dispositivo guardó después: gana el más reciente, no pisamos con datos viejos
        applyServerState(d.server);
        notice('↩ Otro dispositivo avanzó: se cargó el avance más reciente del servidor.', '#ffd479');
        renderCurrentIfVisible();
        setSaveStatus('avance del servidor cargado', '#ffd479');
        return;
      }
      const t = new Date().toLocaleTimeString();
      setSaveStatus(`guardado ✓ ${t}`);
    } catch (e) {
      if (String(e && e.message) !== '401') setSaveStatus('no se pudo guardar', '#ffb4b4');
    }
  });
}
function queueSave() { saveProgress(); }  // guardado inmediato, sin retardo
// Red de seguridad: si el navegador se cierra/va a segundo plano, vuelve a enviar
window.addEventListener('pagehide', saveProgress);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') saveProgress(); });
// Si el navegador restaura la página desde la caché de atrás/adelante, el JS no se
// vuelve a ejecutar: releer el avance del servidor para no mostrar estado viejo.
window.addEventListener('pageshow', async (e) => {
  if (!e.persisted || !state.judge) return;
  try {
    const r = await fetch('/juez/progress', {cache: 'no-store'});
    if (!r.ok) return;
    const s = await r.json();
    applyServerState(s);
    renderCurrentIfVisible();
    if (state.index > 0) {
      notice(`↩ Avance actualizado del servidor: evaluación ${state.index + 1} de ${state.rows.length}.`);
    }
  } catch (err) { /* ignora */ }
});

async function init() {
  try {
    const r = await fetch('/juez/role', {cache: 'no-store'});
    if (r.status === 401) throw new Error('sin autenticación');
    const d = await r.json();
    state.judge = d.judge;
    state.blind = !!d.blind;
  } catch {
    alert('No se pudo identificar tu sesión. Cierra y vuelve a abrir el enlace.');
    return;
  }
  $('judgeTag').textContent = state.judge ? state.judge.toUpperCase() : 'JUEZ';
  if (state.blind) {
    document.body.classList.add('blind');
    document.title = 'talkdrill — adjudicación ciega';
    const h1 = document.querySelector('#screen-welcome h1');
    if (h1) h1.innerHTML = 'talkdrill — adjudicación <span class="judgetag" id="judgeTag">JUEZ3</span>';
    const bn = $('blindNotice');
    if (bn) bn.hidden = false;
  }
  const sheet = await fetch('/juez/sheet.json', {cache: 'no-store'}).then(r => r.json());
  state.rows = sheet.map(r => ({ ...r, key: `${r.file}:${r.word}` }));

  // ---- restaurar progreso del servidor (SQLite) — sin importar el dispositivo ----
  let saved = null;
  try {
    const resp = await fetch('/juez/progress', {cache: 'no-store'});
    if (resp.status === 401) {
      notice('⚠ No pude leer tu avance: la sesión no está autenticada. Recarga con Ctrl+F5 o vuelve a abrir el enlace.', '#ffb4b4');
    } else if (resp.ok) {
      saved = await resp.json();
    }
  } catch (e) {
    notice('⚠ No pude leer tu avance del servidor (red). Al moverte se reintentará el guardado.', '#ffd479');
  }
  if (saved) {
    state.index = clampIndex(saved.index | 0);
    state.verdicts = saved.verdicts || {};
    state.notes = saved.notes || {};
    state.seq = saved.seq || 0;
  }

  // ---- migración desde versiones anteriores: fusiona (sin pisar) lo que haya en este navegador ----
  let imported = 0;
  const local = localBackup(state.judge);
  if (local) {
    for (const [k, v] of Object.entries(local.verdicts || {})) {
      if (!state.verdicts[k]) { state.verdicts[k] = v; imported += 1; }
    }
    for (const [k, v] of Object.entries(local.notes || {})) {
      if (!state.notes[k]) state.notes[k] = v;
    }
    const localIndex = clampIndex(local.index | 0);
    const advanced = localIndex > state.index;
    if (advanced) state.index = localIndex;
    if (imported > 0 || advanced) {
      saveProgress();  // sube al servidor el avance del navegador
    }
  }

  if (state.index > 0) {
    const extra = imported > 0 ? ` (${imported} veredictos recuperados de este navegador)` : '';
    notice(`↩ Avance recuperado: evaluación ${state.index + 1} de ${state.rows.length}${extra}.`);
  }
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
    // cerrar la sesión también en el servidor (con un seq estrictamente mayor al actual)
    try {
      const srv = await fetch('/juez/progress', {cache: 'no-store'}).then(r => r.ok ? r.json() : null).catch(() => null);
      state.seq = Math.max(state.seq || 0, (srv && srv.seq) || 0) + 1;
      await postProgress({index: 0, verdicts: {}, notes: {}, seq: state.seq});
    } catch (e) { /* el envío ya se hizo; el organizador puede reiniciar */ }
    state.verdicts = {};
    state.notes = {};
    try { localStorage.removeItem(`talkdrill-judge-state-${state.judge}`); } catch (e) { /* ignora */ }
  } catch (err) {
    btn.disabled = false;
    $('sendStatus').textContent = 'No se pudo enviar. Intenta de nuevo o avísale al organizador.';
  }
});

init();
