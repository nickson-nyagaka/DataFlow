# Kickoff prompts (paste into Antigravity, Planning mode)

## A. Phase 0 (first message ever)

You are the engineering agent for DATAFLOW. Before doing anything else:

1. Read `AGENTS.md` completely. It is binding.
2. Run `python scripts/gate_check.py`. It must report Phase 0 as the current phase. If not, stop and tell me.
3. Read `docs/00_MASTER_BRIEF.md`, the **Phase 0** section of `docs/PHASE_PLAN.md`, `docs/OPEN_QUESTIONS.md` and `docs/DECISION_LOG.md`.
4. Confirm `reference/OPTIMIZED_DATA_MGT.sanitized.ipynb` exists. If it does not, stop and ask me to place it there. Never use any other copy of the notebook.
5. Execute **Phase 0 only** (notebook audit, documentation only, no application code). Inspect every one of the 89 cells programmatically and read the executable code. Do not trust headings or comments. The pre-audited leads in the master brief (§5) are hypotheses: verify or refute each with evidence.
6. Work autonomously. Do not ask me about routine decisions. Put business-rule questions in `docs/OPEN_QUESTIONS.md`.
7. When every Phase 0 exit criterion is met, run `/phase-report` and **stop**. Do not begin Phase 1.

## B. Every later phase (only after I have approved the previous one)

Phase N has been approved by me; see `docs/gates/PHASE_APPROVALS.md`. Run `/phase-start` and execute only the phase the gate check allows. Work autonomously inside the phase. When all exit criteria are evidenced, run `/phase-report` and stop.

## C. After a rejection

I rejected Phase N. Read `docs/gates/REJECTIONS.md`. Run `/phase-start`. Fix only the listed defects, re-run the full suite for the phase, and resubmit with a delta report via `/phase-report`.
