# DECISION LOG

Classes: BUG-FIX · BUSINESS-RULE-CHANGE (Owner-approved only) · DEFECT · AMBIGUOUS · TECHNICAL

| ID | Decision | Reason | Affected modules | Date | Status |
|----|----------|--------|------------------|------|--------|
| D-001 | NSP is a required component of the **general** Defined Package pathway for PWID only. FSW, MSM, TG, VP: NSP is not required. | Owner rule. NOTE: the notebook (cell 61) has every `nsp_q*` requirement commented out in both pathways, so this is a BUSINESS-RULE-CHANGE; expected diffs vs the notebook must be classified, not hidden. | analytics/defined_package, config/populations/*.yaml | 2026-11-10 | OWNER-CONFIRMED |
| D-002 | Viral-load suppression: LDL, or numeric value < 200 copies/ml. | Owner rule; keep until Owner confirms a change. | analytics/viral_load | 2026-11-10 | OWNER-CONFIRMED |
| D-003 | A missing sex is never defaulted (notebook cell 84 uses `.fillna('F')`). Missing sex is reported as Unknown. | Owner rule. | core/cleaning, analytics/demographics | 2026-11-10 | OWNER-CONFIRMED |
| D-004 | Duplicate UICs are never auto-deleted. They are flagged; handling policy is OQ-04. | Owner rule. | core/deduplication | 2026-11-10 | OWNER-CONFIRMED |
| D-005 | Local-only processing; no cloud, no external AI on source records, Streamlit bound to 127.0.0.1. | Owner rule (HIV KP data). | all | 2026-11-10 | OWNER-CONFIRMED |
| D-006 | Bit-for-bit synthetic Excel workbook determinism achieved via zip archive timestamp normalization (`2026-01-01 00:00:00`) and openpyxl `docProps/core.xml` datetime sanitization. | Guarantees exact SHA-256 reproducibility across machines and runs. | tests/synthetic/generator.py | 2026-11-10 | TECHNICAL |
| D-007 | IdentifierScrubbingFilter in logging engine intercepts `record.exc_info` and formats/redacts raw exception tracebacks prior to handler emission. | Defense-in-depth privacy safeguard ensuring zero UIC/CCC leak even during unhandled crash tracebacks. | utils/logger.py | 2026-11-10 | TECHNICAL |
