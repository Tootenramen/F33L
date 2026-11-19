"""Synthetic-audio tests: every expected answer is known because we made the sound."""
import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import listen as L
import jukebox as J

SR = L.SR
def tone(freq, dur, harmonics=3):
    t = np.arange(int(SR * dur)) / SR
    return sum(np.sin(2 * np.pi * freq * (h + 1) * t) / (h + 1) for h in range(harmonics)).astype(np.float32) * 0.3

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

class Key(unittest.TestCase):
    def key_of(self, notes_weights):
        y = np.concatenate([tone(midi(n), 0.5 * w) for n, w in notes_weights for _ in range(4)])
        return L.best_key(L.chroma(L.stft_mag(y)))[0]
    def test_c_major(self):  # C major scale, tonic and dominant held longer
        self.assertEqual(self.key_of([(60, 3), (62, 1), (64, 2), (65, 1), (67, 2), (69, 1), (71, 1), (72, 2)]), "C major")
    def test_a_minor(self):  # A natural minor, tonic and fifth held longer
        self.assertEqual(self.key_of([(57, 3), (59, 1), (60, 2), (62, 1), (64, 2), (65, 1), (67, 1), (69, 2)]), "A minor")

class Tempo(unittest.TestCase):
    def test_click_120(self):
        y = np.zeros(SR * 20, dtype=np.float32)
        for b in range(40):
            i = int(b * 0.5 * SR); y[i:i + 400] += np.random.RandomState(b).randn(400).astype(np.float32)
        mag = L.stft_mag(y); flux = np.concatenate([[0], np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)])
        self.assertAlmostEqual(L.tempo(flux), 120, delta=4)

class Graph(unittest.TestCase):
    def test_repeating_bar_links_same_position(self):
        rs = np.random.RandomState(1)
        bar = [tone(f, 0.5) + 0.0 for f in (220, 330, 440, 660)]  # four distinct sounds per bar, 120 BPM
        y = np.concatenate(bar * 16)
        g = J.build(y, bpm=120, threshold=0.35)
        self.assertGreater(len(g["edges"]), 20)
        for e in g["edges"]:
            self.assertEqual((e["a"] - e["b"]) % 4, 0)       # only same bar position
            self.assertGreaterEqual(abs(e["a"] - e["b"]), 8)   # never trivial neighbours
        for nd in g["nodes"]: self.assertTrue(0 <= nd["arousal"] <= 1)

if __name__ == "__main__":
    unittest.main()
