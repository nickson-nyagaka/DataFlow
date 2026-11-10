---
description: Finish the current phase, produce the completion report, and stop
---
1. Re-run `python scripts/gate_check.py N` to confirm N is still the allowed phase.
2. Run `ruff check .`, `ruff format --check .`, and the full `pytest` suite (with coverage from Phase 4). Capture the raw terminal output.
3. Walk the Phase N exit-criteria checklist in `docs/PHASE_PLAN.md`. Tick a box only with evidence. If any box cannot be ticked, either fix it or list it under "Not done"; in that case do NOT submit unless the Owner has previously accepted that gap in `docs/DECISION_LOG.md`.
4. Copy `docs/templates/COMPLETION_REPORT.md` to `docs/reports/PHASE_N_REPORT.md` and fill every section. Paste raw output; do not paraphrase.
5. Update `docs/DECISION_LOG.md`, `docs/OPEN_QUESTIONS.md`, `docs/PROGRESS.md` (Phase N = SUBMITTED).
6. Commit; tag `phase-N-submitted`. Do not tag anything as approved. Do not edit `docs/gates/PHASE_APPROVALS.md`.
7. Final message: a 10-line summary, the path to the report, then exactly:
   `PHASE N SUBMITTED — awaiting Owner approval. I will not start Phase N+1.`
8. Stop. Take no further action.
