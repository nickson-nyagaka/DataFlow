# DATAFLOW v1.0.0 — Field Troubleshooting & Technical Diagnostic Guide

This operational manual documents solutions for common technical issues encountered by field deployment teams running DATAFLOW on Windows desktop and laptop systems.

---

## 1. Windows PowerShell Execution Policy Restrictions

### Symptom
When attempting to run `run_dataflow.ps1`, PowerShell displays a red security block:
```
File D:\DataFlow\dataflow-agent-pack\run_dataflow.ps1 cannot be loaded because running scripts is disabled on this system.
For more information, see about_Execution_Policies at https:/go.microsoft.com/fwlink/?LinkID=135170.
    + CategoryInfo          : SecurityError: (:) [], PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```

### Root Cause
Windows 10 and 11 workstations in corporate or institutional networks default to the `Restricted` PowerShell Execution Policy, preventing the execution of unsigned local scripts.

### Recommended Fix: Dual-Launcher Wrapper (Zero Friction)
Instead of running the `.ps1` file directly, double-click **`run_dataflow.bat`** in the project root directory.  
`run_dataflow.bat` invokes PowerShell with session-scoped bypass parameters:
```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dataflow.ps1"
```
This bypass applies strictly to the transient launcher process and does not weaken system-wide IT group policies.

### Alternative Fix: Manual PowerShell Session Bypass
If running directly from the PowerShell console, grant execution permissions for your current terminal session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_dataflow.ps1
```

---

## 2. Port 8501 Address Conflicts (Port Already in Use)

### Symptom
Streamlit fails to launch or silently redirects to `http://127.0.0.1:8502`, or terminal logs show:
```
OSError: [WinError 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted
```

### Root Cause
A previously opened instance of DATAFLOW or another local service is still running in the background and holding socket `127.0.0.1:8501`.

### Resolution Steps
1. **Find and terminate lingering Python instances in PowerShell:**
   ```powershell
   Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
   ```
2. **Identify specific process holding port 8501:**
   ```powershell
   netstat -ano | findstr :8501
   # Note the PID in the rightmost column (e.g., 14320)
   Stop-Process -Id 14320 -Force
   ```
3. **Launch on a custom port if another mandatory service uses 8501:**
   ```powershell
   streamlit run app.py --server.address=127.0.0.1 --server.port=8510
   ```

---

## 3. Out-of-Memory (OOM) Errors on Large Cohorts (> 40k rows)

### Symptom
The pipeline terminates abruptly during Cleaning or Reporting with:
```
MemoryError
```
or Windows displays a *"Low Virtual Memory"* notification.

### Root Causes & Verifications
1. **32-Bit Python Architecture Trap:**
   Check your Python architecture by running:
   ```powershell
   python -c "import platform; print(platform.architecture())"
   ```
   If the output reports `('32bit', 'WindowsPE')`, Python is strictly limited to 2.0 GB of virtual address space by the operating system, regardless of how much physical RAM your machine has.
   - **Fix:** Install **64-bit Python 3.11 or later** from [python.org](https://www.python.org/downloads/windows/).
2. **Concurrent In-Memory Workbooks:**
   When running large cohorts (> 80,000 rows) on 4 GB or 8 GB laptops, ensure background applications (such as large spreadsheets in Microsoft Excel or heavy browser tabs) are closed before processing.
3. **Write-Only Streaming Exporters:**
   DATAFLOW v1.0.0 automatically utilizes `openpyxl.Workbook(write_only=True)` and streaming generators for `02_Cleaned_Data_<POP>.xlsx`, reducing memory footprints by over 80%.

---

## 4. Excel Workbook Ingestion & Parsing Errors

### Error: `IngestionError: Could not detect Register sheet in workbook`
- **Cause:** The input Excel file does not contain a worksheet matching expected aliases.
- **Accepted Register Sheet Names:** `Register`, `FSW`, `MSM`, `PWID`, `TG`, `VP`, `KP_Register`, `Cohort`.
- **Fix:** Rename the raw data tab to `Register` (or the target population code).

### Error: `IngestionError: Missing required columns in sheet`
- **Cause:** Critical demographic anchor columns could not be identified after scanning rows 0–15.
- **Required Columns:**
  - `kp_vp_unique_identifier_code` (Accepted aliases: `UIC`, `Program UIC`, `Client UIC`)
  - `county` (Accepted aliases: `County`, `County Name`)
  - `date_of_enrolment` (Accepted aliases: `Enrolment Date`, `Date Enrolled`, `DOB`)
- **Fix:** Ensure column headers exist in the first 10 rows and match standard MOH/NASCOP naming conventions.

### Error: `IngestionError: Ambiguous duplicate column mapping`
- **Cause:** Two distinct columns in the raw workbook normalize to the exact same canonical column (e.g., both `UIC` and `Client UIC` appear as separate columns).
- **Fix:** Delete or rename the redundant duplicate column before uploading.

### Error: `zipfile.BadZipFile: File is not a zip file`
- **Cause:** The uploaded `.xlsx` file is corrupt, partially downloaded, or is actually an old binary `.xls` (Excel 97-2003) format saved with an `.xlsx` extension.
- **Fix:** Open the file in Microsoft Excel and choose **File $\rightarrow$ Save As $\rightarrow$ Excel Workbook (.xlsx)**.

---

## 5. Diagnostic Support Bundle Generation

When contacting M&E technical support, never email raw cohort workbooks containing patient UICs or medical data.

Instead, use DATAFLOW's built-in **One-Click Diagnostic Support Bundle**:

1. In the application sidebar, navigate to the **About** tab.
2. Scroll to the **Diagnostic & Technical Support** card.
3. Click **"Generate Diagnostic Support Bundle 📦"**.
4. The system will compile a timestamped ZIP archive in `runtime/audit/diagnostics/`:
   ```
   DATAFLOW_Diagnostic_Bundle_YYYYMMDD_HHMMSS.zip
   ├── system_environment.json   # OS, Python version, platform architecture, RAM
   ├── config_hashes.json        # SHA-256 hashes of active population YAML configs
   ├── pipeline_state.json       # Last run parameters, stage timings, error counts
   └── execution.log             # Technical trace scrubbed of all patient PII
   ```
5. Click **Download Diagnostic Bundle (.zip)** and share this file with technical support. All patient identifiers, UICs, CCCs, and PE codes are guaranteed to be redacted via regex scrubbers (`[REDACTED_UIC]`, `[REDACTED_CCC]`, `[REDACTED_NUPI]`).
