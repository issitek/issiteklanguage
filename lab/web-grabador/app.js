/* talkdrill — grabador de frases (estático; los audios no salen del dispositivo) */
'use strict';

/* Frases: texto EXACTO de docs/fase0/guion-pronunciacion.md */
const PHRASES = [
  { id: 1,  text: "Good morning! How are you today?" },
  { id: 2,  text: "Thank you very much." },
  { id: 3,  text: "I think this is good." },
  { id: 4,  text: "Three thin things are there." },
  { id: 5,  text: "My mother and father are together." },
  { id: 6,  text: "I went to the third floor." },
  { id: 7,  text: "I usually go on the third of May." },
  { id: 8,  text: "This is the other one." },
  { id: 9,  text: "The weather is better in spring." },
  { id: 10, text: "There are three theaters in town." },
  { id: 11, text: "She thought about those things for a month." },
  { id: 12, text: "I see a sheep on the ship." },
  { id: 13, text: "Please sleep near the sink." },
  { id: 14, text: "He is living in a little house near the beach." },
  { id: 15, text: "Fit or feed, which do you need?" },
  { id: 16, text: "I swim in the sea every summer." },
  { id: 17, text: "The list of seats is little." },
  { id: 18, text: "Red roses grow in the garden." },
  { id: 19, text: "Rice is delicious with ripe tomatoes." },
  { id: 20, text: "My brother runs every morning on the river road." },
  { id: 21, text: "The price of fresh fruit is really high." },
  { id: 22, text: "She sells fresh fish and chips." },
  { id: 23, text: "I watch TV on Sundays and shop on Friday." },
  { id: 24, text: "Chicken, cheese and churros, please!" },
  { id: 25, text: "The teacher teaches touch in class." },
  { id: 26, text: "I bought a very cheap phone with cash." },
  { id: 27, text: "She lives in a big apartment near the beach." },
  { id: 28, text: "I drink tea every day at seven." },
  { id: 29, text: "I would like a chicken sandwich and a drink." },
  { id: 30, text: "These three things are for them." },
];

const TARGET_RATE = 16000;
const $ = (id) => document.getElementById(id);
const screens = ['screen-welcome', 'screen-record', 'screen-done'];
const show = (id) => { for (const s of screens) $(s).classList.toggle('active', s === id); };

/* Código de participante autogenerado (sin nombres, no se teclea) */
const CODE_ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'; // sin 0/o/1/l
function genCode() {
  try {
    const rand = new Uint32Array(6);
    crypto.getRandomValues(rand);
    let code = 's';
    for (const r of rand) code += CODE_ALPHABET[r % CODE_ALPHABET.length];
    return code;
  } catch {
    // WebCrypto no disponible (contexto no seguro): Math.random basta para un id opaco
    let code = 's';
    for (let i = 0; i < 6; i++) code += CODE_ALPHABET[Math.floor(Math.random() * CODE_ALPHABET.length)];
    return code;
  }
}

const state = {
  code: genCode(),
  index: 0,
  items: new Map(),   // phraseId -> Uint8Array WAV
  recording: false,
  chunks: [],
  audioCtx: null,
  stream: null,
  processor: null,
  source: null,
  startedAt: 0,
  timerInt: null,
};

/* ============ Pantalla 1: requisito de consentimiento ============ */
const consentBox = $('consent');
const startBtn = $('btnStart');

$('autoCode').textContent = state.code;
$('btnCopyCode').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(state.code);
    $('btnCopyCode').textContent = '¡Copiado!';
    setTimeout(() => { $('btnCopyCode').textContent = 'Copiar código'; }, 1500);
  } catch { $('btnCopyCode').textContent = state.code; }
});

const refreshStart = () => { startBtn.disabled = !consentBox.checked; };
consentBox.addEventListener('change', refreshStart);
refreshStart();

startBtn.addEventListener('click', () => {
  state.index = 0;
  show('screen-record');
  loadPhrase();
});

/* ============ Pantalla 2: grabación ============ */
function loadPhrase() {
  const p = PHRASES[state.index];
  $('progressLabel').textContent = `Frase ${p.id} / ${PHRASES.length}`;
  $('progressFill').style.width = `${(state.index / PHRASES.length) * 100}%`;
  $('phraseText').textContent = p.text;
  $('recState').textContent = 'listo';
  $('recTimer').textContent = '—';
  updateButtons();
}

function hasAudio() { return state.items.has(PHRASES[state.index].id); }

function updateButtons() {
  const has = hasAudio();
  const rec = state.recording;
  $('btnRecord').textContent = rec ? '⏹ Detener' : '🎙 Grabar';
  $('btnRecord').classList.toggle('recording', rec);
  $('btnPlay').disabled = !has || rec;
  $('btnRetry').disabled = !has || rec;
  $('btnNext').disabled = !has || rec;
}

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('Este navegador no permite acceso al micrófono (¿archivo abierto con file://? usa GitHub Pages o localhost).');
    return;
  }
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
    });
  } catch (err) {
    alert('No se pudo abrir el micrófono. Permiso denegado o dispositivo ausente.');
    return;
  }
  try {
    state.audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: TARGET_RATE });
  } catch {
    state.audioCtx = new (window.AudioContext || window.webkitAudioContext)(); // nativa; remuestreamos al cerrar
  }
  state.chunks = [];
  state.source = state.audioCtx.createMediaStreamSource(state.stream);
  state.processor = state.audioCtx.createScriptProcessor(4096, 1, 1);
  state.processor.onaudioprocess = (e) => {
    state.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  };
  state.source.connect(state.processor);
  state.processor.connect(state.audioCtx.destination);
  state.recording = true;
  state.startedAt = performance.now();
  $('recState').textContent = '● grabando';
  clearInterval(state.timerInt);
  state.timerInt = setInterval(() => {
    const s = Math.floor((performance.now() - state.startedAt) / 1000);
    $('recTimer').textContent = `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  }, 250);
  updateButtons();
}

function stopRecording() {
  clearInterval(state.timerInt);
  state.processor?.disconnect();
  state.source?.disconnect();
  state.stream?.getTracks().forEach((t) => t.stop());
  const inRate = state.audioCtx.sampleRate;
  state.audioCtx?.close();
  // concatenar
  let total = 0;
  for (const c of state.chunks) total += c.length;
  const merged = new Float32Array(total);
  let off = 0;
  for (const c of state.chunks) { merged.set(c, off); off += c.length; }
  // downsample lineal si el navegador no honró los 16 kHz
  const pcm16 = window.TalkCodec.downsampleLinear(merged, inRate, TARGET_RATE);
  const wav = window.TalkCodec.wavBytes(pcm16, TARGET_RATE);
  state.items.set(PHRASES[state.index].id, wav);
  state.recording = false;
  state.chunks = [];
  $('recState').textContent = 'grabado ✓';
  updateButtons();
}

$('btnRecord').addEventListener('click', () => {
  if (state.recording) stopRecording();
  else startRecording();
});

$('btnRetry').addEventListener('click', () => {
  const id = PHRASES[state.index].id;
  state.items.delete(id);
  updateButtons();
  $('recState').textContent = 'listo (audio descartado)';
});

$('btnPlay').addEventListener('click', () => {
  const wav = state.items.get(PHRASES[state.index].id);
  if (!wav) return;
  const url = URL.createObjectURL(new Blob([wav], { type: 'audio/wav' }));
  const audio = $('playback');
  audio.src = url;
  audio.play();
});

$('btnNext').addEventListener('click', () => {
  if (state.index + 1 < PHRASES.length) {
    state.index += 1;
    loadPhrase();
  } else {
    $('progressFill').style.width = '100%';
    $('doneCode').textContent = state.code;
    show('screen-done');
  }
});

window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && $('screen-record').classList.contains('active')
      && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
    e.preventDefault();
    $('btnRecord').click();
  }
});

/* ============ Pantalla 3: exportación ============ */
function entriesFor(code, items) {
  return [...items.entries()].map(([id, wav]) => ({
    name: `${code}/${String(id).padStart(2, '0')}.wav`,
    data: wav,
  }));
}

$('btnZip').addEventListener('click', () => {
  const zip = window.TalkCodec.zipBuild(entriesFor(state.code, state.items));
  const blob = new Blob([zip], { type: 'application/zip' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${state.code}.zip`;
  a.click();
  URL.revokeObjectURL(a.href);
});

$('btnLoose').addEventListener('click', async () => {
  for (const [id, wav] of state.items) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([wav], { type: 'audio/wav' }));
    a.download = `${String(id).padStart(2, '0')}.wav`;
    a.click();
    await new Promise((r) => setTimeout(r, 120));
  }
});

const btnSaveDir = $('btnSaveDir');
if (window.showDirectoryPicker) {
  btnSaveDir.hidden = false;
  btnSaveDir.addEventListener('click', async () => {
    try {
      const parent = await window.showDirectoryPicker({ mode: 'readwrite' });
      const dir = await parent.getDirectoryHandle(state.code, { create: true });
      for (const [id, wav] of state.items) {
        const name = `${String(id).padStart(2, '0')}.wav`;
        const fh = await dir.getFileHandle(name, { create: true });
        const w = await fh.createWritable();
        await w.write(wav);
        await w.close();
      }
      btnSaveDir.textContent = '✅ Guardado en la carpeta';
      btnSaveDir.disabled = true;
    } catch (err) {
      if (err.name !== 'AbortError') alert('No se pudo guardar en la carpeta: ' + err.message);
    }
  });
}

/* ============ Envío directo al organizador (mismo origen) ============ */
const UPLOAD_URL = '/upload';
const sendStatus = $('sendStatus');

$('btnSendEmail').addEventListener('click', async () => {
  const btn = $('btnSendEmail');
  btn.disabled = true;
  sendStatus.className = 'send-status info';
  sendStatus.textContent = 'Preparando y enviando…';
  try {
    const zip = window.TalkCodec.zipBuild(entriesFor(state.code, state.items));
    // el receptor espera binario ZIP + código en cabecera, no multipart
    const r = await fetch(UPLOAD_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/zip',
        'X-Participant-Code': state.code,
      },
      body: zip,
    });
    const txt = await r.text();
    let ok = r.ok;
    try { ok = JSON.parse(txt)?.ok === true; } catch { /* texto plano, r.ok manda */ }
    if (!ok) throw new Error(`servidor respondió ${r.status}: ${txt.slice(0, 120)}`);
    sendStatus.className = 'send-status ok';
    sendStatus.textContent = '✅ ¡Recibido! Muchas gracias.';
    btn.textContent = '✔ Enviado';
  } catch (err) {
    console.warn('envío directo falló:', err);
    sendStatus.className = 'send-status err';
    sendStatus.textContent = 'No se pudo enviar. Usa «Descargar ZIP» y envíalo como archivo.';
    btn.disabled = false;
  }
});
