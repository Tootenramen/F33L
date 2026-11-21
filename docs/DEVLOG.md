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

## 2026-11-19 (later): learning what a natural cut sounds like
Idea: real beat boundaries in a song are examples of continuity, and random splices are examples of breaks. Train a model on the difference between the sound just before and just after a cut, then use it to score candidate jumps. Tested **leave-one-song-out** on five different tracks (a rap track, two ambient/electronic pieces, a children's TV album and a lullaby; 4 minutes each), so the model never saw the song it was scored on. Metric: AUC of separating random splices from ordinary beat edges (0.5 = chance).

| feature set | mean AUC, all splices | mean AUC, hard cases only* |
|---|---|---|
| plain Euclidean distance (what v0.5/v0.6 use) | 0.817 | 0.774 |
| learned, absolute band differences | 0.834 | 0.795 |
| learned, adds direction, loudness level and signed band change | **0.868** | **0.838** |

*hard cases: only splices the plain distance already thinks are fairly smooth, which is the regime the engine picks from.
The richer model won on all five held-out songs. The rap track went from 0.705 to 0.814.

**But the two proxies disagree.** When I rebuilt the rap track with a model that never saw it and re-ran `tools/splice_metric.py` (raw spectral/loudness difference across the cut), the learned ranking scored *slightly lower* than the plain-distance ranking: 83% vs 86% of jumps as smooth as a normal beat edge (demo: 69% vs 73%). Plausible reason: that metric rewards the smallest difference, while real beat edges at drum hits legitimately differ a lot, and the learned model has learned that. Neither proxy is ears.

Decision: ship both, **default stays the plain distance** (the version a listener already judged "better but not perfect"), and add a **Cut style** switch (smoothest / natural-learned) so a listener can A/B them. Labels record which style was playing, so the next fit can tell which one produces fewer "off" jumps. The model is `continuity_model.js` (77 weights, trained by `tools/continuity.js` on the five local tracks; no audio is stored in the repo).

Caveats: five songs, one machine, negatives are random splices (some of which are fine), and the positive class is "ordinary beat edge", not "sounds good".

## 2026-11-19 (later still): half/double-time control
The tempo estimate can land on half or double the felt tempo on rap and vocal music (roadmap issue on this). Added a **Beat length** switch (auto / shorter / longer). On the rap track (smooth-jump share, same proxy as above): shorter beats (x2, 157 BPM, 706 beats) 86% of jumps <= p75 and 96% <= p90, with about twice as many jump options; auto (78 BPM) 86% / 93%; longer (x0.5) 78% / 87%. So shorter beats lose nothing on the proxy and give finer cut points; auto stays the default until a listener says which sounds better.

## Mid-word cuts, measured (first look)
Word timestamps (faster-whisper base, tools/words.py) + tools/midword.js on Revenge (dense rap, first 240 s, 966 words).
A cut is "mid-word" if it is >40 ms inside a word. Result: 73% of ordinary beat boundaries already fall inside a word;
jumps land mid-word at the same rate (source 74%, landing 68-71%, either end 89%) in BOTH distance and learned modes.
Meaning: the engine is currently blind to words, as suspected; on rap almost any beat cut is mid-word, so it needs a
vocal-aware term. An oracle that only takes gap-to-gap jumps would leave ~11% of edges, so there is room. Next: an
audio-only proxy for "this boundary is in a word gap" (voice-band level at the cut), validated against these labels.

## Reading EternalBox's source, and an "eternal" style (opt-in, `style:'eternal'`)
What the original does (go-js.html / jremix.js): Spotify's analysis supplies beats AND sound segments (timbre 12, pitch 12, loudness start/max,
duration, confidence). Two beats are compared by the SEQUENCE of segments inside them, index by index: timbre + 10x pitch + loudness + 100x duration
(Spotify units), plus a hard penalty if the beats sit at different places in their bar. Threshold is raised until ~1/6 of the beats have a
branch, max 4 branches per beat, one extra long backward branch, jump chance ramps up between jumps. Playback cuts exactly on Spotify beat boundaries.
We mirror that with our own onset segmenter + segment descriptors (no Spotify data). Measured on Revenge (word timestamps):
word-consistent jumps (neither end inside a word, or both inside the SAME word at the same point +-70 ms): distance 15%, learned 15.5%, eternal 18%.
Mid-word rate is unchanged (~75% source, ~70% landing): in dense rap almost any cut is inside a word, so segment matching alone cannot avoid it.

### Results, three vocal tracks with word timestamps (Revenge, Bluey, PuppyCat; Kick Me transcribed to 0 words, unusable)
word-consistent jumps: distance 15% / 68% / 41%; learned 16% / 64% / 40%; eternal+smooth 18% / 71% / 43%; plain eternal 18% / 72% / 30%.
So eternal+smooth is >= distance on all three, by small margins; plain eternal is worse on PuppyCat. Independent splice proxy (% as smooth as a
natural edge, p75): Revenge 80 -> 71, Bluey 30 -> 39, PuppyCat 81 -> 83: mixed. Shipped as the opt-in "Eternal-style" cut style, default unchanged.
Negative results: waveform fine-alignment of the landing (+-50 ms, NCC before and after the cut) changed word-consistency by +-0.3 points;
matching the lead-in (history 1-2) lowered it slightly (15.0 -> 14.8 / 14.4); loudness at the boundary cannot tell a word gap from a word
(AUC 0.53 and 0.50, because the instrumental is mixed in), so no cheap audio-only gap detector exists yet. A vocal-isolation model
(e.g. a source separator) would be the next real lever, and it is a heavy dependency.
