# DECISION LOG

Classes: BUG-FIX · BUSINESS-RULE-CHANGE (Owner-approved only) · DEFECT · AMBIGUOUS · TECHNICAL

| ID | Decision | Reason | Affected modules | Date | Status |
|----|----------|--------|------------------|------|--------|
| D-001 | NSP is a required component of the **general** Defined Package pathway for PWID only. FSW, MSM, TG, VP: NSP is not required. | Owner rule. NOTE: the notebook (cell 61) has every `nsp_q*` requirement commented out in both pathways, so this is a BUSINESS-RULE-CHANGE; expected diffs vs the notebook must be classified, not hidden. | analytics/defined_package, config/populations/*.yaml | 2026-11-10 | OWNER-CONFIRMED |
| D-002 | Viral-load suppression: LDL, or numeric value < 200 copies/ml. | Owner rule; keep until Owner confirms a change. | analytics/viral_load | 2026-11-10 | OWNER-CONFIRMED |
| D-003 | A missing sex is never defaulted (notebook cell 84 uses `.fillna('F')`). Missing sex is reported as Unknown. | Owner rule. | core/cleaning, analytics/demographics | 2026-11-10 | OWNER-CONFIRMED |
| D-004 | Duplicate UICs are never auto-deleted. They are flagged; handling policy is OQ-04. | Owner rule. | core/deduplication | 2026-11-10 | OWNER-CONFIRMED |
| D-005 | Local-only processing; no cloud, no external AI on source records, Streamlit bound to 127.0.0.1. | Owner rule (HIV KP data). | all | 2026-11-10 | OWNER-CONFIRMED |
