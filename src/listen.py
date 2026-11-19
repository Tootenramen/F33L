"""F33L listen v0: turn an audio file into a moment-by-moment listening transcript.

Needs only ffmpeg on PATH (or --ffmpeg) and numpy. Local analysis; no audio leaves the machine.
Usage: python listen.py song.mp3 [--ffmpeg path\\to\\ffmpeg.exe] [--out report.json]
"""
import argparse, json, subprocess, sys
import numpy as np

SR = 22050
N_FFT, HOP = 2048, 512
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Kessler key profiles
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def decode(path, ffmpeg):
    cmd = [ffmpeg, "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def stft_mag(y):
    win = np.hanning(N_FFT)
    n = 1 + (len(y) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(y[idx] * win, axis=1))  # (frames, bins)


def chroma(mag):
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    ok = (freqs >= 55) & (freqs <= 2000)
    pc = (np.round(12 * np.log2(freqs[ok] / 440.0) + 69).astype(int)) % 12
    c = np.zeros((mag.shape[0], 12))
    for k in range(12):
        c[:, k] = mag[:, ok][:, pc == k].sum(axis=1)
    return c


def best_key(c):
    v = c.sum(axis=0)
    best = (-2, None)
    for k in range(12):
        for name, prof in (("major", MAJ), ("minor", MIN)):
            r = np.corrcoef(v, np.roll(prof, k))[0, 1]
            if r > best[0]:
                best = (r, f"{NOTES[k]} {name}")
    return best[1], float(best[0])


def tempo(flux):
    f = flux - flux.mean()
    ac = np.correlate(f, f, mode="full")[len(f) - 1:]
    fps = SR / HOP
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
    lag = lo + int(np.argmax(ac[lo:hi]))
    return 60.0 * fps / lag


def describe(db, bright, onset, db_all, br_all, on_all):
    e = "loud" if db > np.percentile(db_all, 75) else "quiet" if db < np.percentile(db_all, 25) else "mid-energy"
    b = "bright/harsh" if bright > np.percentile(br_all, 75) else "dark/muffled" if bright < np.percentile(br_all, 25) else "balanced"
    r = "dense, driving" if onset > np.percentile(on_all, 75) else "sparse, spacious" if onset < np.percentile(on_all, 25) else "steady"
    return f"{e}, {b}, {r}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--out")
    ap.add_argument("--seg", type=float, default=15.0, help="seconds per section")
    a = ap.parse_args()

    y = decode(a.audio, a.ffmpeg)
    mag = stft_mag(y)
    fps = SR / HOP
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    rms = np.sqrt((mag ** 2).mean(axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    cent = (mag * freqs).sum(axis=1) / (mag.sum(axis=1) + 1e-9)
    flux = np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    c = chroma(mag)

    key, conf = best_key(c)
    bpm = tempo(flux)
    seg = int(a.seg * fps)
    nseg = len(db) // seg
    secs = []
    for i in range(nseg):
        s = slice(i * seg, (i + 1) * seg)
        thr = flux[s].mean() + flux[s].std()
        onsets = int(((flux[s][1:-1] > flux[s][:-2]) & (flux[s][1:-1] > flux[s][2:]) & (flux[s][1:-1] > thr)).sum())
        secs.append(dict(t=i * a.seg, db=float(db[s].mean()), brightness_hz=float(cent[s].mean()),
                         onsets_per_s=onsets / a.seg, key=best_key(c[s])[0]))
    dball = np.array([x["db"] for x in secs]); brall = np.array([x["brightness_hz"] for x in secs])
    onall = np.array([x["onsets_per_s"] for x in secs])
    for x in secs:
        x["feel"] = describe(x["db"], x["brightness_hz"], x["onsets_per_s"], dball, brall, onall)

    rep = dict(file=a.audio, duration_s=len(y) / SR, tempo_bpm=round(bpm, 1), tempo_note="half/double-time ambiguity is common",
               key=key, key_confidence=round(conf, 2), loudness_range_db=float(np.percentile(db, 95) - np.percentile(db, 5)),
               sections=secs)
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=2)
    print(f"LISTENING TRANSCRIPT  ({rep['duration_s']:.0f}s)")
    print(f"tempo ~{rep['tempo_bpm']} BPM (could be half/double) | key guess: {key} (r={conf:.2f}) | dynamic range {rep['loudness_range_db']:.1f} dB")
    for x in secs:
        m, s = divmod(int(x["t"]), 60)
        print(f"{m}:{s:02d}  {x['db']:6.1f} dB  {x['brightness_hz']:5.0f} Hz  {x['onsets_per_s']:.1f} hits/s  {x['key']:<9}  {x['feel']}")


if __name__ == "__main__":
    sys.exit(main())
