# PHASE <N> COMPLETION REPORT — <phase name>

Branch: `phase/<N>-<slug>` · Tag: `phase-<N>-submitted` · Date: <YYYY-MM-DD>

## 1. Summary (max 10 lines)
What was built, what was verified, what you need from the Owner.

## 2. Deliverables
| Path | Purpose |
|------|---------|

## 3. Exit-criteria checklist
Copy every criterion from docs/PHASE_PLAN.md. Each needs an evidence pointer (test name, report section or command).
- [ ] criterion — evidence: …

## 4. Raw test evidence
Paste unedited terminal output.
```
$ pytest -q
$ ruff check .
$ pytest --cov=core --cov=analytics   (Phase 4+)
```

## 5. Differences versus the notebook
| Item | Notebook behaviour | New behaviour | Class (BUG-FIX / BUSINESS-RULE-CHANGE / DEFECT / AMBIGUOUS) | Decision ID |
|------|--------------------|---------------|-----|-----|

## 6. Decisions made (IDs in DECISION_LOG.md)

## 7. Open questions raised / work BLOCKED by them

## 8. Risks and Not done
Be explicit. "Not done" is acceptable; hidden gaps are not.

## 9. How the Owner verifies this phase
Exact commands, expected outcomes, and what to eyeball. Real-file commands must be structure/aggregate-only.

## 10. Files changed
`git diff --stat <base>..HEAD`
