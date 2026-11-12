# WORK PACKAGES — OWNER EDITS ONLY

The agent may work only on the single work package whose status is ACTIVE (or REJECTED, meaning rework).
Exactly one WP may be ACTIVE or REJECTED at a time.

baseline_tag: v1.0.0

Statuses: QUEUED | ACTIVE | APPROVED | REJECTED
Types: STRESS (find, never fix) | FIX | ENHANCE
Line format (keep the shape exactly):
`WP <ID> | STATUS: <status> | type: <type> | golden_update: <allowed|no> | title: <text>`

Suggested order and rationale are in HUMAN_RUNBOOK_V2.md.

WP E1 | STATUS: QUEUED | type: ENHANCE | golden_update: no | title: Shape-profile tool and realistic generator v2
WP S7 | STATUS: QUEUED | type: STRESS | golden_update: no | title: Test the tests (mutation and switch-sensitivity)
WP S3 | STATUS: QUEUED | type: STRESS | golden_update: no | title: Metamorphic and invariant testing of analytics
WP S2 | STATUS: QUEUED | type: STRESS | golden_update: no | title: Data-chaos and ingestion fuzzing
WP S4 | STATUS: QUEUED | type: STRESS | golden_update: no | title: Excel output robustness and export safety
WP S6 | STATUS: QUEUED | type: STRESS | golden_update: no | title: Privacy and security canary audit
WP S5 | STATUS: QUEUED | type: STRESS | golden_update: no | title: UI end-to-end and failure injection
WP S1 | STATUS: QUEUED | type: STRESS | golden_update: no | title: Scale, performance and soak
