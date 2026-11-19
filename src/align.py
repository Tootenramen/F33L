"""F33L align v0: line up lyric timings (faster-whisper) with the energy curve from listen.py.
Local only. Output goes to outputs/ (git-ignored); do not commit lyrics of copyrighted songs.
Usage: python align.py song.mp3 --ffmpeg path\\to\\ffmpeg.exe [--model small] [--out outputs/x.json]
"""
import argparse, json, sys
import numpy as np
from faster_whisper import WhisperModel
import listen as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--model", default="small")
    ap.add_argument("--out", default="outputs/align.json")
    a = ap.parse_args()

    y = L.decode(a.audio, a.ffmpeg)
    mag = L.stft_mag(y)
    fps = L.SR / L.HOP
    freqs = np.fft.rfftfreq(L.N_FFT, 1 / L.SR)
    db = 20 * np.log10(np.sqrt((mag ** 2).mean(axis=1)) + 1e-9)
    cent = (mag * freqs).sum(axis=1) / (mag.sum(axis=1) + 1e-9)

    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    import subprocess
    raw = subprocess.run([a.ffmpeg, "-v", "error", "-i", a.audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    wav16 = np.frombuffer(raw, dtype=np.float32)  # decode ourselves: avoids a PyAV version clash
    segs, info = model.transcribe(wav16, language="en", vad_filter=False, word_timestamps=False,
                                  condition_on_previous_text=False)
    rows = []
    for s in segs:
        i0, i1 = int(s.start * fps), max(int(s.end * fps), int(s.start * fps) + 1)
        rows.append(dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip(),
                         db=float(db[i0:i1].mean()), brightness_hz=float(cent[i0:i1].mean())))
    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(dict(file=a.audio, language=info.language, segments=rows), open(a.out, "w"), indent=2)
    print(f"{len(rows)} segments -> {a.out}")


if __name__ == "__main__":
    sys.exit(main())
