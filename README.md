[![F33L: play any song forever, and every beat knows how it feels](docs/hero.png)](https://tootenramen.github.io/F33L/)

# F33L

**Play any song forever. It jumps between beats that sound alike, and every beat knows how it feels.**

An open experiment: can a computer learn how humans perceive and feel music? F33L measures the sound (tempo, key, pitch,
dynamics, texture), builds a map of which beats resemble each other, and tags every beat with its energy and brightness so
you can steer a song by feeling. Everything runs in your browser. Your audio never leaves your device.

**Live demo:** https://tootenramen.github.io/F33L/ (plays an original track made for F33L; load your own song too)

<img src="docs/preview.png" alt="F33L on a phone: the beat map, jump controls and feeling selector" width="300">

## What's inside

| Path | What it is |
|---|---|
| `index.html` | the jukebox player: drop a song, beat map, jump arcs, "stay in the feeling" modes |
| `analyze.js` | the in-browser listener: builds the beat graph from any audio (v2 engine: real beat tracking, transient-snapped cuts, splice-aware jump ranking) |
| `src/serve.py` | optional local helper for YouTube links (127.0.0.1 only) |
| `src/listen.py` | a moment-by-moment listening transcript for any song |
| `tools/` | `make_graph.js` (graph from a file) and `splice_metric.py` (an independent check of how smooth the jumps are) |
| `src/align.py` | lines up lyric timings with the energy curve |
| `src/make_demo.py` | generates the original demo track and its graph |
| `tests/` | synthetic-audio tests with known answers |
| `docs/` | the roadmap and screenshots |

## Use it
**On the website:** press **Try the demo song**, or drop in your own audio or video file (mp3, wav, m4a, mp4...). F33L listens to the song right in your browser (a few seconds), builds the beat map, and loops it forever. Nothing is uploaded.

**Loop a YouTube link (local only):** the public site cannot fetch videos, so this runs on your own computer.
1. Install Python, ffmpeg and yt-dlp (`winget install yt-dlp`, or `pip install yt-dlp`).
2. Run `python src/serve.py` and open http://127.0.0.1:8765/ (the helper prints the address; use `--port` if that one is taken).
3. Paste a link and press **Loop it**. The audio is fetched to a temporary file on your machine, analyzed in the page, then deleted.

For your own listening only. Respect the service's terms and the artist's rights; do not redistribute. The helper listens on 127.0.0.1 only and accepts only https YouTube links.

**Teach it what sounds right:** while a song plays, press **G** (that jump was smooth) or **B** (it was off), or use the buttons. Off jumps are removed so they can't play again. Export your labels as a small JSON file (no audio) and `node tools/tune.js f33l-labels.json` shows which measurements predict a bad cut.

**Power users:** `node tools/make_graph.js song.mp3 out.json --ffmpeg ffmpeg` builds the same graph the page builds.

Follow the work: [CHANGELOG](CHANGELOG.md) (versions) and [docs/DEVLOG.md](docs/DEVLOG.md) (what was measured, what failed).

## How the jumps are chosen
Looping a song without it sounding broken is mostly about *where you cut*. F33L v2 does this:
1. **Real beats.** A dynamic-programming beat tracker follows the song's actual onsets, then each cut is snapped to the nearest transient, so cuts land on the start of a sound instead of in the middle of one.
2. **Land one beat after the match.** After beat A, jump to the beat that *follows* a beat that sounds like A, so the music keeps flowing.
3. **Rank by how the cut actually sounds.** Every candidate jump is scored by comparing the sound just before the cut with the sound just after it, against how rough a normal beat boundary is in the same song.
4. **Crossfade every edge** by 20 ms (provably transparent when the audio is continuous), and **let the jump chance build slowly**, like the original, so the song keeps its shape.

Measured on one real track (not a promise for every song): the share of jumps as smooth as an ordinary beat edge went from **46% to 86%** on a 4.5-minute rap track and from **21% to 73%** on the synthetic demo, using `tools/splice_metric.py`, which measures the real audio around each cut with different windows than the engine uses. That is a proxy. Whether it *sounds* seamless is a listening test, and vocals (a cut in the middle of a word) are still the hardest case.

## The idea
1. **Measure the sound.** Turn audio into interpretable features: tempo, meter, key and mode, chord motion, melodic contour, register, dynamics, spectral brightness, roughness, texture, silence.
2. **Map to emotion.** Link those features to emotion using published music-psychology models (valence-arousal, discrete emotions, expectation and tension/release) instead of ad hoc guesses.
3. **Explain.** Give an AI a structured, readable "score card" it can reason over, and have it say *why* a song is likely to feel the way it does.
4. **Test against people.** Compare predictions to human ratings. Report where it is right, where it is wrong, and where listeners disagree with each other.

## Research questions
- Which features carry the most emotional signal, and how much of it is universal vs cultural or personal?
- Can a language model, given only a feature report, predict human valence/arousal better than a plain audio classifier?
- Does adding music-theory knowledge (modes, cadences, tension) improve both accuracy and explanations?
- How should a system express uncertainty when listeners genuinely disagree?
- What can a system *not* know about a person's experience (memory, context, culture)?

## Approach (v0 sketch)
- Python feature extraction (candidates: librosa, essentia, madmom) producing a versioned JSON report per track.
- Baselines: simple regression/classifiers on public emotion-annotated datasets.
- LLM layer: reads the report, predicts emotion with confidence and a short rationale.
- Evaluation: held-out human ratings, agreement between raters as the ceiling, and calibration of confidence.

## Candidate public resources (check each license before use)
- Valence-arousal circumplex (Russell) and GEMS music emotion scales.
- Annotated datasets such as DEAM, PMEmo and MTG-Jamendo mood/theme tags.
- Key-finding profiles (Krumhansl-Schmuckler) and standard chord/key detection methods.

## Principles
- **Open.** Apache-2.0. Methods, data processing and results are published, including negative results.
- **Honest.** No claim without a measurement. Report uncertainty and disagreement.
- **Respectful of music and listeners.** Use only audio and data we are licensed to use. Do not redistribute copyrighted recordings. Human listening studies need consent and privacy.
- **People first.** The goal is to help people connect with music and with each other, not to replace listening.

## Status
Early, working prototypes (all local; audio never leaves your machine; needs ffmpeg + numpy):
- `src/listen.py`: a moment-by-moment "listening transcript" (loudness, brightness, rhythmic density, tempo, key guess per section).
- `src/align.py`: lines up lyric timings (faster-whisper) with the energy curve. Outputs stay in the git-ignored `outputs/`; do not publish lyrics of copyrighted songs.
- `analyze.js` + `index.html`: a locally computed beat-similarity jump graph (`analyze.js`) and a browser player that plays a song forever by jumping between beats that sound alike, with per-beat energy/brightness tags and a "stay in the feeling" mode. Inspired by the MIT-licensed Infinite/Eternal Jukebox (no Spotify API needed here).
- `tests/`: synthetic-audio tests (known key, known tempo, cuts landing on clicks). Run: `python -m unittest discover tests` and `node --test tests/analyze.test.js`.

Known limits: key detection is unreliable on rap/vocal-heavy music; tempo can be half/double; the per-beat "feeling" tags are simple energy/brightness proxies, not a validated emotion model; the browser player has not yet had a listening test on real tracks.

## Contributing
Musicians, music theorists, psychologists, audio engineers and ML people are all welcome. Open an issue with a question, a paper, a dataset or a critique.

---
Built by [Gustavo Freitas](https://github.com/Tootenramen) - [LinkedIn](https://www.linkedin.com/in/gustavo-freitas-69b93910b/) - [more projects](https://github.com/Tootenramen)
