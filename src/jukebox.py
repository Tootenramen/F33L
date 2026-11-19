"""F33L jukebox v0: build a beat-similarity jump graph, computed locally (ideas from the MIT-licensed
Infinite/Eternal Jukebox: beats described by timbre, pitch, loudness, position in bar; jump between similar beats).
Differences: no Spotify API (everything from the audio file), and every beat carries a feeling tag.
Usage: python jukebox.py song.mp3 --ffmpeg ffmpeg.exe --out web/graph.json
"""
import argparse, json, sys
import numpy as np
import listen as L


def beat_grid(flux, fps, bpm):
    """Beat times from the onset envelope: phase-align a grid at the given tempo (simple, robust)."""
    period = fps * 60.0 / bpm
    n = len(flux)
    best_phase, best_score = 0.0, -1.0
    for ph in np.arange(0, period, 1.0):
        idx = np.round(np.arange(ph, n, period)).astype(int)
        idx = idx[idx < n]
        s = flux[idx].sum()
        if s > best_score:
            best_phase, best_score = ph, s
    idx = np.round(np.arange(best_phase, n, period)).astype(int)
    return idx[idx < n] / fps


def beat_features(mag, y_len_s, fps, beats, c):
    """Per-beat vector: chroma (pitch), 12 log-spaced band energies (timbre), loudness."""
    freqs = np.fft.rfftfreq(L.N_FFT, 1 / L.SR)
    edges = np.geomspace(60, 9000, 13)
    bands = np.stack([mag[:, (freqs >= edges[i]) & (freqs < edges[i + 1])].sum(axis=1) for i in range(12)], axis=1)
    bands = np.log1p(bands)
    db = 20 * np.log10(np.sqrt((mag ** 2).mean(axis=1)) + 1e-9)
    cent = (mag * freqs).sum(axis=1) / (mag.sum(axis=1) + 1e-9)
    out = []
    bounds = np.append(beats, y_len_s)
    for i in range(len(beats)):
        a, b = int(bounds[i] * fps), max(int(bounds[i + 1] * fps), int(bounds[i] * fps) + 1)
        ch = c[a:b].mean(axis=0); ch = ch / (ch.sum() + 1e-9)
        tm = bands[a:b].mean(axis=0); tm = tm - tm.mean()
        out.append(dict(chroma=ch, timbre=tm, db=float(db[a:b].mean()), cent=float(cent[a:b].mean())))
    return out


def similarity_graph(feats, bar=4, threshold=0.35, min_gap=8, topk=4):
    """Distance between beats = timbre + pitch + loudness + same-position-in-bar penalty.
    Returns edges (i -> j) where distance < threshold (scaled), skipping near neighbours."""
    n = len(feats)
    T = np.stack([f["timbre"] for f in feats]); T = T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-9)
    C = np.stack([f["chroma"] for f in feats]); C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
    D = np.array([f["db"] for f in feats]); Dn = (D - D.mean()) / (D.std() + 1e-9)
    dt = 1 - T @ T.T
    dc = 1 - C @ C.T
    dd = np.abs(Dn[:, None] - Dn[None, :]) / 4.0
    pos = (np.arange(n)[:, None] % bar) != (np.arange(n)[None, :] % bar)
    dist = 0.5 * dt + 0.3 * dc + 0.2 * dd + 0.15 * pos
    np.fill_diagonal(dist, 9)
    # adaptive: keep the closest few beats per beat, and only if they are in the closest 3% of all pairs
    cut = min(threshold, float(np.percentile(dist[dist < 9], 3)))
    edges = []
    for i in range(n):
        order = np.argsort(dist[i])
        kept = 0
        for j in order:
            if dist[i, j] >= cut or kept >= topk:
                break
            if abs(int(j) - i) >= min_gap and j != i + 1:
                edges.append((i, int(j), float(dist[i, j])))
                kept += 1
    return edges


def feeling(db, cent, db_all, cent_all):
    """Cheap per-beat arousal/valence-ish proxies (to be replaced by learned models, see ROADMAP)."""
    arousal = float(np.clip((db - np.percentile(db_all, 10)) / (np.percentile(db_all, 90) - np.percentile(db_all, 10) + 1e-9), 0, 1))
    bright = float(np.clip((cent - np.percentile(cent_all, 10)) / (np.percentile(cent_all, 90) - np.percentile(cent_all, 10) + 1e-9), 0, 1))
    return arousal, bright


def build(y, bpm=None, threshold=0.35):
    mag = L.stft_mag(y)
    fps = L.SR / L.HOP
    freqs = np.fft.rfftfreq(L.N_FFT, 1 / L.SR)
    flux = np.concatenate([[0], np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)])
    bpm = bpm or L.tempo(flux)
    while bpm < 70: bpm *= 2
    while bpm > 160: bpm /= 2
    beats = beat_grid(flux, fps, bpm)
    c = L.chroma(mag)
    feats = beat_features(mag, len(y) / L.SR, fps, beats, c)
    edges = similarity_graph(feats, threshold=threshold)
    dball = np.array([f["db"] for f in feats]); cball = np.array([f["cent"] for f in feats])
    nodes = []
    for i, f in enumerate(feats):
        ar, br = feeling(f["db"], f["cent"], dball, cball)
        nodes.append(dict(i=i, t=round(float(beats[i]), 3), arousal=round(ar, 2), brightness=round(br, 2)))
    return dict(bpm=round(float(bpm), 1), beats=len(beats), nodes=nodes,
                edges=[dict(a=a, b=b, d=round(d, 3)) for a, b, d in edges])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio"); ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--out", default="web/graph.json"); ap.add_argument("--threshold", type=float, default=0.35)
    a = ap.parse_args()
    g = build(L.decode(a.audio, a.ffmpeg), threshold=a.threshold)
    import os; os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(g, open(a.out, "w"))
    print(f"{g['beats']} beats @ {g['bpm']} BPM, {len(g['edges'])} jump edges -> {a.out}")


if __name__ == "__main__":
    sys.exit(main())
