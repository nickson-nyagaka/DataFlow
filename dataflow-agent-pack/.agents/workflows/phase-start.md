---
description: Start (or resume) the one phase the gate allows
---
1. Run `python scripts/gate_check.py`. Note the allowed phase N. If it prints BLOCKED or GATE ERROR, stop and tell the Owner.
2. Read, in this order: `AGENTS.md`, `docs/00_MASTER_BRIEF.md`, the Phase N section of `docs/PHASE_PLAN.md`, `docs/OPEN_QUESTIONS.md`, `docs/DECISION_LOG.md`, and `docs/gates/REJECTIONS.md` if Phase N was rejected.
3. Inspect the repository state (`git status`, `git log --oneline -n 15`, the tree). Never assume what exists.
4. Create or switch to branch `phase/N-<slug>`.
5. Write an implementation plan covering files to create or change (all inside the phase's *May touch* list), tests to write first, risks, and which open questions block what. Do not wait for approval of the plan; proceed.
6. Set Phase N to IN PROGRESS in `docs/PROGRESS.md`.
7. Implement in small commits. Run `ruff check .` and `pytest -q` often. Fix failures at the cause.
8. Stay inside the phase. If you notice work that belongs to a later phase, note it in `docs/PROGRESS.md` under "Later" and move on.
9. When every exit criterion is evidenced, run `/phase-report`.
