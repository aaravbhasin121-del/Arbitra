# Architecture

Browser -> FastAPI -> SQLite.

Planned modules: auth, events, teams, submissions, gallery, judge assignment, rubric, scoring, normalization, results, audit, export.

Authorization is enforced at API endpoints; frontend hiding is not a security boundary.
