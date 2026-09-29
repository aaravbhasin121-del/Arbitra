# Arbitra — DOGFOOD 2026 Full Build

This package is the consolidated T1–T4 implementation. It is intended as the single project folder rather than a sequence of incremental zips.

## Run
```bash
docker compose down -v
docker compose up --build
```
Open http://localhost:8000

## Demo users
- organizer / organizer123
- judge_a / judge123
- judge_b / judge123
- participant / participant123

## Included
- T1: auth, roles, events, tracks, teams/invites, submission deadline enforcement, public gallery
- T2: judge assignments, weighted rubric, score isolation, progress, normalization endpoint, CSV export, audit model
- T3: voting, duplicate detection, rate limiting, hidden voting results, comments
- T4: REST API, webhook configuration, signed certificates, embeddable gallery, bulk export
- Bonus-oriented foundations: documented normalization, pairwise-ready architecture, threat/security documentation, API-first endpoints

## Acceptance
The supplied `run.py` and `fixtures.json` are included for local verification. Run:
```bash
python3 run.py .dogfood.toml > acceptance-report.txt
```
Run this while Docker is serving the app. The final report must be the actual output, not the placeholder currently committed.

## Important scope note
The DOGFOOD materials specify the required behavior but do not prescribe every implementation detail. The normalization formula and some T3/T4 policy details should be reviewed and documented before submission. Do not claim a feature merely because an endpoint exists; demo and test it.

## Judging Lab additions

Arbitra also includes the following auditable judging tools:

- **Score Receipts** — deterministic weighted score receipt with rubric version and hash.
- **Normalization Proof** — reproducible weighted score calculation and proof hash.
- **Judge Calibration Lab** — deterministic sample projects for pre-judging alignment.
- **What-if Judging** — hypothetical score adjustments that do not mutate stored results.
- **Assignment Health** — coverage and workload warnings.
- **Event Health** — operational readiness view.
- **Immutable Published Snapshot** — published results captured with a snapshot hash.
- **Local Acceptance Checker** — contract-style readiness checks for the demo environment.

These are additive product features; the DOGFOOD acceptance contract remains the source of truth for required checks.
