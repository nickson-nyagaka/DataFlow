---
description: Finish the active work package, write the report, and stop
---
1. Re-run `python scripts/gate_check.py <id>` to confirm the WP is still the allowed one.
2. Run `ruff check .`, `ruff format --check .`, the full `pytest` suite, the golden tests and the oracle comparison. Capture raw output. For FIX/ENHANCE, confirm golden output is unchanged unless `golden_update: allowed`.
3. For STRESS WPs, confirm `git diff --stat <baseline_tag>..HEAD` shows **no changes to read-only paths**. If it does, revert those changes and note it.
4. Walk the exit-criteria checklist in `docs/WORK_PACKAGE_SPECS.md`. Tick only with evidence; list gaps under coverage.
5. Copy `docs/templates/WP_REPORT.md` to `docs/reports/WP_<id>_REPORT.md` and fill every section with raw output.
6. Update `docs/stress/FINDINGS.md`, `docs/PROPOSED_WORK.md`, `docs/DECISION_LOG.md`, `docs/OPEN_QUESTIONS.md`.
7. Commit; tag `wp-<id>-submitted`. Do not edit `docs/gates/WORK_PACKAGES.md`.
8. Final message: 10-line summary, the report path, then exactly:
   `WP <id> SUBMITTED — awaiting Owner approval. I will not start another work package.`
9. Stop.
