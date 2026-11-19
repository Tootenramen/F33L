"""Word-level timestamps for a song (first N seconds), so we can MEASURE whether a cut lands inside a word.
Local only (faster-whisper on CPU). Output: outputs/words_<name>.json = [{start,end,w}, ...]. Outputs are git-ignored.
Usage: python words.py audio.mp3 name [--ffmpeg path] [--model base] [--seconds 240]"""
import argparse, json, os, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
ap = argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("name"); ap.add_argument("--ffmpeg", default="ffmpeg")
ap.add_argument("--model", default="base"); ap.add_argument("--seconds", type=int, default=240); a = ap.parse_args()
raw = subprocess.run([a.ffmpeg, "-v", "error", "-t", str(a.seconds), "-i", a.audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
y = np.frombuffer(raw, dtype=np.float32)
segs, info = WhisperModel(a.model, device="cpu", compute_type="int8").transcribe(y, word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
words = [dict(start=round(w.start, 3), end=round(w.end, 3), w=w.word.strip()) for s in segs for w in (s.words or [])]
os.makedirs("outputs", exist_ok=True); json.dump(words, open(f"outputs/words_{a.name}.json", "w"))
print(f"{a.name}: {len(words)} words, language={info.language}")
