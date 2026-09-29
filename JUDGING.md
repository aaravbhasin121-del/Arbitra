# Judging

Judges can retrieve only their own scores. Participants are denied judge-score access. Organizers can export judging data.

Planned engine: weighted rubric, assignments, scoring, completion tracking, backend peer-score isolation, documented normalization, final results, CSV export.

The DOGFOOD materials require a documented/defensible normalization method but do not prescribe one exact formula; the final implementation must document the selected method.


## Arbitra Judging Lab

### Score Receipt
Each submitted project score set is stored with the rubric version, weighted total, canonical JSON payload, and SHA-256 receipt hash. Editing a score replaces the judge/project score set so the current state remains deterministic.

### Normalization Proof
Arbitra converts each completed judge's rubric score into a 0–100 weighted score, then takes the arithmetic mean across completed judges for the project. The run stores the method, rubric, per-judge values, results, and a SHA-256 proof hash.

### What-if Judging
The UI can apply hypothetical deltas to stored receipt totals for exploration. It never writes those hypothetical values to the database.

### Calibration Lab
The UI includes three deterministic sample projects so judges can compare scoring disagreement before live judging.

### Publication Snapshot
Publishing requires a normalization run. Arbitra stores the normalized result set and a SHA-256 snapshot hash, creating a reproducible publication artifact.
