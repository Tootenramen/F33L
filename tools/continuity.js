// node tools/continuity.js --ffmpeg ffmpeg  a.mp3 b.mp3 c.mp3 ...
// Experiment: can a model LEARN what a continuous cut sounds like? Positives = ordinary beat edges (tail[j] -> head[j]),
// negatives = random splices (tail[a+1] -> head[k]). Leave-one-song-out, so the test song was never seen in training.
// Compares a learned per-feature weighting against the plain Euclidean splice distance the engine uses today.
const { spawnSync } = require('child_process'), A = require('../analyze.js');
const i0 = process.argv.indexOf('--ffmpeg'), ff = i0 > 0 ? process.argv[i0 + 1] : 'ffmpeg';
const SKIPV = new Set(['--ffmpeg', '--export', '--exclude']);
const files = process.argv.slice(2).filter((x, i, a) => !SKIPV.has(x) && !SKIPV.has(a[i - 1]));
let seed = 12345; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

function auc(scores, labels) { // P(score of a splice > score of a natural edge)
  const idx = scores.map((s, i) => i).sort((a, b) => scores[a] - scores[b]); const rank = new Array(scores.length);
  for (let i = 0; i < idx.length;) { let j = i; while (j + 1 < idx.length && scores[idx[j + 1]] === scores[idx[i]]) j++; for (let k = i; k <= j; k++) rank[idx[k]] = (i + j) / 2 + 1; i = j + 1; }
  let n1 = 0, n0 = 0, r1 = 0; labels.forEach((l, i) => { if (l) { n1++; r1 += rank[i]; } else n0++; }); return (r1 - n1 * (n1 + 1) / 2) / (n1 * n0);
}
function fitLR(X, y, iters = 400, lr = 0.2, l2 = 1e-3) {
  const d = X[0].length, mu = Array(d).fill(0), sd = Array(d).fill(0);
  X.forEach(r => r.forEach((v, j) => mu[j] += v / X.length)); X.forEach(r => r.forEach((v, j) => sd[j] += (v - mu[j]) ** 2 / X.length)); sd.forEach((v, j) => sd[j] = Math.sqrt(v) || 1);
  const Z = X.map(r => r.map((v, j) => (v - mu[j]) / sd[j])); let w = Array(d).fill(0), b = 0;
  for (let it = 0; it < iters; it++) { const gw = Array(d).fill(0); let gb = 0; for (let i = 0; i < Z.length; i++) { let z = b; for (let j = 0; j < d; j++) z += Z[i][j] * w[j]; const e = 1 / (1 + Math.exp(-z)) - y[i]; gb += e; for (let j = 0; j < d; j++) gw[j] += e * Z[i][j]; } for (let j = 0; j < d; j++) w[j] -= lr * (gw[j] / Z.length + l2 * w[j]); b -= lr * gb / Z.length; }
  return { w, b, mu, sd, score: r => { let z = b; for (let j = 0; j < d; j++) z += ((r[j] - mu[j]) / sd[j]) * w[j]; return z; } };
}
(async () => {
  const songs = [];
  for (const f of files) {
    const r = spawnSync(ff, ['-v', 'error', '-t', '240', '-i', f, '-ac', '1', '-ar', String(A.SR), '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
    if (r.status !== 0) { console.error('skip', f); continue; }
    const y = new Float32Array(r.stdout.buffer, r.stdout.byteOffset, r.stdout.length / 4), g = await A.build(y, { debug: true }), { tail, head, dbTail, dbHead } = g._internals;
    const feat = (i, k) => A.pairFeatures(tail[i], head[k], dbTail[i], dbHead[k]);
    const rows = [], labels = [];
    for (let j = 1; j < g.beats; j++) { rows.push(feat(j, j)); labels.push(0); }
    for (let a = 0; a < g.beats - 1; a++) for (let t = 0; t < 3; t++) { const k = Math.floor(rnd() * g.beats); if (Math.abs(k - (a + 1)) >= 8) { rows.push(feat(a + 1, k)); labels.push(1); } }
    songs.push({ name: f.split(/[\/]/).pop().slice(0, 28), rows, labels, beats: g.beats });
  }
  console.log(`songs: ${songs.length}`); const euclid = r => Math.sqrt(r.slice(0, 24).reduce((s, v) => s + v * v, 0));
  const ex = process.argv.indexOf('--export');
  if (ex > 0) { // train on everything (optionally leaving one song out) and write the model the engine loads
    const skip = process.argv.indexOf('--exclude') > 0 ? process.argv[process.argv.indexOf('--exclude') + 1] : null;
    const tr = songs.filter(s => !skip || !s.name.includes(skip)), m = fitLR(tr.flatMap(s => s.rows), tr.flatMap(s => s.labels), 600);
    const r5 = v => +v.toFixed(5), M = { note: 'continuity model trained by tools/continuity.js; higher score = more likely a break', songs: tr.length, b: r5(m.b), w: m.w.map(r5), mu: m.mu.map(r5), sd: m.sd.map(r5) };
    require('fs').writeFileSync(process.argv[ex + 1], '(function(r){const M=' + JSON.stringify(M) + ';if(typeof module!=="undefined"&&module.exports)module.exports=M;else r.F33LModel=M;})(typeof self!=="undefined"?self:this);' + String.fromCharCode(10)); console.log('exported', process.argv[ex + 1], 'trained on', tr.length, 'songs'); process.exit(0);
  }
  const out = [];
  for (let t = 0; t < songs.length; t++) {
    const tr = songs.filter((_, i) => i !== t), X = tr.flatMap(s => s.rows), y = tr.flatMap(s => s.labels), m = fitLR(X, y), te = songs[t];
    const base = te.rows.map(euclid), learned = te.rows.map(m.score);
    // hard regime: only splices the baseline already thinks are fairly smooth (the candidates the engine actually picks from)
    const natB = base.filter((_, i) => te.labels[i] === 0).sort((a, b) => a - b), cut = natB[Math.floor(natB.length * 0.9)];
    const keep = te.rows.map((_, i) => te.labels[i] === 0 || base[i] <= cut * 1.5);
    const pick = a => a.filter((_, i) => keep[i]), L = pick(te.labels);
    out.push({ song: te.name, beats: te.beats, baselineAUC: +auc(base, te.labels).toFixed(3), learnedAUC: +auc(learned, te.labels).toFixed(3), baselineHard: +auc(pick(base), L).toFixed(3), learnedHard: +auc(pick(learned), L).toFixed(3), hardN: L.length });
  }
  console.table(out);
  const mean = k => +(out.reduce((s, r) => s + r[k], 0) / out.length).toFixed(3);
  console.log('mean  all-splices AUC: baseline', mean('baselineAUC'), 'learned', mean('learnedAUC'), '| hard-regime AUC: baseline', mean('baselineHard'), 'learned', mean('learnedHard'));
})();
