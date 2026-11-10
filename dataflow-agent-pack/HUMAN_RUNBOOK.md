# HUMAN RUNBOOK (for the Owner; the agent does not need this)

## 0. One-time setup (30 minutes)

1. **Sanitise the notebook before the agent sees it.** The original notebook's saved outputs include tables that contain the identifier column (UICs / CCC numbers) in several cells. Run:
   `python scripts/sanitize_notebook.py "<path to original>.ipynb" reference/OPTIMIZED_DATA_MGT.sanitized.ipynb`
   Then **move the original out of the workspace** (store it somewhere outside the `dataflow` folder). If the original has already been opened by an agent session, treat that as a possible data exposure and check your organisation's data-protection obligations.
2. Keep every real workbook **outside** the workspace (e.g. `D:\kp_private\`). The agent's models run in the cloud, so anything inside the workspace can leave your machine.
3. `git init`, commit this pack plus the sanitised notebook as the baseline.
4. Create a Python 3.11+ virtual environment outside or inside the folder as you prefer.
5. Antigravity settings (names may differ slightly by version):
   - Terminal command auto-execution: **Always Proceed with a deny list**. Suggested denies: `rm -rf`, `del /s`, `rmdir /s`, `format`, `git push`, `git remote`, `curl`, `wget`, `Invoke-WebRequest`, `iwr`, `scp`, `ssh`.
   - Review policy: **Agent Decides** (you review at phase gates via git diff; each phase is on its own branch).
   - Browser JavaScript execution: **Request Review**.
   - Use **Planning** mode for Phase 0 and each phase start.
6. The pack uses `.agents/` for workflows. If your Antigravity version expects `.agent/`, rename the folder. `AGENTS.md` is read as a rule by current versions; if yours only reads `GEMINI.md`, copy `AGENTS.md` to `GEMINI.md`.

## 1. Running a phase

1. Paste the correct prompt from `KICKOFF_PROMPT.md`.
2. Let the agent work. It will stop by itself with `PHASE N SUBMITTED`.
3. Open `docs/reports/PHASE_N_REPORT.md` and the phase's **Owner test** in `docs/PHASE_PLAN.md`.
4. Run the commands yourself. Do not accept pasted output as proof.
5. **Approve:** in `docs/gates/PHASE_APPROVALS.md` change that phase's line to
   `PHASE N | STATUS: APPROVED | by: Nickson | date: <today> | tag: phase-N-approved`
   then merge the branch and `git tag phase-N-approved`.
6. **Reject:** set the line to `REJECTED`, list defects in `docs/gates/REJECTIONS.md`, use prompt C.
7. Answer open questions in `docs/OPEN_QUESTIONS.md` as they arise. Anything unanswered keeps affected indicators PROVISIONAL.

## 2. Red flags: reject the phase if you see

- Test counts that dropped, tests edited or marked skip/xfail, or `# noqa`/`type: ignore` sprinkled to silence problems.
- A report with no raw terminal output, or "should work" language.
- Hardcoded numbers in the dashboard or placeholder functions.
- Work from a later phase in the diff (`git diff --stat` shows it).
- Any real-looking identifier in logs, tests, docs or commits.
- Changes inside `reference/` or `docs/gates/`.
- A calculated difference vs the notebook with no decision-log entry.

## 3. Your real-data checks (never upload real data into the workspace)

- Phase 2: `python -m core.pipeline inspect "<real workbook>"` → structure only.
- Phase 3/4: `python -m core.pipeline run "<real workbook>" --aggregate-only` → counts only; compare with your notebook's numbers SR by SR.
- Phase 5/7: `python scripts/compare_summaries.py <notebook-output.xlsx> <dataflow-output.xlsx>` → cell-level deltas, aggregates only.
