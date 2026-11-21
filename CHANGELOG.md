# Changelog
All notable changes to F33L. Newest first. Versions are milestones; each links to the commit that closed it.

## v0.7.0 - 2026-11-19: learned cut scoring, switchable
- **Cut style switch** in the player: *smoothest* (plain distance, default) or *natural (learned)*. Labels now record which style you heard.
- **`continuity_model.js` + `tools/continuity.js`:** a small model trained to tell real beat edges from random splices. Leave-one-song-out on five tracks: mean AUC 0.817 to 0.868 (hard cases 0.774 to 0.838). My raw-difference proxy slightly prefers the plain distance, so it is opt-in until a listener decides. See DEVLOG.
- **Beat length control** (auto / shorter / longer) to fix half- or double-time readings; rebuilds the map instantly.
- `tools/make_graph.js --learned`; `tools/tune.js` also reads the learned score.

## v0.6.0 - 2026-11-19: teach it with your ears
- **Jump feedback in the player:** mark the jump you just heard as *smooth* or *off* (buttons, or press G / B). Off jumps are removed so they cannot play again. Labels stay in your browser and can be exported as a small JSON file (no audio).
- **`tools/tune.js`:** fits a tiny logistic regression on exported labels to show which measurement predicts a bad cut.
- Edges now carry the loudness jump (`l`) across the cut.
- Tried matching the beat *before* the cut too (phrase lead-in). Measured no gain, so it ships **off** (`history: 0`). See DEVLOG.
- Added a favicon.

## v0.5.0 - 2026-11-19: engine v2 ([8b9e474](../../commit/8b9e474))
- Dynamic-programming beat tracker that follows real onsets; every cut is snapped to the nearest transient.
- After beat A, land on the beat that *follows* a matching beat (not on the match itself).
- Jumps are ranked by a direct "splice smoothness" cost (sound just before the cut vs just after, relative to a normal beat edge).
- 20 ms crossfade on every beat edge (verified transparent for continuous audio) and a jump chance that builds slowly, like the original.
- Removed the Python graph builder; one engine (`analyze.js`) now serves both the page and the CLI (`tools/make_graph.js`).

## v0.4.0 - 2026-11-19: drop in any song, loop a link ([d22473e](../../commit/d22473e))
- Analysis runs in the browser: drop an audio or video file and it builds the beat map itself.
- Optional local helper (`src/serve.py`) for YouTube links via yt-dlp, 127.0.0.1 only, https YouTube links only.
- Fixed: the helper never downloaded (yt-dlp `--print` implies simulate; needs `--no-simulate`). Progress now shows next to the button.

## v0.3.0 - 2026-11-19: live demo ([916a205](../../commit/916a205))
- GitHub Pages site, hero image, README in the same style as the author's other projects, original synthetic demo track.

## v0.2.0 - 2026-11-18: first working prototypes ([f8e3826](../../commit/f8e3826))
- `listen.py`: a moment-by-moment listening transcript (loudness, brightness, rhythm density, tempo, key guess).
- First beat-similarity jump graph and browser player; lyric-timing alignment with faster-whisper; synthetic-audio tests.

## v0.1.0 - 2026-11-18: the question ([10d1cd4](../../commit/10d1cd4))
- Premise, research questions, principles and roadmap.
