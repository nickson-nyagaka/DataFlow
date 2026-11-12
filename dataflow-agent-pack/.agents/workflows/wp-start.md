---
description: Start (or resume) the one work package the Owner has activated
---
1. Run `python scripts/gate_check.py`. Note the WP id, type and golden_update flag. If it prints BLOCKED, GATE ERROR, BASELINE TAG MISSING or NO ACTIVE WORK PACKAGE, stop and tell the Owner.
2. Read, in order: `AGENTS.md`, the WP's section in `docs/WORK_PACKAGE_SPECS.md`, `docs/DECISION_LOG.md`, `docs/OPEN_QUESTIONS.md`, `docs/stress/FINDINGS.md`, and `docs/gates/REJECTIONS.md` if rework.
3. Inspect repository state (`git status`, `git log --oneline -n 15`). Confirm the baseline tag exists and the full test suite is green **before changing anything**; record that baseline result.
4. Create or switch to branch `wp/<id>-<slug>`.
5. Plan: test designs, tooling, resource guards, seeds, what you will not cover. Proceed without waiting for plan approval.
6. Work inside the allowed paths for the WP type (AGENTS.md section 3). Commit small and often.
7. If you notice work outside the WP, add it to `docs/PROPOSED_WORK.md` and move on.
8. When every exit criterion is evidenced, run `/wp-report`.
