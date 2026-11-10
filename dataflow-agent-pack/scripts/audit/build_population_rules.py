#!/usr/bin/env python3
"""Build docs/POPULATION_RULES.md with population matrix and pathway rules."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

content = """# POPULATION RULES — DATAFLOW

Population-specific business rules, cohort configurations, indicator applicability, and export specifications extracted from `reference/OPTIMIZED_DATA_MGT.sanitized.ipynb`.
Audit date: 2026-11-10 | Author: DATAFLOW Engineering Agent | Phase: 0

---

## 1. Population Overview & File Source Specifications

Extracted from notebook cells 04, 06, 08, 10, and 12:

| Population | Full Name | File Extension | Register Sheet Name | KPLHIV Sheet Name | Default Header Rows | Notebook Reference |
|---|---|---|---|---|---|---|
| **FSW** | Female Sex Workers | `.xlsb` | `Register` | `KPLHIV` | `skiprows=2` | Cell 04 (Active) |
| **MSM** | Men who have Sex with Men | `.xlsb` | `MSM` | `KPLHIV` | `skiprows=2` | Cell 06 (Commented) |
| **TG** | Transgender | `.xlsb` | `Register` | `KPLHIV` | `skiprows=2` | Cell 08 (Commented) |
| **PWID** | People Who Inject Drugs | `.xlsx` | `Register` | `KPLHIV` | `skiprows=2` | Cell 10 (Commented) |
| **VP** | Vulnerable Populations | `.xlsb` | `Register` | `KPLHIV` | `skiprows=2` | Cell 12 (Commented) |

> [!NOTE]
> Notice sheet naming divergence: MSM register uses sheet name `'MSM'`, whereas FSW, TG, PWID, and VP use `'Register'`. The ingestion engine must support configurable sheet name aliases per population.

---

## 2. Population × Indicator × Pathway × Export Block Matrix

| Indicator / Block | FSW | MSM | TG | PWID | VP | Rule / Policy Reference |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Geographic Keys** (`county`, `sr_name`, `region`) | Yes | Yes | Yes | Yes | Yes | Standard group keys across all populations |
| **Age Grouping** (`15-19`, `20-24`, `25+`, `Below 15`) | Yes | Yes | Yes | Yes | Yes | BR-006: Missing age reported as `Unknown` |
| **Cohort & PE Totals** (`TotalCohort`, `TotalPE`) | Yes | Yes | Yes | Yes | Yes | Distinct client / PE code count |
| **HIV Testing (HTS)** (`HTSQ1..2`, `SEM`, `Neg`, `Pos`) | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **KPLHIV & Viral Load** (`Total_KPLHIV`, `Suppressed`) | Yes | Yes | Yes | Yes | Yes | Standard from KPLHIV sheet |
| **Defined Package (General Pathway)** | Standard | Standard | Standard | **Requires NSP** | Standard | BR-001 / D-001: NSP required for PWID only |
| **Defined Package (PLHIV Pathway)** | Standard | Standard | Standard | Pending OQ-01 | Standard | OQ-01 default: NSP not required for PLHIV path |
| **PrEP Indicators** (`PREP_Q1..2`, `SEM`) | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **ART Indicators** (`New_on_ART`, `CurrentArt`) | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **STI Screening, Diagnosis & Treatment** | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **TB Screening** (`TB_SCREENED_Q1..2`, `SEM`) | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **Peer Education & RRC** (`PeerEducation`, `HE_RRC`) | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **Condoms Received & Distributed** | Yes | Yes | Yes | Yes | Yes | Standard across all populations |
| **NSP Received & Distributed** (`NSP_Q1..SEM`, `total_nsp`) | **No** | **No** | **No** | **Yes** | **No** | BR-001: PWID-only commodity |
| **Excel Export Block: NSP** | Omitted | Omitted | Omitted | **Included** | Omitted | Cells 77, 82 include NSP; Cells 75, 80 omit |
| **Export Sheet Title (Q1)** | `KP_Summary` | `KP_Summary` | `KP_Summary` | `PWID_Summary` | `KP_Summary` | Notebook cells 75 vs 77 |
| **Export Sheet Title (Full Semester)** | `Summary` | `Summary` | `Summary` | `PWID_Summary` | `Summary` | Notebook cells 80 vs 82 |

---

## 3. Defined Package Pathway Specifications

The Defined Package represents comprehensive service delivery for Key Populations and has two mutually exclusive operational pathways in notebook Cell 61:

### Pathway 1: General (HIV-Negative / Unknown Status)
Clients must receive the full package of primary prevention services within the reporting period:
- **FSW / MSM / TG / VP:**
  $$\text{DefinedPackage} = \text{HTS} \\land \text{STI\\_Screening} \\land \text{TB\\_Screening} \\land \text{Condoms} \\land \text{HE\\_RRC}$$
- **PWID (per BR-001 / Decision D-001):**
  $$\text{DefinedPackage}_{\text{PWID}} = \text{HTS} \\land \text{STI\\_Screening} \\land \text{TB\\_Screening} \\land \text{Condoms} \\land \text{HE\\_RRC} \\land \\mathbf{NSP}$$

*(In the notebook code, NSP was commented out for all populations; BR-001 restores it as a mandatory requirement specifically for PWID.)*

### Pathway 2: PLHIV-Service (Known Positive)
For clients already known to be living with HIV, HTS is not applicable. The client qualifies through the PLHIV service pathway:
$$\text{PLHIV\\_Service} = \text{Known\\_Positive} \\land \text{STI\\_Screening} \\land \text{TB\\_Screening} \\land \text{Condoms} \\land \text{HE\\_RRC}$$
*(Whether NSP applies to PWID under the PLHIV pathway is tracked under **OQ-01**; default is NO until confirmed by Owner).*

### Combined Defined Package Indicator
$$\text{DefinedPackage} = \text{Pathway 1 (General)} \\lor \text{Pathway 2 (PLHIV-Service)}$$

---

## 4. Configuration Architecture (YAML-Driven)

Per `AGENTS.md` Rule 6, population-specific variations must **never** be hardcoded using `if population == 'PWID':` branching in application logic. Instead, they are completely declared in population configuration files:
- `config/populations/fsw.yaml`
- `config/populations/msm.yaml`
- `config/populations/tg.yaml`
- `config/populations/pwid.yaml`
- `config/populations/vp.yaml`

Each population YAML defines:
1. `sheet_aliases`: Sheet detection aliases (`Register`, `MSM`, `KPLHIV`).
2. `header_skiprows`: Number of metadata header rows before column names (default 2).
3. `defined_package`:
   - `require_nsp`: `true` for PWID, `false` for FSW/MSM/TG/VP.
   - `components`: List of required indicator families.
4. `reporting`:
   - `include_nsp_block`: `true` for PWID, `false` for others.
   - `sheet_name_q1`: `PWID_Summary` for PWID, `KP_Summary` for others.
   - `sheet_name_sem`: `PWID_Summary` for PWID, `Summary` for others.
"""


def main():
    out_path = BASE_DIR / "docs" / "POPULATION_RULES.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Written docs/POPULATION_RULES.md ({len(content.splitlines())} lines)")


if __name__ == "__main__":
    main()
