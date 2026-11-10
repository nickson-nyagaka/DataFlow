# OPEN QUESTIONS (Owner answers here)

Columns: ID · question · why it matters · options · recommended default · blocks · status.
The agent adds rows; the Owner fills the **Answer** column. Until answered, dependent indicators are PROVISIONAL.

| ID | Question | Why it matters | Options | Recommended default | Blocks | Answer | Status |
|----|----------|----------------|---------|---------------------|--------|--------|--------|
| OQ-01 | Is NSP also required in the **PLHIV-service pathway** for PWID? | Changes Defined Package for PLHIV | (a) yes (b) no (c) only for PWID with injecting risk | (b) no, until the approved definition says otherwise | Phase 4 | | OPEN |
| OQ-02 | Which templates use which age categories (notebook cells 57 vs 84 differ)? Should missing age be `Unknown`? | Age columns in every report | list per template | `Unknown` column; keep per-template categories | Phase 2/4 | | OPEN |
| OQ-03 | Missing sex: `Unknown` column in pivots, or excluded with a footnote? | Cell 84 uses `.fillna('F')` | (a) Unknown column (b) excluded + note | (a) | Phase 4/5 | | OPEN |
| OQ-04 | Duplicate UIC policy for indicators | Numerator/denominator consistency | (a) keep all rows, count unique UICs (union of events) (b) flag and exclude until resolved (c) keep latest enrolment | (a) with a Critical DQA flag | Phase 2/4 | | OPEN |
| OQ-05 | Reporting calendar: which visit columns/months belong to Q1 and Q2 in each register template? Are there always 3 per quarter? Any population that differs? | Period engine correctness | table per population | none; needs Owner | Phase 1/4 | | OPEN |
| OQ-06 | Intended rule for `hts_sem`: "(Q1 and Q2) or (Q2 and enrolled in/after month M)". Code uses M = 7, comment says April/10. What is M, and should the enrolment **year** matter? | Semester HTS | M = 4 / 7 / 10 / config per cycle | config per reporting cycle | Phase 4 | | OPEN |
| OQ-07 | HIV × ART DQA rule at cell 38: code flags **Negative + ART Yes**; comments mention Positive. Which rules do you want? | Which exceptions are raised | (a) Negative on ART (b) Positive not on ART (c) both as separate rules | (c) | Phase 3 | | OPEN |
| OQ-08 | Allowed-value vocabulary per categorical field (e.g., `Known Positive`, `Initiated`, `Restart`, `Refill`, `Switched`, `Discontinued`, Yes/No). Canonical spelling? | Replaces `.capitalize()` | Owner supplies lists | derive from the register template drop-downs | Phase 2 | | OPEN |
| OQ-09 | Viral load: use the latest result per client? Within what window? Is the suppression denominator all KPLHIV or only those with a result? What does `>LDL` mean? | Suppression rate | (a) latest in period (b) latest in 12 months (c) all rows | none; needs Owner | Phase 4 | | OPEN |
| OQ-10 | Active clients: confirm `Active` (monthly KPLHIV columns) and `Active`/`Yes` (ART outcome columns) definitions and which months apply per cycle | Active counts | Owner confirms | none | Phase 4 | | OPEN |
| OQ-11 | What are `OLD_Cohort` and `NEW_Cohort` meant to be? (Referenced in column order, never computed.) | Report columns | define / remove | remove unless defined | Phase 0/5 | | OPEN |
| OQ-12 | `TotalCohort`: unique UIC count of all register rows, or only active/enrolled in period? | Denominator everywhere | Owner confirms | unique UIC, all rows | Phase 4 | | OPEN |
| OQ-13 | NSP block colour: keep coral fallback (`FF7D81`) or assign a new colour? | Excel appearance | keep / new hex | keep | Phase 5 | | OPEN |
| OQ-14 | May exports contain UICs by default, or should masking be on by default? | Privacy vs usefulness to SRs | (a) UICs on, warn (b) masked by default | (a) | Phase 5/6 | | OPEN |
