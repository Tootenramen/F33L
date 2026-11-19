// node tools/tune.js f33l-labels.json [more.json ...]
// Fits a tiny logistic regression on YOUR "smooth / off" jump labels so we can see which measurements predict a bad cut.
// Features per jump: s = splice roughness vs a normal beat edge, d = beat similarity distance, l = loudness jump (dB), z = learned continuity score (when present).
const fs = require('fs');
const FEATS = ['s', 'd', 'l', 'z'];

function fit(rows, iters = 3000, lr = 0.1) {
  const X = rows.map(r => FEATS.map(f => +r[f] || 0)), y = rows.map(r => (r.kind === 'bad' ? 1 : 0));
  const mu = FEATS.map((_, j) => X.reduce((s, r) => s + r[j], 0) / X.length);
  const sd = FEATS.map((_, j) => Math.sqrt(X.reduce((s, r) => s + (r[j] - mu[j]) ** 2, 0) / X.length) || 1);
  const Z = X.map(r => r.map((v, j) => (v - mu[j]) / sd[j]));
  let w = FEATS.map(() => 0), b = 0;
  for (let it = 0; it < iters; it++) {
    const gw = FEATS.map(() => 0); let gb = 0;
    for (let i = 0; i < Z.length; i++) { const p = 1 / (1 + Math.exp(-(b + Z[i].reduce((s, v, j) => s + v * w[j], 0)))); const e = p - y[i]; gb += e; Z[i].forEach((v, j) => (gw[j] += e * v)); }
    w = w.map((v, j) => v - lr * gw[j] / Z.length); b -= lr * gb / Z.length;
  }
  const pred = Z.map(r => 1 / (1 + Math.exp(-(b + r.reduce((s, v, j) => s + v * w[j], 0)))) > 0.5 ? 1 : 0);
  const acc = pred.reduce((s, p, i) => s + (p === y[i] ? 1 : 0), 0) / y.length;
  return { weights: Object.fromEntries(FEATS.map((f, j) => [f, +w[j].toFixed(3)])), bias: +b.toFixed(3), accuracy: +acc.toFixed(3), n: rows.length, bad: y.reduce((s, v) => s + v, 0) };
}
module.exports = { fit };

if (require.main === module) {
  const rows = process.argv.slice(2).flatMap(f => JSON.parse(fs.readFileSync(f, 'utf8')).labels || []).filter(r => r.kind === 'bad' || r.kind === 'good');
  if (rows.length < 10) { console.log(`Only ${rows.length} labels. Label at least 30 jumps (both smooth and off) for this to mean anything.`); process.exit(0); }
  const r = fit(rows);
  console.log(JSON.stringify(r, null, 1));
  console.log('Positive weight = bigger value makes a jump more likely to sound off. Treat this as a hint from a small sample, not a law.');
}
