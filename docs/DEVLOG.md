# F33L devlog
Honest notes, including what did not work. Numbers are from one or two songs on one machine: hints, not benchmarks.

## 2026-11-19: why the loop "skipped halfway through a word"
A listener compared F33L with the Eternal Jukebox on the same song. The Eternal Jukebox sounded clean; F33L cut in the middle of words and lost the song's flow. Causes I found by reading my own code and the original's FAQ:
1. **Wrong landing.** After beat A I jumped *to* the matching beat B. It should be the beat *after* B, so the sound keeps flowing.
2. **Rigid beat grid.** A fixed grid at one tempo drifts away from the real hits, so cuts landed mid-sound.
3. **No crossfade** at the cut.
4. **Jumped too often**, so the song lost its shape.

Fixes shipped in v0.5.0 (see CHANGELOG). To check them without guessing I wrote `tools/splice_metric.py`, an independent proxy: it compares the real audio just before and after every cut and asks how it ranks against ordinary beat boundaries in the same song.

| | share of jumps as smooth as a normal beat edge (<= p75) |
|---|---|
| 4.5-min rap track, v1 | 46% |
| 4.5-min rap track, v2 | 86% |
| synthetic demo, v1 | 21% |
| synthetic demo, v2 | 73% |

Caveats: the engine and the proxy both measure "sound before vs after the cut", so they are related; snapping cuts to transients raises the baseline of ordinary boundaries, so absolute numbers are not comparable across versions; and no proxy hears a cut in the middle of a word.

Isolating just the landing fix (same old picks, same old grid): median splice roughness fell about 8% (rap track) and about 19% (demo). Modest on its own; most of the gain came from ranking jumps by the real splice cost.

## 2026-11-19: crossfade is transparent
Rendering the song straight through (no jumps) with the same crossfade logic reproduces the original audio: mean absolute difference about 3e-7. The 7 outliers out of the whole render are single samples at sharp drum hits (sub-sample rounding).

## 2026-11-19: negative result, phrase lead-in matching
Idea: also require the beat *before* the cut to match, so the phrase leading into the jump agrees. Tried weights 0, 0.5, 1.

| lead-in weight | rap track (<= p75) | demo (<= p75) |
|---|---|---|
| 0 | 86% | 73% |
| 0.5 | 85% | 70% |
| 1 | 84% | 70% |

No gain, slightly worse. Shipped off. The proxy may simply be saturated, which is why v0.6.0 adds listener feedback.

## 2026-11-19: ground truth has to be human
Because a mid-word cut is not visible in the numbers, v0.6.0 lets a listener label jumps (smooth / off). `tools/tune.js` then fits which measurements predict "off". Needs roughly 30 or more labels across several songs before it means anything.

## 2026-11-19: bug, YouTube fetch did nothing
The local helper never downloaded: yt-dlp treats `--print` as a dry run unless `--no-simulate` is set. The page also reported progress at the bottom, out of sight. Both fixed in v0.4.0.

## Earlier
- 2026-11-18: premise and principles (v0.1.0). First listening transcript and jump graph (v0.2.0). On a rap track the lyrics line up with the energy curve: the loud step at the first hook came at 86.9 s, about 8 dB above the verse.
- Key detection is unreliable on vocal-heavy music; tempo can be half or double. Known, not fixed.

## Next
- Collect labels across several songs and fit the cost weights.
- Vocal-aware cuts: prefer cutting in gaps or at word starts.
- Better timbre features, a tuning panel (threshold, delete jumps), and an accuracy comparison with the original on shared songs.
