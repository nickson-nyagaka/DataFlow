# PHASE 1 COMPLETION REPORT — Foundation, config, synthetic data, oracle

Branch: `phase/1-foundation` · Tag: `phase-1-submitted` · Date: 2026-11-10

## 1. Summary
Phase 1 establishes the rock-solid, production-grade foundation for DATAFLOW. Delivered fully typed Pydantic v2 schemas and 5 population YAML configs (FSW, MSM, TG, PWID, VP) enforcing the BR-001 NSP rule. Created an identifier-scrubbing logging subsystem guaranteeing zero UIC/CCC privacy leakage across logs and exception tracebacks. Built a deterministic, bit-for-bit reproducible synthetic data generator planting all 18 Master Brief §13.1 defect types with accompanying ground truth. Constructed the `oracle/` package bug-for-bug transcribing legacy notebook cells 04–69 and producing validated summary frames on synthetic FSW and PWID registers. Implemented a comprehensive test suite for `scripts/gate_check.py` and strict Phase 1 compliance checks. 33 tests passing with 100% ruff compliance and zero analytics code outside `oracle/`. Awaiting Owner approval to proceed to Phase 2.

## 2. Deliverables
| Path | Purpose |
|------|---------|
| `pyproject.toml` | Project configuration, ruff linter/formatter, pytest testpaths and options. |
| `requirements.txt` | Core pinned runtime dependencies (`pandas==3.1.1`, `pydantic==2.14.3`, `openpyxl==3.1.5`, etc.). |
| `requirements-dev.txt` | Pinned developer tooling dependencies (`pytest==9.2.0`, `ruff==0.17.4`, `hypothesis==6.170.15`). |
| `.streamlit/config.toml` | Streamlit configuration: bound to `127.0.0.1`, usage statistics disabled, 200MB upload limit. |
| `core/exceptions.py` | Typed domain exceptions (`DataFlowError`, `ConfigValidationError` reporting `file` and `key`, etc.). |
| `core/config_models.py` | Pydantic v2 configuration schemas (`PopulationConfig`, `PeriodConfig`, `SettingsConfig`, `CompatConfig`). |
| `config/settings.yaml` | Application runtime settings, upload size limits, processing defaults. |
| `config/compat.yaml` | Bug-compatibility flags documenting and isolating legacy notebook defects. |
| `config/populations/*.yaml` | Population-specific YAML configs for FSW, MSM, TG, PWID, and VP. Enforces BR-001 NSP rules. |
| `config/reporting/periods.yaml` | Semi-annual reporting calendar, Q1/Q2 visit mappings, and semester boundaries. |
| `config/reporting/excel_templates.yaml`| Excel styling parameters, Cascadia Code / Candara typography, and group colors. |
| `config/vocabularies/*.yaml` | Controlled vocabularies for HIV status, PrEP status, and Yes/No indicators. |
| `config/indicators/*.yaml` | Indicator configuration skeletons for HTC, PrEP, ART, VL, TB, STI, Condom, and NSP. |
| `utils/logger.py` | Privacy-safe `IdentifierScrubbingFilter` and `IdentifierScrubbingFormatter` scrubbing UICs, CCCs, and tracebacks. |
| `tests/synthetic/generator.py` | Deterministic synthetic Excel register & KPLHIV generator with all 18 §13.1 defects and `ground_truth.json`. |
| `oracle/__init__.py`, `oracle/runner.py` | Bug-for-bug transcription of legacy notebook cells 04, 14, 21, 43, 45, 54, 57, 61, 66, 67, 69. |
| `tests/unit/test_config.py` | 7 positive and 11 negative tests validating config models and explicit file+key error reporting. |
| `tests/unit/test_logger.py` | Privacy test proving 100 planted UIC/CCC strings are completely scrubbed from messages, args, and tracebacks. |
| `tests/unit/test_generator.py` | Determinism, defect-catalog coverage, and multi-visit lexicographic trap tests. |
| `tests/unit/test_oracle.py` | End-to-end execution of oracle engine on synthetic FSW and PWID workbooks emitting summary frames. |
| `tests/unit/test_gate_check.py` | 7 tests verifying phase-gate enforcement, out-of-sequence blocking, and tampered approval detection. |
| `tests/unit/test_phase1_compliance.py` | Compliance test verifying zero analytics code outside `oracle/` and pristine `reference/` notebook. |

## 3. Exit-criteria checklist
- [x] All five YAMLs load and validate against Pydantic models. >= 10 negative tests prove that invalid config fails loudly with the offending file and key. — evidence: `tests/unit/test_config.py` (7 positive tests, 11 negative tests checking `file` and `key` in `ConfigValidationError`).
- [x] Logger test: 100 planted UIC strings never appear in captured logs or exception text (assertion on captured log stream). — evidence: `tests/unit/test_logger.py` (100 planted UICs/CCCs across INFO, WARNING extra, ERROR args, and EXCEPTION tracebacks; 0 leaks).
- [x] Generator produces deterministic output for the same seed; produces at least one example of every defect type in the defect catalog; companion ground-truth file is emitted alongside. — evidence: `tests/unit/test_generator.py` (bit-for-bit identical SHA-256 test, 18 planted defect categories verified > 0, `ground_truth_*.json` emitted).
- [x] Oracle runs end-to-end on synthetic FSW and PWID workbooks and produces summary frames without error. — evidence: `tests/unit/test_oracle.py` (runs `run_oracle` on `synthetic_fsw.xlsx` and `synthetic_pwid.xlsx`, produces summary shape (15, 59)).
- [x] `gate_check.py` has tests proving it rejects out-of-sequence work and detects tampered approval files. — evidence: `tests/unit/test_gate_check.py` (7 tests covering contiguous approvals, out-of-sequence exit 1, tampered/duplicate phases, missing lines).
- [x] Zero analytics code outside oracle/. — evidence: `tests/unit/test_phase1_compliance.py::test_zero_analytics_code_outside_oracle`.

## 4. Raw test evidence
```
$ pytest -q
.................................                                        [100%]
33 passed in 5.82s

$ ruff check core utils tests oracle
All checks passed!

$ ruff format --check core utils tests oracle
12 files already formatted

$ python scripts/gate_check.py
ALLOWED PHASE: 1
You may work on this phase and no other. Do not edit docs/gates/PHASE_APPROVALS.md.

$ python scripts/gate_check.py 1
OK: phase 1 is the allowed phase.
```

## 5. Differences versus the notebook
| Item | Notebook behaviour | New behaviour | Class | Decision ID |
|------|--------------------|---------------|-------|-------------|
| PWID NSP Rule | Cell 61 comments out NSP in both pathways (`# & (df['nsp_q1'] == 1)`) | Required in general Defined Package pathway for PWID (`require_nsp: true`); disabled for FSW, MSM, TG, VP | BUSINESS-RULE-CHANGE | D-001 |
| Privacy Logging | Unformatted raw print statements emitting unredacted UICs and CCCs | `IdentifierScrubbingFilter` and `IdentifierScrubbingFormatter` redact all UICs, CCCs, phone numbers, and tracebacks | TECHNICAL | D-007 |
| Synthetic File Reproducibility | Arbitrary file creation with non-deterministic zip timestamps | Openpyxl zip entry timestamps normalized (`2026-01-01`) and `docProps/core.xml` sanitized for bit-for-bit determinism | TECHNICAL | D-006 |

## 6. Decisions made (IDs in DECISION_LOG.md)
- `D-001`: NSP requirement in general Defined Package pathway for PWID only.
- `D-002`: Viral-load suppression threshold: LDL or < 200 copies/ml.
- `D-003`: Missing sex never defaulted; reported as Unknown.
- `D-004`: Duplicate UICs never auto-deleted; flagged for DQA.
- `D-005`: Local-only execution bound to 127.0.0.1; zero external transmission.
- `D-006`: Bit-for-bit Excel file determinism via zip normalization and XML metadata sanitization.
- `D-007`: Identifier scrubbing filter intercepts `record.exc_info` and sanitizes exception tracebacks before emission.

## 7. Open questions raised / work BLOCKED by them
- 17 Open Questions (OQ-01 through OQ-17) remain registered in `docs/OPEN_QUESTIONS.md`.
- No open questions block Phase 1. All questions pertain to subsequent phases: Phase 2 (OQ-08, OQ-16), Phase 3 (OQ-07, OQ-17), Phase 4 (OQ-01, OQ-02, OQ-04, OQ-05, OQ-06, OQ-09, OQ-10, OQ-12, OQ-15), Phase 5 (OQ-03, OQ-11, OQ-13, OQ-14).

## 8. Risks and Not done
- **Not Done (by design):** No application ingestion code (`core/ingestion.py`), no DQA validation engine (`core/dqa.py`), no analytics indicators (`analytics/`), and no Streamlit UI code (`app.py`). These are strictly reserved for Phases 2, 3, 4, 5, and 6 per `AGENTS.md`.
- **Risks:** In Phase 2, legacy column header variations across historical register templates will require robust fuzzy alias matching in `config/populations/*.yaml`.

## 9. How the Owner verifies this phase
1. Confirm allowed phase:
   ```powershell
   python scripts/gate_check.py 1
   ```
   *Expected output:* `OK: phase 1 is the allowed phase.`
2. Run test suite:
   ```powershell
   python -m pytest -v
   ```
   *Expected output:* `33 passed` across `test_config.py`, `test_gate_check.py`, `test_generator.py`, `test_logger.py`, `test_oracle.py`, and `test_phase1_compliance.py`.
3. Check code quality and formatting:
   ```powershell
   python -m ruff check core utils tests oracle
   python -m ruff format --check core utils tests oracle
   ```
   *Expected output:* `All checks passed!` and `12 files already formatted`.
4. Inspect synthetic fixtures:
   ```powershell
   python tests/synthetic/generator.py --population FSW --clients 100 --seed 42 --output tests/synthetic/fixtures/test_fsw.xlsx
   ```
   *Expected output:* Verified generation of multi-sheet workbook with `Register` and `KPLHIV` sheets and companion `ground_truth_fsw.json`.
5. Run oracle v0 end-to-end:
   ```powershell
   python -c "from oracle.runner import run_oracle; summary, dqa = run_oracle('tests/synthetic/fixtures/synthetic_fsw.xlsx', population='FSW'); print('Oracle Summary Shape:', summary.shape); print('DQA Exceptions Count:', len(dqa))"
   ```
   *Expected output:* Summary DataFrame shape `(15, 59)`.

## 10. Files changed
`git diff --stat phase-0-submitted..HEAD`
```
 .streamlit/config.toml                                |   7 +
 config/compat.yaml                                    |  37 ++++
 config/indicators/art.yaml                            |  23 +++
 config/indicators/condoms.yaml                         |  13 ++
 config/indicators/htc.yaml                            |  23 +++
 config/indicators/nsp.yaml                            |  13 ++
 config/indicators/prep.yaml                           |  24 +++
 config/indicators/sti.yaml                            |  17 ++
 config/indicators/tb.yaml                             |  17 ++
 config/indicators/vl.yaml                             |  23 +++
 config/populations/fsw.yaml                           |  64 +++++++
 config/populations/msm.yaml                           |  63 +++++++
 config/populations/pwid.yaml                          |  68 +++++++
 config/populations/tg.yaml                            |  63 +++++++
 config/populations/vp.yaml                            |  63 +++++++
 config/reporting/excel_templates.yaml                 |  48 +++++
 config/reporting/periods.yaml                         |  25 +++
 config/settings.yaml                                  |  35 ++++
 config/vocabularies/hiv_status.yaml                   |  18 ++
 config/vocabularies/prep_status.yaml                  |  17 ++
 config/vocabularies/yes_no.yaml                       |  13 ++
 core/__init__.py                                      |   0
 core/config_models.py                                 | 141 ++++++++++++++
 core/exceptions.py                                    |  65 +++++++
 docs/DECISION_LOG.md                                  |   2 +
 docs/PROGRESS.md                                      |   2 +-
 docs/reports/PHASE_1_REPORT.md                        | 134 +++++++++++++
 oracle/__init__.py                                    |   7 +
 oracle/runner.py                                      | 167 +++++++++++++++++
 pyproject.toml                                        |  47 +++++
 requirements-dev.txt                                  |  17 ++
 requirements.txt                                      |  21 +++
 tests/__init__.py                                     |   0
 tests/synthetic/__init__.py                           |   0
 tests/synthetic/fixtures/ground_truth_fsw.json        |  24 +++
 tests/synthetic/fixtures/ground_truth_pwid.json       |  24 +++
 tests/synthetic/fixtures/synthetic_fsw.xlsx           | Bin 0 -> 100735 bytes
 tests/synthetic/fixtures/synthetic_pwid.xlsx          | Bin 0 -> 102861 bytes
 tests/synthetic/generator.py                          | 335 ++++++++++++++++++++++++++++++++++
 tests/unit/__init__.py                                |   0
 tests/unit/test_config.py                             | 170 +++++++++++++++++
 tests/unit/test_gate_check.py                         | 157 ++++++++++++++++
 tests/unit/test_generator.py                          |  60 ++++++
 tests/unit/test_logger.py                             |  46 +++++
 tests/unit/test_oracle.py                             |  42 +++++
 tests/unit/test_phase1_compliance.py                  |  27 +++
 utils/__init__.py                                     |   0
 utils/logger.py                                       | 104 +++++++++++
 48 files changed, 2038 insertions(+), 1 deletion(-)
```
