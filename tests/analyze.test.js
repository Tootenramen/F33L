// node --test tests/   (synthetic audio with known answers, same idea as test_listen.py)
const test = require('node:test'), assert = require('node:assert'), A = require('../analyze.js');
const SR = A.SR;
const tone = (f, d) => { const n = Math.floor(SR * d), y = new Float32Array(n); for (let i = 0; i < n; i++) for (let h = 1; h <= 3; h++) y[i] += Math.sin(2 * Math.PI * f * h * i / SR) / h * 0.3; return y; };
const cat = parts => { const y = new Float32Array(parts.reduce((s, p) => s + p.length, 0)); let o = 0; for (const p of parts) { y.set(p, o); o += p.length; } return y; };

test('repeating 4-beat bar: jumps only between same bar positions, never neighbours', async () => {
  const bar = [220, 330, 440, 660].map(f => tone(f, 0.5)), y = cat(Array(16).fill(bar).flat());
  const g = await A.build(y, { bpm: 120 });
  assert.ok(g.edges.length > 20, 'expected jump edges, got ' + g.edges.length);
  for (const e of g.edges) { assert.ok((e.a - e.b) % 4 === 0); assert.ok(Math.abs(e.a - e.b) >= 8); }
  for (const n of g.nodes) assert.ok(n.arousal >= 0 && n.arousal <= 1 && n.brightness >= 0 && n.brightness <= 1);
});

test('click track at 120 BPM is detected as about 120', async () => {
  const y = new Float32Array(SR * 20); let seed = 1; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5;
  for (let b = 0; b < 40; b++) { const i = Math.floor(b * 0.5 * SR); for (let k = 0; k < 400; k++) y[i + k] += rnd() * 2; }
  const { mag, frames } = await A.stftMag(y), fps = SR / 512, flux = new Float64Array(frames);
  for (let f = 1; f < frames; f++) { let s = 0; for (let k = 0; k < 1025; k++) s += Math.max(0, mag[f * 1025 + k] - mag[(f - 1) * 1025 + k]); flux[f] = s; }
  assert.ok(Math.abs(A.tempo(flux, fps) - 120) < 4);
});
