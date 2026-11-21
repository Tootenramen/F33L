// node tools/gapprobe.js --ffmpeg ffmpeg audio.mp3 words.json : can audio alone tell that a beat boundary sits in a gap between words?
const { spawnSync } = require('child_process'), A = require('../analyze.js'), fs = require('fs');
const i0 = process.argv.indexOf('--ffmpeg'), ff = process.argv[i0 + 1];
const [f, wf] = process.argv.slice(2).filter((x, i, a) => x !== '--ffmpeg' && a[i - 1] !== '--ffmpeg'), W = JSON.parse(fs.readFileSync(wf)), M = 0.04;
const inWord = t => W.some(w => t > w.start + M && t < w.end - M);
function auc(sc, lb) { const idx = sc.map((_, i) => i).sort((a, b) => sc[a] - sc[b]); let r1 = 0, n1 = 0, n0 = 0; idx.forEach((k, r) => { if (lb[k]) { n1++; r1 += r + 1; } else n0++; }); return (r1 - n1 * (n1 + 1) / 2) / (n1 * n0); }
(async () => {
  const r = spawnSync(ff, ['-v', 'error', '-t', '240', '-i', f, '-ac', '1', '-ar', String(A.SR), '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
  const y = new Float32Array(r.stdout.buffer, r.stdout.byteOffset, r.stdout.length / 4), g = await A.build(y, { debug: true }), { dbTail, dbHead } = g._internals;
  const sc = [], lb = [], sc2 = [];
  for (let j = 3; j < g.beats - 3; j++) { const t = g.nodes[j].t; let loc = 0; for (let k = j - 4; k <= j + 4; k++) loc += (dbTail[k] + dbHead[k]) / 18;
    sc.push(((dbTail[j] + dbHead[j]) / 2) - loc); sc2.push(Math.min(dbTail[j], dbHead[j]) - loc); lb.push(inWord(t) ? 1 : 0); }
  // label 1 = inside a word; score should be HIGH when inside, so use +level
  console.log('boundaries', lb.length, 'inWord', (lb.reduce((a, b) => a + b, 0) / lb.length).toFixed(2), 'AUC meanLevel-vs-local', auc(sc, lb).toFixed(3), 'AUC minLevel-vs-local', auc(sc2, lb).toFixed(3));
})();
