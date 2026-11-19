"""Regenerate every figure in docs/HOW_IT_WORKS.md.

The data figures are drawn from the real demo track (demo/demo.mp3) and the real beat graph the engine built from it
(demo/graph.json). The measured-result figures use the numbers recorded in docs/DEVLOG.md. Nothing here is decorative:
if a chart is a diagram instead of data, its title says "diagram".

Usage:  python tools/make_figures.py [--ffmpeg ffmpeg] [--out docs/img]
Needs:  numpy, matplotlib
"""
import argparse, json, os, subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Arc

ap = argparse.ArgumentParser()
ap.add_argument("--ffmpeg", default="ffmpeg")
ap.add_argument("--out", default="docs/img")
args = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, args.out)
os.makedirs(OUT, exist_ok=True)

# ---- palette (matches the website) ----
BG, PANEL, INK, MUTE, GRID = "#07070c", "#10101a", "#ecebf5", "#8a89a6", "#23233a"
PINK, CYAN, VIOLET, GREEN, AMBER, RED = "#f472b6", "#22d3ee", "#a78bfa", "#34d399", "#fbbf24", "#fb7185"
FEEL = LinearSegmentedColormap.from_list("feel", ["#1d4e89", "#22a6d3", "#a78bfa", "#f472b6"])
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG, "text.color": INK,
    "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": MUTE, "axes.edgecolor": GRID,
    "axes.titlecolor": INK, "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "grid.color": GRID, "legend.frameon": False,
    "font.family": "DejaVu Sans",
})

def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print("wrote", p)

def dh(ax, title, sub, ytop, x=0.15):
    ax.text(x, ytop, title, fontsize=19, fontweight="bold", color=INK, ha="left", va="top")
    ax.text(x, ytop - 0.42, sub, fontsize=11.5, color=MUTE, ha="left", va="top")

def headline(fig, title, sub, y=0.995):
    fig.text(0.0, y, title, fontsize=19, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.0, y - 0.07, sub, fontsize=11.5, color=MUTE, ha="left", va="top")

# ---- load the real data ----
SR, N_FFT, HOP, MEL = 22050, 2048, 512, 24
g = json.load(open(os.path.join(ROOT, "demo", "graph.json")))
raw = subprocess.run([args.ffmpeg, "-v", "error", "-i", os.path.join(ROOT, "demo", "demo.mp3"),
                      "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
y = np.frombuffer(raw, dtype=np.float32)
dur = len(y) / SR
beats = np.array([n["t"] for n in g["nodes"]])
arousal = np.array([n["arousal"] for n in g["nodes"]])
bright = np.array([n["brightness"] for n in g["nodes"]])
edges = g["edges"]
NB = len(beats)
BPM = g["bpm"]

win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)
frames = 1 + (len(y) - N_FFT) // HOP
idx = np.arange(N_FFT)[None, :] + HOP * np.arange(frames)[:, None]
mag = np.abs(np.fft.rfft(y[idx] * win, axis=1)).astype(np.float32)
freqs = np.arange(N_FFT // 2 + 1) * SR / N_FFT
medges = 50 * (10000 / 50) ** (np.arange(MEL + 1) / MEL)
mel = np.zeros((frames, MEL), np.float32)
for b in range(MEL):
    m = (freqs >= medges[b]) & (freqs < medges[b + 1])
    mel[:, b] = np.log1p(mag[:, m].sum(1))
pc = np.full(len(freqs), -1)
ok = (freqs >= 55) & (freqs <= 2000)
pc[ok] = (np.round(12 * np.log2(freqs[ok] / 440) + 69).astype(int) % 12)
chroma = np.zeros((frames, 12), np.float32)
for j in range(12):
    chroma[:, j] = mag[:, pc == j].sum(1)
chroma /= chroma.sum(1, keepdims=True) + 1e-9
dbf = 20 * np.log10(np.sqrt((mag ** 2).sum(1) / mag.shape[1]) + 1e-9)
flux = np.zeros(frames)
flux[1:] = np.maximum(mag[1:] - mag[:-1], 0).sum(1)
ft = (np.arange(frames) * HOP + N_FFT / 2) / SR           # frame centre times
t2f = lambda t: int(max(0, round((t * SR - N_FFT / 2) / HOP)))
LAYERS = [(0, "calm pad"), (1, "+ bass"), (2, "+ arpeggio\n+ drums"), (3, "same,\nmore energy"), (4, "+ lead melody"), (5, "+ the lift")]
BARS = 4 * 60 / 105
LAYER_T = [k * 4 * BARS for k in range(7)]

# =====================================================================================
# 00  the experiment (diagram)
# =====================================================================================
fig = plt.figure(figsize=(12, 4.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 4.6)
dh(ax, "The experiment: can a computer learn how music feels?", "Four steps. Here is honestly where each one stands today.", 4.45)
steps = [
    ("1", "MEASURE", "tempo, beats, timbre,\npitch, loudness, texture", "BUILT", GREEN),
    ("2", "MAP TO FEELING", "energy + brightness per beat.\nA proxy, not a validated\nemotion model", "PROXY", AMBER),
    ("3", "EXPLAIN", "an AI reads a score card\nand says WHY a song\nfeels that way", "SKETCH", VIOLET),
    ("4", "TEST ON PEOPLE", "compare to human ratings.\nReport where listeners\ndisagree", "NOT YET", RED),
]
for k, (n, t, d, tag, col) in enumerate(steps):
    x = 0.15 + k * 2.95
    ax.add_patch(FancyBboxPatch((x, 0.7), 2.55, 2.5, boxstyle="round,pad=0.02,rounding_size=0.14", fc=PANEL, ec=col, lw=2))
    ax.text(x + 0.2, 2.8, n, fontsize=26, fontweight="bold", color=col, va="center")
    ax.text(x + 0.75, 2.8, t, fontsize=11, fontweight="bold", color=INK, va="center")
    ax.text(x + 0.2, 1.95, d, fontsize=9.6, color=MUTE, va="center", linespacing=1.5)
    ax.add_patch(FancyBboxPatch((x + 0.2, 0.9), 1.15, 0.38, boxstyle="round,pad=0.01,rounding_size=0.18", fc=col, ec="none"))
    ax.text(x + 0.775, 1.09, tag, fontsize=9.5, fontweight="bold", color=BG, ha="center", va="center")
    if k < 3:
        ax.add_patch(FancyArrowPatch((x + 2.6, 1.95), (x + 2.93, 1.95), arrowstyle="-|>", mutation_scale=18, color=MUTE, lw=2))
ax.text(0.15, 0.3, "The jukebox on the website is the visible part of steps 1 and 2: it measures every beat and lets you steer by the feeling tags.", fontsize=10, color=MUTE)
save(fig, "00_experiment.png")

# =====================================================================================
# 01  the pipeline (diagram)
# =====================================================================================
fig = plt.figure(figsize=(12, 7.2)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 12.3); ax.set_ylim(0, 7.2)
dh(ax, "From a song to a map you can wander", "What happens in your browser in the few seconds after you drop a file in. Nothing is uploaded.", 7.05, 0.1)
boxes = [
    ("1  LISTEN", "Slice the audio into 23 ms\nwindows (FFT). Keep loudness,\nbrightness, 24 pitch bands,\n12 note classes.", CYAN),
    ("2  FEEL THE PULSE", "Find where sounds START\n(onsets). Autocorrelate them\nto estimate the tempo.", CYAN),
    ("3  TRACK THE BEATS", "Dynamic programming picks\nthe beat path that hits real\nonsets but stays near tempo.", VIOLET),
    ("4  SNAP TO SOUNDS", "Move every beat onto the\nnearest transient (within 60 ms)\nso cuts land on a sound's START.", VIOLET),
    ("5  FINGERPRINT", "Each beat becomes: timbre (12)\n+ notes (12) + loudness.\nWhat a beat 'sounds like'.", PINK),
    ("6  FIND TWINS", "Compare every beat with every\nother. Close = twins. Penalty\nif the bar position differs.", PINK),
    ("7  PRICE THE CUT", "For each candidate jump, compare\nthe sound just BEFORE the cut\nwith just AFTER, vs a normal edge.", AMBER),
    ("8  KEEP THE BEST", "Keep jumps that are twin-close\nAND no rougher than 1.7x a\nnormal edge. Top 4 per beat.", AMBER),
]
xs = [0.1, 3.2, 6.3, 9.4]
pos = [(xs[0], 4.2), (xs[1], 4.2), (xs[2], 4.2), (xs[3], 4.2), (xs[3], 1.95), (xs[2], 1.95), (xs[1], 1.95), (xs[0], 1.95)]
for (t, d, col), (x, yy) in zip(boxes, pos):
    ax.add_patch(FancyBboxPatch((x, yy), 2.8, 1.95, boxstyle="round,pad=0.02,rounding_size=0.12", fc=PANEL, ec=col, lw=2))
    ax.text(x + 0.18, yy + 1.62, t, fontsize=11, fontweight="bold", color=col, va="center")
    ax.text(x + 0.18, yy + 0.78, d, fontsize=8.8, color=INK, va="center", linespacing=1.5)
for k in range(3):
    ax.add_patch(FancyArrowPatch((xs[k] + 2.84, 5.17), (xs[k + 1] - 0.04, 5.17), arrowstyle="-|>", mutation_scale=16, color=MUTE, lw=1.8))
    ax.add_patch(FancyArrowPatch((xs[k + 1] - 0.04, 2.92), (xs[k] + 2.84, 2.92), arrowstyle="-|>", mutation_scale=16, color=MUTE, lw=1.8))
ax.add_patch(FancyArrowPatch((xs[3] + 1.4, 4.15), (xs[3] + 1.4, 3.95), arrowstyle="-|>", mutation_scale=16, color=MUTE, lw=1.8))
ax.add_patch(FancyBboxPatch((0.1, 0.15), 12.1, 1.35, boxstyle="round,pad=0.02,rounding_size=0.12", fc="#1a1030", ec=PINK, lw=2))
ax.text(0.35, 1.2, "9  PLAY FOREVER", fontsize=12, fontweight="bold", color=PINK, va="center")
ax.text(0.35, 0.65, "Play beat by beat. At every beat, roll the dice (the chance builds the longer it has been since the last jump).\nIf it hits, take one of that beat's jumps. A 20 ms crossfade glues every join.", fontsize=9.6, color=INK, va="center", linespacing=1.5)
ax.add_patch(FancyArrowPatch((1.5, 1.9), (1.5, 1.55), arrowstyle="-|>", mutation_scale=16, color=MUTE, lw=1.8))
save(fig, "01_pipeline.png")

# =====================================================================================
# 02  anatomy of the demo song (data)
# =====================================================================================
fig = plt.figure(figsize=(12, 6.8))
headline(fig, "The demo song, as the engine hears it", "Real data. The track builds in layers every 4 bars, so it has a clear calm -> intense arc. Vertical lines are the 98 detected beats.", 1.0)
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.6], hspace=0.06, top=0.8)
ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1], sharex=ax1)
tt = np.arange(len(y)) / SR
step = 64
env = np.array([np.abs(y[i:i + step]).max() for i in range(0, len(y) - step, step)])
te = (np.arange(len(env)) * step) / SR
ax1.fill_between(te, -env, env, color=PINK, lw=0, alpha=0.9)
ax1.set_ylabel("waveform"); ax1.set_yticks([]); ax1.set_ylim(-1.05 * env.max(), 1.05 * env.max())
for b in beats:
    ax1.axvline(b, color=CYAN, lw=0.5, alpha=0.35)
for k, (_, label) in enumerate(LAYERS):
    ax1.text((LAYER_T[k] + LAYER_T[k + 1]) / 2, 1.08 * env.max(), label, ha="center", va="bottom", fontsize=9.5, color=INK, linespacing=1.2)
    if k:
        ax1.axvline(LAYER_T[k], color=INK, lw=1, ls=":", alpha=0.6)
ax1.tick_params(labelbottom=False)
ax2.imshow(mel.T, origin="lower", aspect="auto", extent=[ft[0], ft[-1], medges[0], medges[-1]], cmap="magma", vmin=0.3, interpolation="nearest")
ax2.set_yscale("log"); ax2.set_ylim(60, 8000)
ax2.set_ylabel("pitch band (Hz)  -  bright = loud"); ax2.set_xlabel("time (s)")
for b in beats:
    ax2.axvline(b, color=CYAN, lw=0.5, alpha=0.3)
ax2.set_xlim(0, dur)
ax2.text(dur - 0.5, 80, f"engine says {BPM} BPM  (true tempo: 105)", ha="right", color=CYAN, fontsize=10, fontweight="bold", bbox=dict(fc=BG, ec="none", pad=3))
save(fig, "02_anatomy.png")

# =====================================================================================
# 03  beat tracking beats a rigid grid (data)
# =====================================================================================
fig = plt.figure(figsize=(12, 6.2))
headline(fig, "Why a rigid beat grid fails and a tracker doesn't", "Real data. Top: a 6-second zoom. Bottom: how far a perfect metronome drifts from the beats the engine actually found.", 1.0)
gs = fig.add_gridspec(2, 1, height_ratios=[1.4, 1], hspace=0.5, top=0.8)
ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])
t0, t1 = 30, 36
m = (ft >= t0) & (ft <= t1)
ax1.fill_between(ft[m], 0, flux[m] / flux.max(), color=VIOLET, alpha=0.55, lw=0)
ax1.plot(ft[m], flux[m] / flux.max(), color=VIOLET, lw=1.2, label="onset strength (where sounds start)")
grid = beats[0] + np.arange(NB + 40) * 60 / BPM
for k, b in enumerate([b for b in beats if t0 <= b <= t1]):
    ax1.axvline(b, color=CYAN, lw=2.2, ymax=0.95, label="detected beat (snapped to the sound)" if k == 0 else None)
for k, b in enumerate([b for b in grid if t0 <= b <= t1]):
    ax1.axvline(b, color=AMBER, lw=1.6, ls="--", ymax=0.7, label="rigid grid at the same BPM" if k == 0 else None)
ax1.set_xlim(t0, t1); ax1.set_ylim(0, 1.25); ax1.set_yticks([]); ax1.set_xlabel("time (s)")
ax1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=9.5, labelcolor=INK)
dev = (beats - grid[:NB]) * 1000
ax2.axhline(0, color=GRID, lw=1)
ax2.fill_between(np.arange(NB), dev, 0, color=AMBER, alpha=0.3, lw=0)
ax2.plot(np.arange(NB), dev, color=AMBER, lw=2)
ax2.set_ylabel("grid minus detected (ms)"); ax2.set_xlabel("beat number")
ax2.text(2, dev.min() * 0.85, "tempo guess 103.4 vs true 105 (1.5% off):\na cut placed by the grid ends up this far from the real hit", ha="left", fontsize=10, color=AMBER, va="center")
save(fig, "03_beat_tracking.png")

# =====================================================================================
# 04  beat similarity matrix + chosen jumps (data)
# =====================================================================================
T = np.zeros((NB, 12)); C = np.zeros((NB, 12)); Dl = np.zeros(NB)
for i in range(NB):
    a = t2f(beats[i]); b = max(t2f(beats[i + 1]) if i + 1 < NB else frames, a + 1)
    mm = (mel[a:b, 0::2] + mel[a:b, 1::2]) / 2
    t_ = mm.mean(0); T[i] = t_ - t_.mean(); C[i] = chroma[a:b].mean(0); C[i] /= C[i].sum() + 1e-9; Dl[i] = dbf[a:b].mean()
unit = lambda M: M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
Tu, Cu = unit(T), unit(C)
dsd = Dl.std() + 1e-9
Dm = 0.5 * (1 - Tu @ Tu.T) + 0.3 * (1 - Cu @ Cu.T) + 0.2 * np.abs(Dl[:, None] - Dl[None, :]) / dsd / 4
pos_ = np.arange(NB) % 4
Dm += 0.15 * (pos_[:, None] != pos_[None, :])
fig, ax = plt.subplots(figsize=(8.6, 8.2))
headline(fig, "Which beats are twins?", "Every beat vs every beat. Bright = sounds alike. Cyan dots = the jumps the engine kept.", 1.02)
im = ax.imshow(Dm, origin="lower", cmap="magma_r", interpolation="nearest", extent=[0, NB, 0, NB])
ax.scatter([e["b"] - 1 + 0.5 for e in edges], [e["a"] + 0.5 for e in edges], s=11, color=CYAN, edgecolor="none", alpha=0.9)
ax.set_xlabel("the beat that sounds like it  (landing = this + 1)"); ax.set_ylabel("the beat we are leaving")
for k in range(1, 6):
    ax.axvline(LAYER_T[k] * BPM / 60, color=INK, lw=0.6, ls=":", alpha=0.4); ax.axhline(LAYER_T[k] * BPM / 60, color=INK, lw=0.6, ls=":", alpha=0.4)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label("distance (dark = far, light = twins)", color=MUTE)
cb.outline.set_edgecolor(GRID); cb.ax.tick_params(colors=MUTE)
ax.set_title("")
save(fig, "04_similarity.png")

# =====================================================================================
# 05  jump arcs (data)
# =====================================================================================
fig, ax = plt.subplots(figsize=(12, 5.2)); ax.set_facecolor("#05050a")
headline(fig, "The jump graph", f"Real data: {len(edges)} possible jumps over {NB} beats ({BPM} BPM). Taller arc = longer leap. Strip colour = how the beat feels (blue calm -> pink loud).", 1.0)
for e in sorted(edges, key=lambda e: -e["d"]):
    x0, x1 = e["a"] + 1, e["b"]
    c = (x0 + x1) / 2; w = abs(x1 - x0); h = w * 0.5
    ax.add_patch(Arc((c, 0), w, 2 * h, theta1=0, theta2=180, color=VIOLET, lw=0.7, alpha=max(0.12, 0.6 - e["d"])))
for i in range(NB):
    ax.add_patch(Rectangle((i, -9), 1, 8, color=FEEL(arousal[i]), lw=0))
ax.set_xlim(0, NB); ax.set_ylim(-10, NB * 0.5 * 0.85); ax.axis("off")
ax.text(0, -12.5, "start of song", color=MUTE, fontsize=10); ax.text(NB, -12.5, "end of song", color=MUTE, fontsize=10, ha="right")
ax.text(NB / 2, NB * 0.5 * 0.8, "every arc is one place the song can fold back on itself", ha="center", color=MUTE, fontsize=11)
save(fig, "05_jump_graph.png")

# =====================================================================================
# 06  landing rule (diagram)
# =====================================================================================
fig = plt.figure(figsize=(12, 6.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 6.6)
dh(ax, "Land ONE BEAT AFTER the match", "A diagram of the single most important fix (v0.5). Beat A sounds like beat B. After A, where should you go next?", 6.45, 0.4)
def row(yv, labels, hl, col):
    for k, lab in enumerate(labels):
        x = 0.4 + k * 1.55
        isb = k in hl
        ax.add_patch(FancyBboxPatch((x, yv), 1.35, 0.7, boxstyle="round,pad=0.01,rounding_size=0.1", fc=(col if isb else PANEL), ec=col, lw=1.6))
        ax.text(x + 0.675, yv + 0.35, lab, ha="center", va="center", fontsize=11.5, fontweight="bold", color=BG if isb else INK)
labs = ["A-1", "A", "A+1", "...", "B-1", "B", "B+1"]
cx = lambda k: 0.4 + k * 1.55 + 0.675
row(4.3, labs, {1, 5}, RED)
ax.annotate("", xy=(cx(5), 5.05), xytext=(cx(1), 5.05), arrowprops=dict(arrowstyle="-|>", color=RED, lw=2.4, connectionstyle="arc3,rad=-0.1"))
ax.text(0.4, 3.85, "Wrong (before v0.5):  jump TO the twin", color=RED, fontsize=12, fontweight="bold")
ax.text(0.4, 3.5, "plays B right after A: the music restarts the phrase in the middle.", fontsize=10, color=MUTE)
row(1.3, labs, {1, 6}, GREEN)
ax.annotate("", xy=(cx(6), 2.05), xytext=(cx(1), 2.05), arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=2.4, connectionstyle="arc3,rad=-0.1"))
ax.text(0.4, 0.85, "Right (v0.5 and later):  jump to the beat that FOLLOWS the twin", color=GREEN, fontsize=12, fontweight="bold")
ax.text(0.4, 0.5, "plays B+1: exactly what the song itself did after something like A. In the original, B was followed by B+1.", fontsize=10, color=INK)
save(fig, "06_landing_rule.png")

# =====================================================================================
# 07  feeling map (data)
# =====================================================================================
fig = plt.figure(figsize=(12, 5.4))
headline(fig, "How each beat 'feels'", "Real data. Two honest proxies per beat: loudness (energy) and spectral brightness. Not a validated emotion model.", 1.0)
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.5], wspace=0.3, top=0.82)
ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])
sc = ax1.scatter(bright, arousal, c=beats, cmap="viridis", s=48, edgecolor=BG, lw=0.6)
ax1.set_xlabel("brightness  (dull -> sparkly)"); ax1.set_ylabel("energy  (quiet -> loud)"); ax1.set_xlim(-0.05, 1.05); ax1.set_ylim(-0.05, 1.05)
ax1.axhline(0.5, color=GRID); ax1.axvline(0.5, color=GRID)
for (x, yv, s_) in [(0.02, 0.03, "calm + dark"), (0.98, 0.03, "calm + bright"), (0.02, 0.97, "loud + dark"), (0.98, 0.97, "loud + bright")]:
    ax1.text(x, yv, s_, color=MUTE, fontsize=9, ha="left" if x < 0.5 else "right", va="bottom" if yv < 0.5 else "top")
cb = fig.colorbar(sc, ax=ax1, fraction=0.05, pad=0.02); cb.set_label("time in song (s)", color=MUTE); cb.outline.set_edgecolor(GRID); cb.ax.tick_params(colors=MUTE)
for k in range(0, 6, 2):
    ax2.axvspan(LAYER_T[k], LAYER_T[k + 1], color=GRID, alpha=0.5, lw=0)
ax2.plot(beats, arousal, color=PINK, lw=2.4, label="energy")
ax2.plot(beats, bright, color=CYAN, lw=2.4, label="brightness")
ax2.set_xlim(0, dur); ax2.set_ylim(-0.02, 1.05); ax2.set_xlabel("time (s)"); ax2.legend(loc="lower right", fontsize=10, labelcolor=INK)
save(fig, "07_feeling_map.png")

# =====================================================================================
# 08  how rough are the chosen cuts (data)
# =====================================================================================
s = np.array([e["s"] for e in edges]); d_ = np.array([e["d"] for e in edges]); l_ = np.array([e["l"] for e in edges])
fig, axs = plt.subplots(1, 3, figsize=(13, 4.4))
headline(fig, "How good are the jumps it keeps?", f"Real data, all {len(edges)} kept jumps. Left: cut roughness vs an ordinary beat edge in the same song. Middle: how alike the twins are. Right: loudness change across the cut.", 1.06)
fig.subplots_adjust(top=0.76, wspace=0.28, bottom=0.2)
axs[0].hist(s, bins=28, color=PINK, edgecolor=BG)
axs[0].axvline(1.0, color=CYAN, lw=2); axs[0].axvline(1.7, color=AMBER, lw=2, ls="--")
axs[0].text(1.0, axs[0].get_ylim()[1] * 0.97, " = a normal\n beat edge", color=CYAN, fontsize=9, va="top"); axs[0].text(1.7, axs[0].get_ylim()[1] * 0.75, " the engine's\n limit (1.7x)", color=AMBER, fontsize=9, va="top")
axs[0].set_xlabel("cut roughness (1.0 = typical beat edge)"); axs[0].set_ylabel("number of jumps")
axs[1].hist(d_, bins=28, color=VIOLET, edgecolor=BG); axs[1].set_xlabel("twin distance (lower = more alike)")
axs[2].hist(l_, bins=28, color=GREEN, edgecolor=BG); axs[2].set_xlabel("loudness jump across the cut (dB)")
share = (s <= 1.0).mean() * 100
fig.text(0.0, 0.02, f"{share:.0f}% of kept jumps are as smooth as the median ordinary beat edge or smoother; the rest are up to 1.7x rougher, never more. The spike at 0.00 = beats that repeat the same bar exactly.", fontsize=10.5, color=INK)
save(fig, "08_cut_quality.png")

# =====================================================================================
# 09  v1 -> v2 (devlog numbers)
# =====================================================================================
fig, ax = plt.subplots(figsize=(9, 5))
headline(fig, "What the v2 engine fixed", "Share of jumps as smooth as an ordinary beat edge (<= 75th percentile). Measured by tools/splice_metric.py, an independent check.", 1.04)
fig.subplots_adjust(top=0.82)
labels = ["4.5-min rap track", "synthetic demo"]; v1 = [46, 21]; v2 = [86, 73]
x = np.arange(2); w = 0.34
b1 = ax.bar(x - w / 2, v1, w, color=MUTE, label="v1 (jump TO the twin, rigid grid, no fade)")
b2 = ax.bar(x + w / 2, v2, w, color=PINK, label="v2 (land after, tracked beats, ranked by cut cost, crossfade)")
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1.5, f"{r.get_height():.0f}%", ha="center", fontsize=13, fontweight="bold", color=INK)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=12); ax.set_ylim(0, 108); ax.set_ylabel("% of jumps"); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=1, labelcolor=INK)
save(fig, "09_v1_vs_v2.png")

# =====================================================================================
# 10  learned model AUC (devlog numbers)
# =====================================================================================
fig, ax = plt.subplots(figsize=(10, 5.2))
headline(fig, "Teaching it what a natural cut sounds like", "Leave-one-song-out on 5 tracks: the model never saw the song it was scored on. AUC 0.5 = coin flip, 1.0 = perfect.", 1.04)
fig.subplots_adjust(top=0.82)
names = ["plain distance\n(default engine)", "learned: absolute\nband differences", "learned: + direction,\nloudness, signed change"]
allv = [0.817, 0.834, 0.868]; hard = [0.774, 0.795, 0.838]
x = np.arange(3); w = 0.34
b1 = ax.bar(x - w / 2, allv, w, color=CYAN, label="all splices"); b2 = ax.bar(x + w / 2, hard, w, color=VIOLET, label="hard cases (the ones the engine actually picks from)")
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.006, f"{r.get_height():.3f}", ha="center", fontsize=11.5, fontweight="bold", color=INK)
ax.axhline(0.5, color=RED, lw=1.5, ls="--"); ax.text(2.6, 0.505, "chance", color=RED, fontsize=9.5, ha="right", va="bottom")
ax.set_ylim(0.45, 0.92); ax.set_xticks(x); ax.set_xticklabels(names, fontsize=10.5); ax.set_ylabel("AUC (separating real beat edges from random splices)")
ax.legend(loc="upper left", labelcolor=INK, fontsize=10)
save(fig, "10_learned_model.png")

# =====================================================================================
# 11  null + conflicting results (devlog numbers)
# =====================================================================================
fig, axs = plt.subplots(1, 3, figsize=(14, 4.6))
headline(fig, "What did NOT work (and where the measures disagree)", "Real results from docs/DEVLOG.md. Science includes the failures.", 1.08)
fig.subplots_adjust(top=0.76, wspace=0.3)
a = axs[0]
a.plot([0, 0.5, 1], [86, 85, 84], "o-", color=PINK, lw=2.5, ms=9, label="rap track"); a.plot([0, 0.5, 1], [73, 70, 70], "o-", color=CYAN, lw=2.5, ms=9, label="demo")
a.set_title("Matching the beat BEFORE the cut too", fontsize=11.5); a.set_xlabel("lead-in weight"); a.set_ylabel("% of jumps <= p75"); a.set_ylim(60, 95); a.set_xticks([0, 0.5, 1]); a.legend(fontsize=9.5, labelcolor=INK, loc="lower left")
a.text(0.5, 91.5, "no gain, slightly worse -> shipped OFF", ha="center", color=AMBER, fontsize=10)
a = axs[1]
lab = ["shorter\n(x2)", "auto", "longer\n(x0.5)"]; p75 = [86, 86, 78]; p90 = [96, 93, 87]
x = np.arange(3); w = 0.36
a.bar(x - w / 2, p75, w, color=PINK, label="<= p75"); a.bar(x + w / 2, p90, w, color=VIOLET, label="<= p90")
for i in range(3):
    a.text(i - w / 2, p75[i] + 1, p75[i], ha="center", fontsize=10, color=INK); a.text(i + w / 2, p90[i] + 1, p90[i], ha="center", fontsize=10, color=INK)
a.set_title("Fixing half- / double-time tempo (rap)", fontsize=11.5); a.set_xticks(x); a.set_xticklabels(lab); a.set_ylim(60, 115); a.legend(fontsize=9.5, labelcolor=INK, loc="upper right", ncol=2)
a = axs[2]
a.bar([0, 1], [86, 83], 0.5, color=[PINK, CYAN]); a.bar([2.2, 3.2], [73, 69], 0.5, color=[PINK, CYAN])
for xx, v in zip([0, 1, 2.2, 3.2], [86, 83, 73, 69]):
    a.text(xx, v + 1, f"{v}%", ha="center", fontsize=11, color=INK, fontweight="bold")
a.set_xticks([0.5, 2.7]); a.set_xticklabels(["rap track", "demo"]); a.set_ylim(55, 98)
a.set_title("Two yardsticks disagree", fontsize=11.5)
a.set_xlabel("pink = plain distance    cyan = learned model", fontsize=9.5)
a.text(0.5, 0.93, "learned wins on the classifier test,\nloses on the raw-difference test", transform=a.transAxes, ha="center", fontsize=9.5, color=AMBER, va="top")
save(fig, "11_negative_results.png")

# =====================================================================================
# 12  the vocal problem (devlog numbers)
# =====================================================================================
fig, ax = plt.subplots(figsize=(10, 4.8))
headline(fig, "The hard problem: cutting through the middle of a word", "Dense rap, first 240 s, 966 words timed with faster-whisper. A cut is mid-word if it lands more than 40 ms inside a word.", 1.06)
fig.subplots_adjust(top=0.78)
rows = [("ordinary beat boundaries", 73, MUTE), ("jumps: where we leave", 74, PINK), ("jumps: where we land (68-71%)", 70, PINK), ("jumps: either end", 89, RED)]
for k, (n, v, c) in enumerate(rows[::-1]):
    ax.barh(k, 100, color=GRID, height=0.55); ax.barh(k, v, color=c, height=0.55)
    ax.text(v + 1.2, k, f"{v}%", va="center", fontsize=13, fontweight="bold", color=INK)
ax.set_yticks(range(4)); ax.set_yticklabels([r[0] for r in rows[::-1]], fontsize=11); ax.set_xlim(0, 108); ax.set_xlabel("% of cuts that land mid-word")
fig.text(0.02, -0.06, "Meaning: the engine is word-blind. On rap, almost ANY beat cut is mid-word. An oracle that took only gap-to-gap jumps would keep ~11% of edges, so there is room to improve.",
        fontsize=9.6, color=AMBER, wrap=True, va="top")
save(fig, "12_vocal_problem.png")

# =====================================================================================
# 13  the crossfade, from real audio (data)
# =====================================================================================
XF = 0.02
best = min(edges, key=lambda e: e["s"])
ta, tb = beats[best["a"] + 1], beats[best["b"]]
def seg(t, n_before, n_after):
    i = int(t * SR); return y[i - n_before:i + n_after]
nx = int(XF * SR / 2)
ctx = int(0.012 * SR)
fig, axs = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True)
headline(fig, "Gluing two moments together without a click", "Real audio from the demo. Every join gets a 20 ms linear crossfade. The two gains always add up to 1, so a join in continuous audio is inaudible (devlog: a whole song re-rendered this way differs by ~3e-7).", 1.02)
fig.subplots_adjust(top=0.84, hspace=0.25)
tms = (np.arange(-ctx, ctx) / SR) * 1000
# top: an ordinary edge, split + fade + sum reproduces the original
t_ord = beats[40]
orig = seg(t_ord, ctx, ctx)
g_out = np.clip(1 - (tms + 10) / 20, 0, 1); g_in = 1 - g_out
a_part, b_part = orig * g_out, orig * g_in
err = np.abs((a_part + b_part) - orig).max()
axs[0].plot(tms, orig, color=MUTE, lw=2.6, label="original audio"); axs[0].plot(tms, a_part + b_part, color=GREEN, lw=1.2, ls="--", label="first half faded out + second half faded in")
axs[0].set_title("An ordinary beat edge: fading the halves out/in sums back to the original (transparent)", fontsize=11.5); axs[0].legend(fontsize=9.5, labelcolor=INK, loc="upper right")
# bottom: a jump
A = seg(ta, ctx, ctx); B = seg(tb, ctx, ctx)
axs[1].plot(tms, A * g_out, color=PINK, lw=1.4, label="where we were (fading out)"); axs[1].plot(tms, B * g_in, color=CYAN, lw=1.4, label="where we land (fading in)")
axs[1].plot(tms, A * g_out + B * g_in, color=INK, lw=2.2, label="what you hear")
ax2 = axs[1].twinx(); ax2.plot(tms, g_out, color=PINK, lw=1, ls=":"); ax2.plot(tms, g_in, color=CYAN, lw=1, ls=":"); ax2.set_ylim(-0.05, 3); ax2.set_yticks([]); ax2.spines["right"].set_visible(False)
axs[1].set_title(f"A real jump (beat {best['a'] + 1} -> beat {best['b']}): one sound melts into the next", fontsize=11.5); axs[1].legend(fontsize=9.5, labelcolor=INK, loc="upper right")
axs[1].set_xlabel("milliseconds around the cut  (dotted = the gain curves)")
for a_ in axs:
    a_.axvline(0, color=AMBER, lw=1, ls=":"); a_.set_yticks([])
save(fig, "13_crossfade.png")

# =====================================================================================
# 14  the jump chance (diagram of the rule)
# =====================================================================================
fig, ax = plt.subplots(figsize=(10, 4.2))
headline(fig, "Why the song keeps its shape", "The exact rule in the player: the chance of a jump starts low after each jump and grows with every beat played without one.", 1.05)
fig.subplots_adjust(top=0.76)
nb = np.arange(0, 33)
for lvl, col, lab in [(20, CYAN, "slider 20%"), (50, PINK, "slider 50% (default)"), (80, AMBER, "slider 80%")]:
    sl = lvl / 100
    ax.plot(nb, 100 * np.minimum(0.85, sl * 0.3 + 0.02 * nb * (0.4 + sl)), color=col, lw=2.6, label=lab)
ax.axhline(85, color=GRID, ls="--"); ax.text(0.3, 86.5, "hard cap 85%", color=MUTE, fontsize=9.5)
ax.set_xlabel("beats played since the last jump"); ax.set_ylabel("chance a jump fires on the next beat (%)"); ax.legend(labelcolor=INK, fontsize=10, loc="upper left", bbox_to_anchor=(0.0, 0.9))
ax.text(32, 4, "exact rule from index.html:  p = min(0.85, s*0.3 + 0.02 * beatsSinceJump * (0.4 + s)),  s = slider", ha="right", fontsize=8.8, color=MUTE)
save(fig, "14_jump_chance.png")
print("done")
