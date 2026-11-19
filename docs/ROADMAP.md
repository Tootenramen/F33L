# F33L roadmap (draft)

- **M0 Question and principles:** this repo. Done on day zero.
- **M1 Feature report:** one command turns an audio file into a readable JSON report (tempo, key/mode, chords, register, dynamics, texture). Tests on synthetic audio with known answers (a C major scale must report C major).
- **M2 Baseline:** train simple models on a public emotion dataset; publish accuracy and the rater-agreement ceiling.
- **M3 LLM layer:** model reads the report, predicts valence/arousal with confidence and a rationale. Compare with M2.
- **M4 Human study:** small, consented listening study to test where the system and people disagree.
- **M5 Write-up:** publish methods, results and failures.

Rule: each milestone ships with tests or measurements, and unproven claims stay out of the README.
