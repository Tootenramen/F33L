/* F33L analyze.js v2: builds the beat-similarity jump graph in the browser (or Node).
   Input: mono Float32Array at 22050 Hz. Output: {bpm, beats, duration, nodes[{i,t,arousal,brightness}], edges[{a,b,d,s}]}.
   An edge a->b means: after playing beat a, continue with beat b (b is the beat AFTER a beat that sounds like a, so the
   music keeps flowing). Ideas from the MIT-licensed Infinite/Eternal Jukebox; the implementation is ours.
   v2 changes: dynamic-programming beat tracking that follows real onsets, cuts snapped to transients, and a direct
   "splice smoothness" cost (how different the sound just before the cut is from the sound just after it). */
(function (root) {
  const SR = 22050, N_FFT = 2048, HOP = 512, BINS = N_FFT / 2 + 1, MEL = 24, FINE = 128;

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

  const percentile = (arr, p) => { const a = Float64Array.from(arr).sort(); if (!a.length) return 0; const x = (a.length - 1) * p / 100, lo = Math.floor(x), hi = Math.ceil(x); return a[lo] + (a[hi] - a[lo]) * (x - lo); };
  const frameCenter = f => (f * HOP + N_FFT / 2) / SR;
  const timeToFrame = t => Math.max(0, Math.round((t * SR - N_FFT / 2) / HOP));

  // tempo from the onset envelope: autocorrelation with a weak preference for common tempos
  function tempo(flux, fps) {
    const n = flux.length; let mean = 0; for (let i = 0; i < n; i++) mean += flux[i]; mean /= n;
    const f = Float64Array.from(flux, v => v - mean), lo = Math.floor(fps * 60 / 180), hi = Math.floor(fps * 60 / 60);
    let best = -Infinity, lag = lo;
    for (let L = lo; L < hi; L++) {
      let s = 0; for (let i = 0; i + L < n; i++) s += f[i] * f[i + L];
      const bpm = 60 * fps / L, prior = Math.exp(-0.5 * Math.pow(Math.log2(bpm / 110) / 0.9, 2));
      s *= prior; if (s > best) { best = s; lag = L; }
    }
    return 60 * fps / lag;
  }

  // Ellis-style dynamic-programming beat tracker: beats land on onsets but stay near the tempo
  function trackBeats(flux, fps, bpm, tight = 100) {
    const n = flux.length; let m = 0, v = 0; for (const x of flux) m += x; m /= n; for (const x of flux) v += (x - m) ** 2;
    const sd = Math.sqrt(v / n) + 1e-9, o = new Float64Array(n);
    for (let i = 0; i < n; i++) o[i] = ((flux[Math.max(0, i - 1)] + 2 * flux[i] + flux[Math.min(n - 1, i + 1)]) / 4) / sd;
    const P = fps * 60 / bpm, kmin = Math.max(1, Math.round(P / 2)), kmax = Math.round(P * 2);
    const score = new Float64Array(n), prev = new Int32Array(n).fill(-1);
    for (let t = 0; t < n; t++) {
      let best = 0, from = -1;
      for (let k = kmin; k <= kmax && t - k >= 0; k++) { const s = score[t - k] - tight * Math.pow(Math.log(k / P), 2); if (s > best) { best = s; from = t - k; } }
      score[t] = o[t] + best; prev[t] = from;
    }
    let end = n - 1, bs = -Infinity; for (let t = Math.max(0, n - Math.round(2 * P)); t < n; t++) if (score[t] > bs) { bs = score[t]; end = t; }
    const out = []; for (let t = end; t >= 0; t = prev[t]) { out.push(t); if (prev[t] < 0) break; } return out.reverse();
  }

  // move each beat time onto the nearest transient so cuts do not land in the middle of a sound
  function snapToOnsets(y, times) {
    const K = Math.floor(y.length / FINE), logE = new Float32Array(K);
    for (let k = 0; k < K; k++) { let e = 0; for (let i = k * FINE; i < (k + 1) * FINE; i++) e += y[i] * y[i]; logE[k] = Math.log(e + 1e-9); }
    const on = new Float32Array(K); for (let k = 1; k < K; k++) on[k] = Math.max(0, logE[k] - logE[k - 1]);
    const win = Math.round(0.06 * SR / FINE), out = [];
    for (const t of times) {
      const c = Math.round(t * SR / FINE); let bk = c, bv = 0;
      for (let k = Math.max(1, c - win); k <= Math.min(K - 1, c + win); k++) if (on[k] > bv) { bv = on[k]; bk = k; }
      out.push((bv > 0.6 ? bk * FINE : c * FINE) / SR);
    }
    for (let i = 1; i < out.length; i++) if (out[i] <= out[i - 1] + 0.05) out[i] = out[i - 1] + 0.05; // stay increasing
    return out;
  }

  // features describing a cut: how the sound just before it (tail) differs from the sound just after it (head)
  function pairFeatures(t, h, dbT, dbH) {
    const v = []; for (let j = 0; j < t.length; j++) v.push(Math.abs(t[j] - h[j]));
    v.push(Math.abs(dbT - dbH), dbH - dbT, dbT, dbH, Math.max(0, dbH - dbT));
    for (let j = 0; j < t.length; j++) v.push(h[j] - t[j]);   // signed, so the model knows the direction of the change
    return v;
  }
  function modelScore(M, x) { let z = M.b; for (let j = 0; j < x.length; j++) z += ((x[j] - M.mu[j]) / M.sd[j]) * M.w[j]; return z; } // higher = more likely a break
  async function build(y, opts = {}) {
    const MODEL = opts.model || null;   // pass the continuity model explicitly (window.F33LModel / require('./continuity_model.js')) to use learned cut scoring
    const onProgress = opts.onProgress || (() => {}), topk = opts.topk ?? 4, bar = 4, minGap = opts.minGap ?? 8;
    const maxRatio = opts.maxRatio ?? 1.7, fps = SR / HOP;
    const { mag, frames } = await stftMag(y, p => onProgress(p * 0.7));
    const freqs = new Float32Array(BINS); for (let k = 0; k < BINS; k++) freqs[k] = k * SR / N_FFT;
    const mEdges = []; for (let i = 0; i <= MEL; i++) mEdges.push(50 * Math.pow(10000 / 50, i / MEL));
    const melOf = new Int8Array(BINS).fill(-1), pc = new Int8Array(BINS).fill(-1);
    for (let k = 0; k < BINS; k++) {
      const f = freqs[k]; for (let b = 0; b < MEL; b++) if (f >= mEdges[b] && f < mEdges[b + 1]) { melOf[k] = b; break; }
      if (f >= 55 && f <= 2000) pc[k] = ((Math.round(12 * Math.log2(f / 440) + 69) % 12) + 12) % 12;
    }
    const db = new Float64Array(frames), cent = new Float64Array(frames), flux = new Float64Array(frames);
    const mel = new Float32Array(frames * MEL), chr = new Float32Array(frames * 12);
    for (let f = 0; f < frames; f++) {
      let e = 0, sm = 0, ws = 0; const m = f * BINS, bf = new Float64Array(MEL), cf = new Float64Array(12);
      for (let k = 0; k < BINS; k++) { const v = mag[m + k]; e += v * v; sm += v; ws += v * freqs[k]; if (melOf[k] >= 0) bf[melOf[k]] += v; if (pc[k] >= 0) cf[pc[k]] += v; }
      db[f] = 20 * Math.log10(Math.sqrt(e / BINS) + 1e-9); cent[f] = ws / (sm + 1e-9);
      let cs = 0; for (let j = 0; j < 12; j++) cs += cf[j]; cs += 1e-9;
      for (let j = 0; j < MEL; j++) mel[f * MEL + j] = Math.log1p(bf[j]);
      for (let j = 0; j < 12; j++) chr[f * 12 + j] = cf[j] / cs;
      if (f > 0) { let fl = 0; const p = m - BINS; for (let k = 0; k < BINS; k++) { const d = mag[m + k] - mag[p + k]; if (d > 0) fl += d; } flux[f] = fl; }
    }
    let bpm = opts.bpm || tempo(flux, fps); while (bpm < 70) bpm *= 2; while (bpm > 160) bpm /= 2;
    const dur = y.length / SR;
    let times = trackBeats(flux, fps, bpm).map(frameCenter);
    times = snapToOnsets(y, times);
    const nB = times.length;
    if (nB < 16) { onProgress(1); return { bpm: +bpm.toFixed(1), beats: nB, duration: dur, nodes: times.map((t, i) => ({ i, t: +t.toFixed(3), arousal: .5, brightness: .5 })), edges: [] }; }
    const bound = i => (i < nB ? times[i] : dur);
    // per-beat vectors (what the beat sounds like)
    const T = [], C = [], D = new Float64Array(nB), CE = new Float64Array(nB);
    for (let i = 0; i < nB; i++) {
      const a = timeToFrame(bound(i)), b = Math.min(frames, Math.max(timeToFrame(bound(i + 1)), a + 1)), n = Math.max(b - a, 1);
      const tm = new Float64Array(12), ch = new Float64Array(12); let d = 0, c = 0, tmean = 0;
      for (let f = a; f < b && f < frames; f++) { for (let j = 0; j < 12; j++) { tm[j] += (mel[f * MEL + 2 * j] + mel[f * MEL + 2 * j + 1]) / 2; ch[j] += chr[f * 12 + j]; } d += db[f]; c += cent[f]; }
      let cs = 0; for (let j = 0; j < 12; j++) { tm[j] /= n; ch[j] /= n; tmean += tm[j]; cs += ch[j]; } tmean /= 12;
      for (let j = 0; j < 12; j++) { tm[j] -= tmean; ch[j] /= (cs + 1e-9); }
      T.push(tm); C.push(ch); D[i] = d / n; CE[i] = c / n; onProgress(0.7 + 0.1 * i / nB);
    }
    // splice vectors: the sound just BEFORE each boundary (tail) and just AFTER it (head)
    const SPAN = 3, V = MEL + 12, tail = [], head = [];
    const vecAt = (f0, f1) => { const v = new Float64Array(V); let n = 0; for (let f = Math.max(0, f0); f < Math.min(frames, f1); f++) { for (let j = 0; j < MEL; j++) v[j] += mel[f * MEL + j]; for (let j = 0; j < 12; j++) v[MEL + j] += 10 * chr[f * 12 + j]; n++; } if (n) for (let j = 0; j < V; j++) v[j] /= n; return v; };
    const dbHead = [], dbTail = [], mdb = (f0, f1) => { let s2 = 0, n2 = 0; for (let f = Math.max(0, f0); f < Math.min(frames, f1); f++) { s2 += db[f]; n2++; } return n2 ? s2 / n2 : -90; };
    for (let j = 0; j < nB; j++) { const f = timeToFrame(times[j]); head.push(vecAt(f, f + SPAN)); tail.push(vecAt(f - SPAN, f)); dbHead.push(mdb(f, f + SPAN)); dbTail.push(mdb(f - SPAN, f)); }
    const dv = (u, w) => { let s = 0; for (let j = 0; j < V; j++) { const d = u[j] - w[j]; s += d * d; } return Math.sqrt(s); };
    const nat = []; for (let j = 1; j < nB; j++) nat.push(dv(tail[j], head[j]));
    const natMed = percentile(nat, 50) + 1e-9;
    // beat similarity (is beat a like beat b?)
    const unit = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) + 1e-9; return v.map(x => x / s); };
    const Tu = T.map(unit), Cu = C.map(unit); let dm = 0; for (const x of D) dm += x; dm /= nB; let dvv = 0; for (const x of D) dvv += (x - dm) ** 2; const dsd = Math.sqrt(dvv / nB) + 1e-9;
    const dot = (u, w) => { let s = 0; for (let j = 0; j < 12; j++) s += u[j] * w[j]; return s; };
    const beatDist0 = (a, b) => 0.5 * (1 - dot(Tu[a], Tu[b])) + 0.3 * (1 - dot(Cu[a], Cu[b])) + 0.2 * Math.abs((D[a] - D[b]) / dsd) / 4;
    const hist = opts.history ?? 0; // experimental: also match the beat BEFORE the cut (measured: no gain, so off by default)
    const beatDist = (a, b) => beatDist0(a, b) + ((a % bar) !== (b % bar) ? 0.15 : 0) + (hist && a > 0 && b > 0 ? hist * beatDist0(a - 1, b - 1) : 0);
    // candidate jumps: after beat a, continue at beat `dest`
    const cand = [], all = [];
    let natZ = [], cutZ = Infinity;
    if (MODEL) { for (let j = 1; j < nB; j++) natZ.push(modelScore(MODEL, pairFeatures(tail[j], head[j], dbTail[j], dbHead[j]))); cutZ = percentile(natZ, 90); }
    for (let a = 0; a < nB - 1; a++) for (let dest = 1; dest < nB; dest++) {
      if (Math.abs(dest - (a + 1)) < minGap) continue;
      const bd = beatDist(a, dest - 1), ratio = dv(tail[a + 1], head[dest]) / natMed;
      const z = MODEL ? modelScore(MODEL, pairFeatures(tail[a + 1], head[dest], dbTail[a + 1], dbHead[dest])) : 0;
      cand.push([a, dest, bd, ratio, z]); all.push(bd);
    }
    const bdCut = Math.min(0.35 * (1 + (opts.history ?? 0)), percentile(all, 4)), edges = [], byA = new Map();
    const smooth = c => (MODEL ? c[4] <= cutZ : c[3] <= maxRatio), rank = c => (MODEL ? c[4] + 6 * c[2] : c[3] + 3 * c[2]);
    for (const c of cand) if (c[2] <= bdCut && smooth(c)) { if (!byA.has(c[0])) byA.set(c[0], []); byA.get(c[0]).push(c); }
    for (const [a, list] of byA) { list.sort((p, q) => rank(p) - rank(q)); for (const c of list.slice(0, topk)) edges.push({ a, b: c[1], d: +c[2].toFixed(3), s: +c[3].toFixed(2), z: +c[4].toFixed(2), l: +Math.abs(dbTail[a + 1] - dbHead[c[1]]).toFixed(1) }); }
    const d10 = percentile(D, 10), d90 = percentile(D, 90), c10 = percentile(CE, 10), c90 = percentile(CE, 90), clip = x => Math.max(0, Math.min(1, x));
    const nodes = times.map((t, i) => ({ i, t: +t.toFixed(3), arousal: +clip((D[i] - d10) / (d90 - d10 + 1e-9)).toFixed(2), brightness: +clip((CE[i] - c10) / (c90 - c10 + 1e-9)).toFixed(2) }));
    onProgress(1);
    const res = { bpm: +bpm.toFixed(1), beats: nB, duration: +dur.toFixed(3), naturalCost: +natMed.toFixed(3), nodes, edges };
    if (opts.debug) res._internals = { tail, head, dbTail, dbHead, MEL };   // for tools/continuity.js (training experiments)
    return res;
  }

  const api = { SR, build, stftMag, tempo, trackBeats, snapToOnsets, pairFeatures, modelScore };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.F33LAnalyze = api;
})(typeof self !== 'undefined' ? self : this);
