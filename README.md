# F33L

**An open experiment: can a computer learn how humans perceive and feel music?**

Music theory describes how tones, rhythm, pitch, key and timbre combine to produce a particular emotion in the human ear and brain. People can feel it. Software can measure it. F33L is the attempt to connect the two: to build an open system that lets AI models (language models, agents, analysis tools) *infer* the emotional experience of a piece of music, and then test those inferences against what real humans report.

> Honest framing: a model can read the structure of music and predict likely emotional effect. Whether that is "understanding" or "feeling" is the open question this project explores, not a claim it makes.

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
Day zero. This repo is the starting line: the question, the plan and the principles. Nothing here is validated yet.

## Contributing
Musicians, music theorists, psychologists, audio engineers and ML people are all welcome. Open an issue with a question, a paper, a dataset or a critique.
