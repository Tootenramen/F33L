"""Generate F33L's original demo track (synthetic, ours, no copyright issues) and its beat graph.
Usage: python make_demo.py --ffmpeg path\to\ffmpeg.exe   -> demo/demo.mp3   (then: node tools/make_graph.js demo/demo.mp3 demo/graph.json)
"""
import argparse, json, subprocess, wave, os
import numpy as np

SR, BPM = 22050, 105
BEAT = 60.0 / BPM
def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def note(f, dur, vol=0.2, harm=4, atk=0.01):
    t = np.arange(int(SR * dur)) / SR
    y = sum(np.sin(2 * np.pi * f * (h + 1) * t) / (h + 1) ** 1.3 for h in range(harm))
    env = np.minimum(1, t / atk) * np.exp(-1.2 * t / max(dur, .1))
    return (y * env * vol).astype(np.float32)
def place(buf, sig, t):
    i = int(t * SR); buf[i:i + len(sig)] += sig[:max(0, len(buf) - i)]
def drum(kind, n=0):
    rs = np.random.RandomState(n)
    if kind == "kick":
        t = np.arange(int(SR * .18)) / SR; return (np.sin(2 * np.pi * (110 * np.exp(-t * 25) + 40) * t) * np.exp(-t * 18) * .6).astype(np.float32)
    t = np.arange(int(SR * .06)) / SR; return (rs.randn(len(t)) * np.exp(-t * 70) * .12).astype(np.float32)

PROG = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G
BARS_PER_CHORD, REPEATS = 1, 6
total_bars = len(PROG) * BARS_PER_CHORD * REPEATS
y = np.zeros(int((total_bars * 4 * BEAT + 2) * SR), dtype=np.float32)
for bar in range(total_bars):
    root, chord = PROG[bar % 4]
    t0 = bar * 4 * BEAT; layer = bar // 4   # 0 calm pad, 1 +bass, 2-3 +arp +drums, 4-5 +lead and lift
    for n in chord: place(y, note(midi(n), 4 * BEAT, .09, 3, .08), t0)
    if layer >= 1:
        for b in range(4): place(y, note(midi(root - 12), BEAT * .9, .22, 2), t0 + b * BEAT)
    if layer >= 2:
        for k in range(8): place(y, note(midi(chord[k % 3] + 12), BEAT * .5, .09, 3), t0 + k * BEAT / 2)
        for b in range(4):
            place(y, drum("kick"), t0 + b * BEAT)
        for k in range(8): place(y, drum("hat", k), t0 + k * BEAT / 2 + BEAT / 4)
    if layer >= 4:
        mel = [chord[2] + 24, chord[1] + 24, chord[2] + 24, chord[0] + 24]
        for b in range(4): place(y, note(midi(mel[b]), BEAT * .95, .16, 5), t0 + b * BEAT)
y = np.tanh(y * 1.4).astype(np.float32)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--ffmpeg", default="ffmpeg"); a = ap.parse_args()
    os.makedirs("../demo", exist_ok=True)
    with wave.open("../demo/_tmp.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32000).astype(np.int16).tobytes())
    subprocess.run([a.ffmpeg, "-y", "-v", "error", "-i", "../demo/_tmp.wav", "-b:a", "96k", "../demo/demo.mp3"], check=True)
    os.remove("../demo/_tmp.wav")
    print(f"demo: {len(y)/SR:.1f}s -> demo/demo.mp3")
