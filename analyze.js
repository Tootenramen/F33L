/* F33L analyze.js: builds the beat-similarity jump graph in the browser (or Node). A port of src/jukebox.py.
   Input: mono Float32Array at 22050 Hz. Output: {bpm, beats, nodes[{i,t,arousal,brightness}], edges[{a,b,d}]}.
   Ideas from the MIT-licensed Infinite/Eternal Jukebox; implementation is ours. No network, no audio leaves the page. */
(function (root) {
  const SR = 22050, N_FFT = 2048, HOP = 512, BINS = N_FFT / 2 + 1;

  // in-place iterative radix-2 FFT
  const REV = new Uint16Array(N_FFT), COS = new Float32Array(N_FFT / 2), SIN = new Float32Array(N_FFT / 2);
  (function init() {
    for (let i = 0; i < N_FFT; i++) { let r = 0, x = i; for (let b = 0; b < 11; b++) { r = (r << 1) | (x & 1); x >>= 1; } REV[i] = r; }
    for (let i = 0; i < N_FFT / 2; i++) { COS[i] = Math.cos(2 * Math.PI * i / N_FFT); SIN[i] = -Math.sin(2 * Math.PI * i / N_FFT); }
  })();
  function fft(re, im) {
    for (let i = 0; i < N_FFT; i++) { const j = REV[i]; if (j > i) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; } }
    for (let size = 2; size <= N_FFT; size <<= 1) {
      const half = size >> 1, step = N_FFT / size;
      for (let s = 0; s < N_FFT; s += size) for (let k = 0, w = 0; k < half; k++, w += step) {
        const a = s + k, b = a + half, tr = re[b] * COS[w] - im[b] * SIN[w], ti = re[b] * SIN[w] + im[b] * COS[w];
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
      }
    }
  }
  const WIN = new Float32Array(N_FFT); for (let i = 0; i < N_FFT; i++) WIN[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N_FFT);

  const tick = () => new Promise(r => setTimeout(r, 0));
  async function stftMag(y, onProgress) {
    const frames = 1 + Math.floor((y.length - N_FFT) / HOP), mag = new Float32Array(frames * BINS);
    const re = new Float32Array(N_FFT), im = new Float32Array(N_FFT);
    for (let f = 0; f < frames; f++) {
      const o = f * HOP;
      for (let i = 0; i < N_FFT; i++) { re[i] = y[o + i] * WIN[i]; im[i] = 0; }
      fft(re, im);
      const m = f * BINS; for (let k = 0; k < BINS; k++) mag[m + k] = Math.hypot(re[k], im[k]);
      if (onProgress && f % 400 === 0) { onProgress(f / frames); await tick(); }
    }
    return { mag, frames };
  }

  const percentile = (arr, p) => { const a = Float64Array.from(arr).sort(); const x = (a.length - 1) * p / 100, lo = Math.floor(x), hi = Math.ceil(x); return a[lo] + (a[hi] - a[lo]) * (x - lo); };

  function tempo(flux, fps) {
    const n = flux.length; let mean = 0; for (let i = 0; i < n; i++) mean += flux[i]; mean /= n;
    const f = Float64Array.from(flux, v => v - mean), lo = Math.floor(fps * 60 / 180), hi = Math.floor(fps * 60 / 60);
    let best = -Infinity, lag = lo;
    for (let L = lo; L < hi; L++) { let s = 0; for (let i = 0; i + L < n; i++) s += f[i] * f[i + L]; if (s > best) { best = s; lag = L; } }
    return 60 * fps / lag;
  }

  function beatGrid(flux, fps, bpm) {
    const period = fps * 60 / bpm, n = flux.length; let bestPh = 0, bestS = -1;
    for (let ph = 0; ph < period; ph += 1) { let s = 0; for (let p = ph; Math.round(p) < n; p += period) s += flux[Math.round(p)]; if (s > bestS) { bestS = s; bestPh = ph; } }
    const out = []; for (let p = bestPh; Math.round(p) < n; p += period) out.push(Math.round(p) / fps); return out;
  }

  async function build(y, opts = {}) {
    const onProgress = opts.onProgress || (() => {}), threshold = opts.threshold ?? 0.35, topk = opts.topk ?? 4, bar = 4, minGap = 8;
    const fps = SR / HOP, { mag, frames } = await stftMag(y, p => onProgress(p * 0.8));
    const freqs = new Float32Array(BINS); for (let k = 0; k < BINS; k++) freqs[k] = k * SR / N_FFT;
    const db = new Float64Array(frames), cent = new Float64Array(frames), flux = new Float64Array(frames);
    for (let f = 0; f < frames; f++) {
      let e = 0, sm = 0, wsum = 0; const m = f * BINS;
      for (let k = 0; k < BINS; k++) { const v = mag[m + k]; e += v * v; sm += v; wsum += v * freqs[k]; }
      db[f] = 20 * Math.log10(Math.sqrt(e / BINS) + 1e-9); cent[f] = wsum / (sm + 1e-9);
      if (f > 0) { let fl = 0; const p = m - BINS; for (let k = 0; k < BINS; k++) { const d = mag[m + k] - mag[p + k]; if (d > 0) fl += d; } flux[f] = fl; }
    }
    let bpm = opts.bpm || tempo(flux, fps); while (bpm < 70) bpm *= 2; while (bpm > 160) bpm /= 2;
    const beats = beatGrid(flux, fps, bpm), nB = beats.length, dur = y.length / SR;
    // chroma + 12 log bands per frame
    const pc = new Int8Array(BINS).fill(-1); for (let k = 0; k < BINS; k++) { const f = freqs[k]; if (f >= 55 && f <= 2000) pc[k] = ((Math.round(12 * Math.log2(f / 440) + 69) % 12) + 12) % 12; }
    const edgesHz = []; for (let i = 0; i < 13; i++) edgesHz.push(60 * Math.pow(9000 / 60, i / 12));
    const bandOf = new Int8Array(BINS).fill(-1); for (let k = 0; k < BINS; k++) for (let b = 0; b < 12; b++) if (freqs[k] >= edgesHz[b] && freqs[k] < edgesHz[b + 1]) { bandOf[k] = b; break; }
    const C = [], T = [], D = new Float64Array(nB), CE = new Float64Array(nB);
    for (let i = 0; i < nB; i++) {
      const a = Math.floor(beats[i] * fps), b = Math.max(Math.floor((i + 1 < nB ? beats[i + 1] : dur) * fps), a + 1), cnt = Math.min(b, frames) - a;
      const ch = new Float64Array(12), tm = new Float64Array(12); let d = 0, c = 0;
      for (let f = a; f < Math.min(b, frames); f++) {
        const m = f * BINS, cf = new Float64Array(12), bf = new Float64Array(12);
        for (let k = 0; k < BINS; k++) { const v = mag[m + k]; if (pc[k] >= 0) cf[pc[k]] += v; if (bandOf[k] >= 0) bf[bandOf[k]] += v; }
        for (let j = 0; j < 12; j++) { ch[j] += cf[j]; tm[j] += Math.log1p(bf[j]); } d += db[f]; c += cent[f];
      }
      const n = Math.max(cnt, 1); let cs = 0, tmean = 0; for (let j = 0; j < 12; j++) { ch[j] /= n; tm[j] /= n; cs += ch[j]; tmean += tm[j]; }
      tmean /= 12; for (let j = 0; j < 12; j++) { ch[j] /= (cs + 1e-9); tm[j] -= tmean; }
      C.push(ch); T.push(tm); D[i] = d / n; CE[i] = c / n; onProgress(0.8 + 0.1 * i / nB);
    }
    const unit = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) + 1e-9; return v.map(x => x / s); };
    const Tu = T.map(unit), Cu = C.map(unit);
    let dm = 0; for (const x of D) dm += x; dm /= nB; let dv = 0; for (const x of D) dv += (x - dm) ** 2; const dsd = Math.sqrt(dv / nB) + 1e-9;
    const Dn = Array.from(D, x => (x - dm) / dsd), dot = (u, v) => { let s = 0; for (let j = 0; j < 12; j++) s += u[j] * v[j]; return s; };
    const dist = new Float32Array(nB * nB), all = [];
    for (let i = 0; i < nB; i++) for (let j = 0; j < nB; j++) {
      if (i === j) { dist[i * nB + j] = 9; continue; }
      const v = 0.5 * (1 - dot(Tu[i], Tu[j])) + 0.3 * (1 - dot(Cu[i], Cu[j])) + 0.2 * Math.abs(Dn[i] - Dn[j]) / 4 + ((i % bar) !== (j % bar) ? 0.15 : 0);
      dist[i * nB + j] = v; all.push(v);
    }
    const cut = Math.min(threshold, percentile(all, 3)), edges = [];
    for (let i = 0; i < nB; i++) {
      const order = Array.from({ length: nB }, (_, j) => j).sort((p, q) => dist[i * nB + p] - dist[i * nB + q]); let kept = 0;
      for (const j of order) { const d = dist[i * nB + j]; if (d >= cut || kept >= topk) break; if (Math.abs(j - i) >= minGap && j !== i + 1) { edges.push({ a: i, b: j, d: +d.toFixed(3) }); kept++; } }
    }
    const d10 = percentile(D, 10), d90 = percentile(D, 90), c10 = percentile(CE, 10), c90 = percentile(CE, 90), clip = x => Math.max(0, Math.min(1, x));
    const nodes = beats.map((t, i) => ({ i, t: +t.toFixed(3), arousal: +clip((D[i] - d10) / (d90 - d10 + 1e-9)).toFixed(2), brightness: +clip((CE[i] - c10) / (c90 - c10 + 1e-9)).toFixed(2) }));
    onProgress(1);
    return { bpm: +bpm.toFixed(1), beats: nB, nodes, edges };
  }

  const api = { SR, build, stftMag, tempo, beatGrid };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.F33LAnalyze = api;
})(typeof self !== 'undefined' ? self : this);
