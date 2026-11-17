/* talkdrill — grabador: codificadores puros (WAV + ZIP store-only).
   Sin dependencias. Usable en navegador (window.TalkCodec) y en node (require). */
'use strict';

const TalkCodec = (() => {
  /* ---------- WAV PCM s16 mono ---------- */
  function pcmFromFloat(float32Array) {
    const out = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return out;
  }

  function downsampleLinear(float32Array, fromRate, toRate) {
    if (fromRate === toRate) return float32Array;
    const ratio = fromRate / toRate;
    const outLen = Math.floor(float32Array.length / ratio);
    const out = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const src = i * ratio;
      const idx = Math.floor(src);
      const frac = src - idx;
      const a = float32Array[idx] || 0;
      const b = float32Array[idx + 1] !== undefined ? float32Array[idx + 1] : a;
      out[i] = a + (b - a) * frac;
    }
    return out;
  }

  function wavBytes(float32Array, sampleRate) {
    const pcm = pcmFromFloat(float32Array);
    const dataSize = pcm.byteLength;
    const buf = new ArrayBuffer(44 + dataSize);
    const dv = new DataView(buf);
    const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(off + i, s.charCodeAt(i)); };
    writeStr(0, 'RIFF');
    dv.setUint32(4, 36 + dataSize, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); // PCM
    dv.setUint16(22, 1, true); // mono
    dv.setUint32(24, sampleRate, true);
    dv.setUint32(28, sampleRate * 2, true);
    dv.setUint16(32, 2, true);
    dv.setUint16(34, 16, true);
    writeStr(36, 'data');
    dv.setUint32(40, dataSize, true);
    new Uint8Array(buf, 44).set(new Uint8Array(pcm.buffer));
    return new Uint8Array(buf);
  }

  /* ---------- CRC32 (tabla) ---------- */
  const CRC_TABLE = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c >>> 0;
    }
    return t;
  })();

  function crc32(bytes) {
    let c = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }

  const u16 = (v) => new Uint8Array([v & 0xff, (v >>> 8) & 0xff]);
  const u32 = (v) => new Uint8Array([v & 0xff, (v >>> 8) & 0xff, (v >>> 16) & 0xff, (v >>> 24) & 0xff]);
  const dosTime = (d) => (((d.getHours() & 0x1f) << 11) | ((d.getMinutes() & 0x3f) << 5) | ((d.getSeconds() / 2) & 0x1f));
  const dosDate = (d) => ((((d.getFullYear() - 1980) & 0x7f) << 9) | (((d.getMonth() + 1) & 0x0f) << 5) | (d.getDate() & 0x1f));

  /* ---------- ZIP store-only (sin compresión; WAV no comprime) ---------- */
  function zipBuild(entries) { // entries: [{name: string (relative, forward slashes), data: Uint8Array}]
    const enc = new TextEncoder();
    const chunks = [];
    const central = [];
    let offset = 0;
    const now = new Date();
    const time = dosTime(now), date = dosDate(now);
    for (const e of entries) {
      const nameB = enc.encode(e.name);
      const crc = crc32(e.data);
      const size = e.data.length;
      const local = new Uint8Array(30 + nameB.length);
      local.set([0x50, 0x4b, 0x03, 0x04], 0);
      local.set(u16(20), 4);
      local.set(u16(0x0800), 6); // UTF-8
      local.set(u16(0), 8); // método: store
      local.set(u16(time), 10);
      local.set(u16(date), 12);
      local.set(u32(crc), 14);
      local.set(u32(size), 18);
      local.set(u32(size), 22);
      local.set(u16(nameB.length), 26);
      local.set(u16(0), 28);
      local.set(nameB, 30);
      chunks.push(local, e.data);
      const cdir = new Uint8Array(46 + nameB.length);
      cdir.set([0x50, 0x4b, 0x01, 0x02], 0);
      cdir.set(u16(20), 4);   // version made by
      cdir.set(u16(20), 6);   // version needed
      cdir.set(u16(0x0800), 8);
      cdir.set(u16(0), 10);
      cdir.set(u16(time), 12);
      cdir.set(u16(date), 14);
      cdir.set(u32(crc), 16);
      cdir.set(u32(size), 20);
      cdir.set(u32(size), 24);
      cdir.set(u16(nameB.length), 28);
      cdir.set(u32(0), 30);   // extra, comment len, disk, attrs
      cdir.set(u32(0), 34);
      cdir.set(u32(0), 38);
      cdir.set(u32(offset), 42);
      cdir.set(nameB, 46);
      central.push(cdir);
      offset += local.length + e.data.length;
    }
    const cSize = central.reduce((a, c) => a + c.length, 0);
    const end = new Uint8Array(22);
    end.set([0x50, 0x4b, 0x05, 0x06], 0);
    end.set(u16(central.length), 8);
    end.set(u16(central.length), 10);
    end.set(u32(cSize), 12);
    end.set(u32(offset), 16);
    end.set(u16(0), 20);
    const all = [...chunks, ...central, end];
    const total = all.reduce((a, c) => a + c.length, 0);
    const out = new Uint8Array(total);
    let p = 0;
    for (const c of all) { out.set(c, p); p += c.length; }
    return out;
  }

  return { pcmFromFloat, downsampleLinear, wavBytes, crc32, zipBuild };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = TalkCodec;
if (typeof window !== 'undefined') window.TalkCodec = TalkCodec;
