#!/usr/bin/env python3
"""Build docs/EXCEL_OUTPUT_SPECIFICATION.md with complete styling, layout, blocks, and formulas."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

content = """# EXCEL OUTPUT SPECIFICATION — DATAFLOW

Complete visual, structural, and formula specifications for DATAFLOW Excel reporting packages, extracted directly from openpyxl implementations in notebook cells 75, 77, 80, 82, and 84.
Audit date: 2026-11-10 | Author: DATAFLOW Engineering Agent | Phase: 0

---

## 1. Visual & Formatting Standards (Global)

All generated Excel workbooks must strictly adhere to the visual identity established in the legacy reports:

| Element | Specification | Legacy Code Reference |
|---|---|---|
| **Header Font** | `Cascadia Code`, 11pt, Bold, Centered | `Font(name="Cascadia Code", size=11, bold=True)` (Cells 75, 77, 80, 82) |
| **Data Font** | `Candara`, 11pt, Regular | `Font(name="Candara", size=11, bold=False)` |
| **TOTAL Font** | `Candara`, 11pt, Bold | `Font(name="Candara", size=11, bold=True)` |
| **Subheader Fill** | Coral (`#FF7D81`), Solid | `PatternFill('solid', fgColor='FF7D81')` (Row 2 across all blocks) |
| **TOTAL Row Fill** | Green (`#6BD669`), Solid | `PatternFill('solid', fgColor='6BD669')` (Summary total row) |
| **Default Group Fill** | Coral (`#FF7D81`), Solid | Fallback for any unmapped group header block |
| **Cell Borders** | Thin solid black (`#000000`) | `Border(left=thin, right=thin, top=thin, bottom=thin)` on all cells |
| **Freeze Panes** | Row 3 (`A3`) | `ws.freeze_panes = 'A3'` (keeps 2 header rows visible) |
| **Gridlines** | Explicitly Hidden | `ws.sheet_view.showGridLines = False` |
| **Row 1 Height** | 22 pt | `ws.row_dimensions[1].height = 22` |
| **Row 2 Height** | 30 pt | `ws.row_dimensions[2].height = 30` |
| **Data Row Heights** | Default / Auto | Unconstrained |
| **Column Widths** | Keys: 22; Data: 14 | Cols 1-3 width = 22, Cols 4+ width = 14 |
| **Horizontal Alignment** | Left: Cols 1-3; Center: Cols 4+ and Headers | `Alignment(horizontal='left' if col <= 3 else 'center')` |
| **Vertical Alignment** | Center | `Alignment(vertical='center', wrap_text=True)` across all cells |

---

## 2. Row-1 Group Header Color Palette

Extracted from `GROUP_HEADER_COLORS` dictionary (Cells 75, 77, 80, 82, 83):

| Block Group Name | Hex Color | Visual Swatch Description | Usage |
|---|:---:|---|---|
| `COUNTY` | `#00B050` | Standard Green | Geographic key |
| `SR NAME` | `#00B050` | Standard Green | Sub-recipient organization key |
| `REGION` | `#00B050` | Standard Green | Regional administrative key |
| `AGE GROUP` | `#00B050` | Standard Green | Age category disaggregations |
| `TOTAL` | `#00B050` | Standard Green | Total Cohort and Peer Educator totals |
| `HIV TESTING & PLHIV` | `#8EA9DB` | Soft Cornflower Blue | HTS Testing, Positives, Negatives, KPLHIV |
| `DEFINED PACKAGE` | `#C6E0B4` | Soft Sage / Light Olive | Defined Package coverage indicators |
| `PREP ` | `#FFE699` | Soft Yellow / Gold | PrEP coverage indicators |
| `ART` | `#8EA9DB` | Soft Cornflower Blue | New on ART and Current ART |
| `STI SCREENING` | `#F8CBAD` | Soft Peach / Coral | STI screening indicators |
| `STI DIAGNOSIS` | `#F8CBAD` | Soft Peach / Coral | STI diagnosis indicators |
| `STI TREATMENT` | `#F8CBAD` | Soft Peach / Coral | STI treatment indicators |
| `TB SCREENING` | `#B3A2C7` | Soft Lavender / Purple | TB screening indicators |
| `PEER EDUCATION` | `#FFFF00` | Bright Canary Yellow | Peer education coverage |
| `CONDOMS` | `#D9D9D9` | Neutral Light Grey | Condom distribution (client & commodity) |
| `NSP` | `#FF7D81` | Coral (Subheader match) | Needle & Syringe Programme (PWID only) |

---

## 3. Total Row & Excel Formulas Specification

Every summary worksheet concludes with an automated **TOTAL** row located immediately below the last data row (`row_idx = last_data_row + 1`):
1. **Column Span 1 to 3:**
   - Merged across columns A, B, and C (`start_row=total_row, start_col=1, end_row=total_row, end_col=3`).
   - Cell A value: `"TOTAL"`.
   - Font: `Candara`, 11pt, Bold.
   - Fill: Green (`#6BD669`).
   - Alignment: Centered horizontally and vertically.
2. **Columns 4 to Last:**
   - Each column contains an Excel dynamic SUM formula:
     $$=\\text{SUM}(\\text{ColLetter}3 : \\text{ColLetter}\\text{LastDataRow})$$
   - Example for Column D (row 3 to row 25): `=SUM(D3:D25)`.
   - Font: `Candara`, 11pt, Bold.
   - Fill: Green (`#6BD669`).
   - Alignment: Centered horizontally and vertically.

> [!IMPORTANT]
> Because openpyxl writes formulas without calculating formula results, cached values are empty until opened in Excel. The validation engine (`reporting/workbook_validator.py`) must compute independent pandas checksums to verify total integrity.

---

## 4. Column Block Specifications by Report Type

### A. Full Semester Non-PWID (`Summary` Sheet — Cell 80)
Target Populations: FSW, MSM, TG, VP | Period: Q1, Q2, SEM | Total Columns: 41

```yaml
blocks:
  - group: "COUNTY"
    subheaders: ["COUNTY"]
    columns: ["county"]
  - group: "SR NAME"
    subheaders: ["SR NAME"]
    columns: ["sr_name"]
  - group: "REGION"
    subheaders: ["REGION"]
    columns: ["region"]
  - group: "AGE GROUP"
    subheaders: ["15-19", "20-24", "25+", "Below 15"]
    columns: ["15-19", "20-24", "25+", "Below 15"]
  - group: "TOTAL"
    subheaders: ["COHORT", "PE"]
    columns: ["TotalCohort", "TotalPE"]
  - group: "HIV TESTING & PLHIV"
    subheaders: ["Q1", "Q2", "SEM", "SEM_ANY", "NEGQ1", "NEGQ2", "POSQ1", "POSQ2", "Total_KPLHIV", "Suppressed"]
    columns: ["HTSQ1", "HTSQ2", "HTS_SEM", "HTS_SEM_ANY", "HTS_Negative", "HTS_Negative_Q2", "HTS_Positive", "HTS_Positive_Q2", "Total_KPLHIV", "Suppressed"]
  - group: "DEFINED PACKAGE"
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["DefinedPackage_Q1", "DefinedPackage_Q2", "DefinedPackage_SEM"]
  - group: "PREP "
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["PREP_Q1", "PREP_Q2", "PREP_SEM"]
  - group: "ART"
    subheaders: ["NEWQ1", "NEWQ2", "CURRENTQ1", "CURRENTQ2"]
    columns: ["New_on_ART", "New_on_ART_Q2", "CurrentArt_Q1", "CurrentArt_Q2"]
  - group: "STI SCREENING"
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["STISCREENEDQ_1", "STISCREENEDQ_2", "STI_SCREENED_SEM"]
  - group: "STI DIAGNOSIS"
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["STIDiagnosid_Q1", "STI_DIAGNOSED_Q2", "STI_DIAGNOSED_SEM"]
  - group: "STI TREATMENT"
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["STItreated_Q1", "STI_TREATED_Q2", "STI_TREATED_SEM"]
  - group: "TB SCREENING"
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["TB_SCREENED_Q1", "TB_SCREENED_Q2", "TB_SCREENED_SEM"]
  - group: "PEER EDUCATION"
    subheaders: ["Q1", "Q2", "SEM"]
    columns: ["PeerEducation_Q1", "PeerEducation_Q2", "PeerEducation_SEM"]
  - group: "CONDOMS"
    subheaders: ["Q1", "Q2", "SEM", "TOTQ1", "TOTQ2", "SEM"]
    columns: ["ReceivedCondom_Q1", "ReceivedCondom_Q2", "ReceivedCondom_SEM", "total_condoms_Q1", "total_condoms_Q2", "total_condoms_SEM"]
```

---

### B. Full Semester PWID (`PWID_Summary` Sheet — Cell 82)
Target Population: PWID | Period: Q1, Q2, SEM | Total Columns: 47 (Blocks 1–15 identical to Non-PWID, plus Block 16 NSP)

```yaml
  - group: "NSP"
    subheaders: ["Q1", "Q2", "SEM", "TOTQ1", "TOTQ2", "SEM"]
    columns: ["NSP_Q1", "NSP_Q2", "NSP_SEM", "total_nsp_Q1", "total_nsp_Q2", "total_nsp_SEM"]
```

---

### C. Q1 Only Non-PWID (`KP_Summary` Sheet — Cell 75)
Target Populations: FSW, MSM, TG, VP | Period: Q1 Only | Total Columns: 16

```yaml
blocks:
  - group: "COUNTY"
    subheaders: ["COUNTY"]
    columns: ["county"]
  - group: "SR NAME"
    subheaders: ["SR NAME"]
    columns: ["sr_name"]
  - group: "REGION"
    subheaders: ["REGION"]
    columns: ["region"]
  - group: "AGE GROUP"
    subheaders: ["15-19", "20-24", "25+", "Below 15"]
    columns: ["15-19", "20-24", "25+", "Below 15"]
  - group: "TOTAL"
    subheaders: ["COHORT", "PE"]
    columns: ["TotalCohort", "TotalPE"]
  - group: "HIV TESTING & PLHIV"
    subheaders: ["Q1", "NEGQ1", "POSQ1", "Total_KPLHIV", "Suppressed"]
    columns: ["HTSQ1", "HTS_Negative", "HTS_Positive", "Total_KPLHIV", "Suppressed"]
  - group: "DEFINED PACKAGE"
    subheaders: ["Q1"]
    columns: ["DefinedPackage_Q1"]
  - group: "PREP "
    subheaders: ["Q1"]
    columns: ["PREP_Q1"]
  - group: "ART"
    subheaders: ["NEWQ1", "CURRENTQ1"]
    columns: ["New_on_ART", "CurrentArt_Q1"]
  - group: "STI SCREENING"
    subheaders: ["Q1"]
    columns: ["STISCREENEDQ_1"]
  - group: "STI DIAGNOSIS"
    subheaders: ["Q1"]
    columns: ["STIDiagnosid_Q1"]
  - group: "STI TREATMENT"
    subheaders: ["Q1"]
    columns: ["STItreated_Q1"]
  - group: "TB SCREENING"
    subheaders: ["Q1"]
    columns: ["TB_SCREENED_Q1"]
  - group: "PEER EDUCATION"
    subheaders: ["Q1"]
    columns: ["PeerEducation_Q1"]
  - group: "CONDOMS"
    subheaders: ["Q1", "TOTQ1"]
    columns: ["ReceivedCondom_Q1", "total_condoms_Q1"]
```

---

### D. Q1 Only PWID (`PWID_Summary` Sheet — Cell 77)
Target Population: PWID | Period: Q1 Only | Total Columns: 18 (Blocks 1–15 identical to Q1 Non-PWID, plus Block 16 NSP)

```yaml
  - group: "NSP"
    subheaders: ["Q1", "TOTQ1"]
    columns: ["NSP_Q1", "total_nsp_Q1"]
```

---

## 5. Additional Mandatory Workbook Sheets

Per Master Brief §10, every production Excel workbook emitted by DATAFLOW must include two additional sheets alongside the main summary:

### 1. `Run Metadata` Sheet
Contains audit and reproducibility parameters:
- `Application Version`: e.g., `DATAFLOW v1.0.0`
- `Execution Timestamp`: ISO 8601 UTC timestamp
- `Target Population`: `FSW` / `MSM` / `TG` / `PWID` / `VP`
- `Reporting Period`: `Q1` / `Q2` / `SEM`
- `Input File SHA-256`: Hash of source workbook
- `Effective Config SHA-256`: Hash of merged YAML settings
- `Compat Mode State`: List of legacy compat switches enabled/disabled
- `Provisional Indicators`: List of any indicators calculated under provisional status with open-question IDs

### 2. `Cleaning Log` Sheet
Detailed audit log of transformations applied to the raw data:
- `Rule ID`: Standard cleaning rule code (e.g., `CLN-001`, `CLN-002`)
- `Description`: Human-readable summary of transformation
- `Columns Affected`: List of dataset columns modified
- `Records Affected`: Row count modified or flagged
- `Status`: `APPLIED` / `SKIPPED` / `WARNING`
"""


def main():
    out_path = BASE_DIR / "docs" / "EXCEL_OUTPUT_SPECIFICATION.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(
        f"Written docs/EXCEL_OUTPUT_SPECIFICATION.md ({len(content.splitlines())} lines)"
    )


if __name__ == "__main__":
    main()
