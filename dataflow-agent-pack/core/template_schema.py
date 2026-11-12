"""Ground-Truth KP Template Schema Specification and Column Mapping Engine.

Based on reference/KP_TEMPLATE.xlsx:
- Register sheet: 19 demographic/enrollment columns + 6 blocks of 53 visit encounter columns (337 total columns).
- KPLHIV sheet: 72 tracking columns including viral load monitoring and clinical history.
"""

from __future__ import annotations

from core.ingestion import DEFAULT_REGISTER_ALIASES, normalize_token, resolve_column_aliases

# 1. Official Register demographic column headers (columns 1 to 19 in reference/KP_TEMPLATE.xlsx)
REGISTER_DEMOGRAPHIC_HEADERS = [
    "Region",
    "SR Name",
    "County",
    "Sub-County",
    "Ward ",
    "Hotspot Name",
    "KP’s/VP’s Name (Three names and Nickname) ",
    "KP/VP Phone No/Block No. ",
    "KP/VP unique identifier code ",
    "Key/Vulnerable population Type ",
    "Date of Birth (DD/MM/YYYY)",
    "Age ",
    "Sex (M/F) ",
    "Date of first Contact ",
    "Date of enrolment ",
    "HIV status at enrollment",
    "CCC Number/NUPI/N/A (10 digit number)",
    "Peer Educator",
    "Peer Educator Code",
]

# 2. Official repeating visit encounter column headers (53 columns per monthly/encounter block in reference/KP_TEMPLATE.xlsx)
REGISTER_ENCOUNTER_HEADERS = [
    "Received peer education(Y/N)  ",
    "HTS Service Point",
    "HIV Tested Results (P/ N/ ND/ NA) ",
    "Date Initiated on ART (Newly Diagnosed) ",
    "Currently on ART (Y/N/N/A) ",
    "ART Outcome",
    "Screened for TB ",
    "TB Screening Results",
    "Diagnosed with TB",
    "Started on TB treatment ",
    "Completed TB Treatment ",
    "On TPT (Started-S/ Ongoing-O/ Completed-C/ N/A) ",
    "Reported potential HIV Exposure within 72 hours  (Y/N) ",
    "Provided with PEP within 72 hours  (Y/N/NA) ",
    "Completed PEP (Y/N/NA) ",
    "Condom requirement as per need (INDICATE NUMBER)  (N/A for Inmates) ",
    "Condoms distributed (INDICATE NUMBER))  (N/A for Inmates) ",
    "Lubricant requirement as per need (INDICATE NUMBER))  (N/A for Inmates) ",
    "Lubricant distributed (INDICATE NUMBER))  (N/A for Inmates) ",
    "Needle and syringe requirement (INDICATE NUMBER)) (N/A for Inmates) ",
    "Needles and syringes distributed  (INDICATE NUMBER)) (N/A for Inmates) ",
    "Screened for Hep C Antibody test  (Y / N) ",
    "HEP C Antibody Screening Results  (P/N/ND) ",
    "Hep C Confirmatory PCR Test Results  (P/N/ND/NA) ",
    "Treated for HEP C  (Y/N/NA) ",
    "Screened for Hep B Using Surface Antigen Test  (Y / N) ",
    "Hepatitis B Surface Antigen Screening Results  ",
    "HBV P Confirmatory Results  (P/ N/ ND) ",
    "On HEP B treatment management (Y/N/NA) ",
    "HEP B vaccination",
    "Screened for STIs (Y/N) ",
    "Diagnosed with STI (Y/N) ",
    "   Treated for STIs  (Y/N/NA/ R-referred) ",
    "Screened for Alcohol and Drug abuse  (Y/ N) ",
    "Results for Alcohol and drug abuse screening  Result",
    "Screened for Mental Health  (Y/N/) ",
    "Mental Health Screening Result",
    "PrEP Status ",
    "# Months Prep Dipensed \n(For refills, restart, initiated)",
    "Cervical Cancer Screening  (Y/ N/ N/A) ",
    "Cervical Cancer Screening Results  (P/ N/ N/A) ",
    "Treated for Cervical Cancer  (Y/ N/ N/A) ",
    "Anal Cancer Screening  (Y/ N/ N/A) ",
    "Anal Cancer Screening Results  (P/ N/ N/A) ",
    "Treated for Anal Cancer  (Y/ N/ N/A) ",
    "Provided with modern FP services",
    "Provided with risk reduction counselling  (Y/N) ",
    "Experienced violence (Y/N) ",
    "Type of violence ",
    "Received post violence support",
    "Status in programme ",
    "Date of next appointment (DD/MM/YYYY)",
    "Remarks / Comments ",
]

# Canonical normalized base tokens for the 53 encounter headers
ENCOUNTER_BASE_TOKENS = [normalize_token(h) for h in REGISTER_ENCOUNTER_HEADERS]

# 3. Official KPLHIV column headers (72 columns in reference/KP_TEMPLATE.xlsx)
KPLHIV_HEADERS = [
    "Region",
    "PROGRAM UIC",
    "SR Name",
    "County",
    "Sub-County",
    "Attached PE code",
    "CCC No. (Provided by ART Centre)",
    "Sex (M/F)",
    "Population Type",
    "Date enrolled in the Program (dd/mm/yyyy)",
    "DOB (dd/mm/yyyy)",
    "Current AGE",
    "Age Group",
    "Date of HIV Diagnosis (dd/mm/yyyy)",
    "Date initiated ART (dd/mm/yyyy)",
    "Current ART Facility",
    "Duration on ART (Months)",
    "Pregnancy status",
    "On PMTCT",
    "EDD (dd/mm/yyyy)",
    "Screened for CaCx",
    "TPT status",
    "Date Initiated (dd/mm/yyyy)",
    "On TB Treatment",
    "Date Initiated (dd/mm/yyyy)",
    "Date Completed Treatment (dd/mm/yyyy)",
    "Last visit Date (dd/mm/yyyy)",
    "TCA (dd/mm/yyyy)",
    "TCA Months",
    "NFM3 (June2024 ART STATUS)",
    "No of Months ART Dispensed",
    "ART Regimen",
    "Jul",
    "Aug",
    "Sep",
    "No of Months ART Dispensed",
    "ART Regimen",
    "Oct",
    "Nov",
    "Dec",
    "No of Months ART Dispensed",
    "ART Regimen",
    "Jan",
    "Feb",
    "Mar",
    "No of Months ART Dispensed",
    "ART Regimen",
    "April",
    "May",
    "June",
    "No of Months ART Dispensed",
    "ART Regimen",
    "Date (dd/mm/yyyy)",
    "Months after last VL",
    "Levels (copies/ml)",
    "Due for VL",
    "Sample 1 Coll. Date (dd/mm/yyyy)",
    "Results 1 Received (dd/mm/yyyy)",
    "Levels (copies/ml)",
    "Sample 2 Coll. Date (dd/mm/yyyy)",
    "Results 2 Received (dd/mm/yyyy)",
    "Levels (copies/ml)",
    "CD4 Date (dd/mm/yyyy)",
    "CD4 Count Cells /mm3",
    "CD4 Date (dd/mm/yyyy)",
    "CD4 Count Cells /mm3",
    "Enrolled in PSSG (dd/mm/yyyy)",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Remarks",
]


def is_kp_template_register(raw_columns: list[str]) -> bool:
    """Detects whether raw register columns match the official 53-column-per-encounter KP template structure."""
    if len(raw_columns) < 72:
        return False

    # Check if index 19 (encounter 1) and index 72 (encounter 2) are both 'received_peer_education_y_n'
    norm_19 = normalize_token(raw_columns[19])
    norm_72 = normalize_token(raw_columns[72])

    if "received_peer_education" in norm_19 and "received_peer_education" in norm_72:
        return True

    # Check if total columns is exactly 337 (19 demographics + 6 * 53)
    if len(raw_columns) == 337:
        return True

    return False


def build_register_template_mapping(
    raw_columns: list[str],
    alias_map: dict[str, list[str]] | None = None,
    required_columns: list[str] | None = None,
) -> dict[str, str]:
    """Generates complete canonical mapping for all Register columns.

    Supports:
    1. Official 337-column KP_TEMPLATE.xlsx structure with 6 visit encounter blocks of 53 columns each.
    2. Legacy / synthetic files with pre-suffixed columns (e.g. prep_status_1).
    """
    if alias_map is None:
        alias_map = DEFAULT_REGISTER_ALIASES

    # If the sheet is the official 337-column template (or multi-block template):
    if is_kp_template_register(raw_columns):
        mapping: dict[str, str] = {}

        # 1. Map demographic headers (first 19 columns) using priority alias resolver
        demo_cols = raw_columns[:19]
        demo_mapping = resolve_column_aliases(
            raw_columns=demo_cols,
            alias_map=alias_map,
            required_columns=required_columns,
        )
        mapping.update(demo_mapping)

        # 2. Map clinical encounter blocks (53 columns per block, up to 6 visits)
        num_encounters = min(6, (len(raw_columns) - 19) // 53)
        for enc in range(num_encounters):
            visit_num = enc + 1
            for i, base_tok in enumerate(ENCOUNTER_BASE_TOKENS):
                col_idx = 19 + enc * 53 + i
                if col_idx < len(raw_columns):
                    raw_col = raw_columns[col_idx]
                    canonical_name = f"{base_tok}_{visit_num}"
                    mapping[raw_col] = canonical_name

        return mapping

    # Fallback to standard alias resolution for synthetic / legacy files
    return resolve_column_aliases(
        raw_columns=raw_columns,
        alias_map=alias_map,
        required_columns=required_columns,
    )


def build_kplhiv_template_mapping(
    raw_columns: list[str],
    alias_map: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    """Generates complete canonical mapping for KPLHIV columns.

    Maps:
    - Demographic keys (UIC, CCC number, county, sr_name, region, age, sex)
    - Primary viral load copies/ml (Col 55 in KP_TEMPLATE) to levels_copies_ml_
    """
    mapping: dict[str, str] = {}

    for idx, raw_col in enumerate(raw_columns):
        norm = normalize_token(raw_col)

        # Map core demographic identifiers
        if "program_uic" in norm or ("uic" in norm and "client" not in norm):
            mapping[raw_col] = "kp_vp_unique_identifier_code"
        elif "ccc" in norm:
            mapping[raw_col] = "ccc_number_nupi_n_a_10_digit_number_"
        elif norm == "county":
            mapping[raw_col] = "county"
        elif "sr" in norm or "sub_recipient" in norm or "partner" in norm:
            mapping[raw_col] = "sr_name"
        elif "region" in norm:
            mapping[raw_col] = "region"
        elif norm in ["sex", "gender", "sex_m_f_"]:
            mapping[raw_col] = "sex_m_f_"
        elif norm in ["age", "current_age"]:
            mapping[raw_col] = "age"
        elif "date_enrolled" in norm:
            mapping[raw_col] = "date_of_enrolment"
        elif "dob" in norm or "date_of_birth" in norm:
            mapping[raw_col] = "date_of_birth_dd_mm_yyyy_"
        elif "art_regimen" in norm:
            mapping[raw_col] = f"art_regimen_{idx}"
        # Primary viral load levels (copies/ml)
        elif "levels_copies_ml" in norm or norm == "levels":
            if "levels_copies_ml_" not in mapping.values():
                mapping[raw_col] = "levels_copies_ml_"
            else:
                mapping[raw_col] = f"levels_copies_ml_{idx}"

    return mapping
