"""Independent splice-quality metric. For each jump a->dest, compare the 46 ms of real audio just before the cut with the
46 ms just after it (loudness jump + log-spectral distance), and compare that with natural boundaries (a->a+1) in the same song.
Usage: python splice_metric.py audio.f32 graph.json label     (audio = mono float32 at 22050 Hz)"""
import json, sys
import numpy as np
SR, W = 22050, 1024
win = np.hanning(W)
def spec(x):
    x = np.pad(x, (0, max(0, W - len(x))))[:W] * win
    return np.log1p(np.abs(np.fft.rfft(x))[5:372])
def cost(y, t_end, t_start):
    e, s = int(t_end * SR), int(t_start * SR)
    if e - W < 0 or s + W > len(y): return None
    L, R = y[e - W:e], y[s:s + W]
    db = abs(10 * np.log10((np.mean(L ** 2) + 1e-9) / (np.mean(R ** 2) + 1e-9)))
    return 0.5 * db + float(np.mean(np.abs(spec(L) - spec(R))))
y = np.fromfile(sys.argv[1], dtype=np.float32); g = json.load(open(sys.argv[2])); label = sys.argv[3]
t = [n["t"] for n in g["nodes"]]; dur = len(y) / SR
nat = [c for i in range(1, len(t)) if (c := cost(y, t[i], t[i])) is not None]
jmp = []
for e in g["edges"]:
    a, d = e["a"], e["b"]
    if a + 1 < len(t) and d < len(t) and (c := cost(y, t[a + 1], t[d])) is not None: jmp.append(c)
nat, jmp = np.array(nat), np.array(jmp)
p75, p90 = np.percentile(nat, 75), np.percentile(nat, 90)
print(f"{label:28s} beats={len(t):4d} jumps={len(jmp):5d} | natural median={np.median(nat):.2f} | jump median={np.median(jmp):.2f} "
      f"(x{np.median(jmp)/np.median(nat):.2f}) | jumps as smooth as a natural beat edge (<=p75): {100*np.mean(jmp<=p75):.0f}%  (<=p90): {100*np.mean(jmp<=p90):.0f}%")
