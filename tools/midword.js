// node tools/midword.js --ffmpeg ffmpeg audio.mp3 outputs/words_x.json
// Share of jumps whose cut (end of beat a) or landing (start of dest) falls strictly inside a spoken/sung word (>40 ms from its edges).
const { spawnSync } = require('child_process'), A = require('../analyze.js'), fs = require('fs');
const i0 = process.argv.indexOf('--ffmpeg'), ff = i0 > 0 ? process.argv[i0 + 1] : 'ffmpeg';
const [f, wf] = process.argv.slice(2).filter((x, i, a) => x !== '--ffmpeg' && a[i - 1] !== '--ffmpeg');
const W = JSON.parse(fs.readFileSync(wf)), M = 0.04;
const inWord = t => W.some(w => t > w.start + M && t < w.end - M), wordAt = t => W.find(w => t > w.start + M && t < w.end - M);
const norm = x => x.toLowerCase().replace(/[^a-z']/g, '');
// a jump is 'word-consistent' if neither end is inside a word, or both ends are inside the SAME word at the same point (within 70 ms)
const consistent = (tc, tl) => { const u = wordAt(tc), v = wordAt(tl); if (!u && !v) return true; if (!u || !v) return false; return norm(u.w) === norm(v.w) && Math.abs((tc - u.start) - (tl - v.start)) < 0.07; };
(async () => {
  const r = spawnSync(ff, ['-v', 'error', '-t', '240', '-i', f, '-ac', '1', '-ar', String(A.SR), '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
  const y = new Float32Array(r.stdout.buffer, r.stdout.byteOffset, r.stdout.length / 4);
  const model = require('../continuity_model.js'), rows = [];
  for (const [name, opts] of [['distance', {}], ['learned', { model }], ['eternal', { style: 'eternal' }], ['eternal+smooth', { style: 'eternal', eternalSmooth: true }]]) {
    const g = await A.build(y, opts); let n = 0, s = 0, l = 0, e = 0, ok = 0;
    for (const x of g.edges) { n++; const a = inWord(g.nodes[Math.min(x.a + 1, g.nodes.length - 1)].t), b = inWord(g.nodes[x.b].t + (x.o || 0)); s += a; l += b; e += (a || b); ok += consistent(g.nodes[Math.min(x.a + 1, g.nodes.length - 1)].t, g.nodes[x.b].t + (x.o || 0)); }
    const nat = g.nodes.filter(nd => inWord(nd.t)).length / g.nodes.length;
    rows.push({ mode: name, edges: n, srcMid: +(s / n).toFixed(3), landMid: +(l / n).toFixed(3), either: +(e / n).toFixed(3), wordConsistent: +(ok / n).toFixed(3), chanceBeatInWord: +nat.toFixed(3) });
  }
  console.table(rows);
})();
