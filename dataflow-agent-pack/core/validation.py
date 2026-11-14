"""Data-Quality Assurance (DQA) engine for DATAFLOW.

Implements:
1. Complete rule registry with severity classification (Critical, Major, Minor, Info).
2. Rules per Master Brief §9-D, notebook cells 17, 28, 34, 36, 38, 40, 42, and Decisions D-014..D-019:
   - DQA_DUPLICATE_UIC (Critical, D-017)
   - DQA_MISSING_UIC (Critical)
   - DQA_MISSING_COUNTY (Critical)
   - DQA_MISSING_SR_NAME (Critical, D-009)
   - DQA_HIV_NEG_ON_ART (Critical, D-014)
   - DQA_PREP_ON_POSITIVE (Critical)
   - DQA_CCC_REG_NOT_KPLHIV (Critical, D-018)
   - DQA_HIV_POS_NO_ART (Major, D-014)
   - DQA_TB_UNSCREENED (Major, D-015)
   - DQA_STI_UNSCREENED (Major, D-016)
   - DQA_MULTIPLE_PREP_INITIATIONS (Major)
   - DQA_CCC_KPLHIV_NOT_REG (Major, D-018)
   - DQA_MISSING_AGE (Major)
   - DQA_MISSING_SEX (Major)
   - DQA_MISSING_DOB (Major)
   - DQA_MISSING_ENROLMENT_DATE (Major)
   - DQA_MISSING_PE_CODE (Major)
   - DQA_UNPARSEABLE_DATE (Minor)
   - DQA_INVALID_VOCABULARY (Minor, D-008)
3. Structured DQAResult containing exception DataFrame and aggregate summary table.
4. block_on_critical setting (D-019) guarding downstream export.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from core.exceptions import DataFlowError


class CriticalDQAError(DataFlowError):
    """Raised when Critical DQA exceptions exist and block_on_critical is enabled."""

    def __init__(self, message: str, critical_counts: dict[str, int]):
        super().__init__(message)
        self.critical_counts = critical_counts


@dataclass(frozen=True)
class DQARule:
    """Metadata and definition of a single DQA rule."""

    id: str
    name: str
    severity: str  # Critical, Major, Minor, Info
    description: str
    suggested_action: str
    populations: list[str] = field(default_factory=lambda: ["ALL"])
    sheet_target: str = "Register"  # Register, KPLHIV, Cross-sheet


class DQARuleCounts(dict):
    """Case-insensitive and prefix-tolerant dictionary for DQA rule counts."""

    def __getitem__(self, key: str) -> int:
        if super().__contains__(key):
            return super().__getitem__(key)
        norm = str(key).lower().removeprefix("dqa_")
        if super().__contains__(norm):
            return super().__getitem__(norm)
        upper_dqa = f"DQA_{norm.upper()}"
        if super().__contains__(upper_dqa):
            return super().__getitem__(upper_dqa)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = 0) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        if isinstance(key, str):
            norm = key.lower().removeprefix("dqa_")
            if super().__contains__(norm):
                return True
            upper_dqa = f"DQA_{norm.upper()}"
            if super().__contains__(upper_dqa):
                return True
        return False


@dataclass
class DQAResults:
    """Aggregated output of a DQA execution run."""

    exceptions_df: pd.DataFrame
    summary_df: pd.DataFrame
    rule_counts: dict[str, int]
    severity_counts: dict[str, int]
    has_critical: bool
    total_exceptions: int

    def get_critical_counts(self) -> dict[str, int]:
        """Returns counts for critical rules only."""
        if self.exceptions_df.empty:
            return DQARuleCounts()
        crit = self.exceptions_df[self.exceptions_df["severity"] == "Critical"]
        return DQARuleCounts(crit["rule_id"].value_counts().to_dict())


# ---------------------------------------------------------------------------
# RULE REGISTRY METADATA
# ---------------------------------------------------------------------------

RULE_DEFINITIONS: dict[str, DQARule] = {
    "duplicate_uic": DQARule(
        id="duplicate_uic",
        name="Duplicate UIC in Register",
        severity="Critical",
        description="Multiple records found sharing the same Unique Identifier Code (UIC).",
        suggested_action="Review duplicate client encounters with Sub-Recipient; merge records if same visit or update UIC if distinct clients.",
        sheet_target="Register",
    ),
    "missing_uic": DQARule(
        id="missing_uic",
        name="Missing Client UIC",
        severity="Critical",
        description="Client record is missing mandatory Unique Identifier Code.",
        suggested_action="Assign valid programmatic UIC prior to reporting.",
        sheet_target="Register",
    ),
    "missing_county": DQARule(
        id="missing_county",
        name="Missing County Geography",
        severity="Critical",
        description="Client record is missing County geographical classification.",
        suggested_action="Assign valid County to maintain reporting geographic integrity.",
        sheet_target="Register",
    ),
    "missing_sr_name": DQARule(
        id="missing_sr_name",
        name="Missing Sub-Recipient Name",
        severity="Critical",
        description="Client record has missing or 'Unknown' Sub-Recipient (SR) name.",
        suggested_action="Assign valid implementing Sub-Recipient organization name.",
        sheet_target="Register",
    ),
    "hiv_neg_on_art": DQARule(
        id="hiv_neg_on_art",
        name="HIV Negative on ART",
        severity="Critical",
        description="Inconsistent clinical status: HIV-negative client documented as currently on ART.",
        suggested_action="Verify HIV test confirmation and ART regimen linkage.",
        sheet_target="Register",
    ),
    "prep_on_positive": DQARule(
        id="prep_on_positive",
        name="PrEP Initiated/Refilled on HIV Positive Client",
        severity="Critical",
        description="Inconsistent clinical status: HIV-positive client initiated, restarted, or refilled on PrEP.",
        suggested_action="Discontinue PrEP immediately; verify ART linkage and confirmatory testing.",
        sheet_target="Register",
    ),
    "ccc_reg_not_kplhiv": DQARule(
        id="ccc_reg_not_kplhiv",
        name="Register CCC Missing in KPLHIV Sheet",
        severity="Critical",
        description="Client documented with a CCC number in the Register sheet is missing from the KPLHIV sheet.",
        suggested_action="Add client to KPLHIV register to track ART outcomes and viral load monitoring.",
        sheet_target="Cross-sheet",
    ),
    "hiv_pos_no_art": DQARule(
        id="hiv_pos_no_art",
        name="HIV Positive Not on ART",
        severity="Major",
        description="Clinical linkage gap: HIV-positive client not documented as currently on ART.",
        suggested_action="Link client to ART facility and document CCC number and ART initiation.",
        sheet_target="Register",
    ),
    "tb_unscreened": DQARule(
        id="tb_unscreened",
        name="TB Diagnosed Without Documented Screening",
        severity="Major",
        description="Client diagnosed with TB without documented prior TB screening.",
        suggested_action="Complete TB screening assessment documentation in register.",
        sheet_target="Register",
    ),
    "sti_unscreened": DQARule(
        id="sti_unscreened",
        name="STI Diagnosed/Treated Without Documented Screening",
        severity="Major",
        description="Client diagnosed or treated for STI without documented prior STI syndromic screening.",
        suggested_action="Complete STI syndromic screening assessment documentation in register.",
        sheet_target="Register",
    ),
    "multiple_prep_initiations": DQARule(
        id="multiple_prep_initiations",
        name="Multiple PrEP Initiations in Period",
        severity="Major",
        description="Client documented with multiple PrEP initiations within the reporting period.",
        suggested_action="Verify whether subsequent initiation should be coded as 'Restart' or 'Refill'.",
        sheet_target="Register",
    ),
    "ccc_kplhiv_not_reg": DQARule(
        id="ccc_kplhiv_not_reg",
        name="KPLHIV Client CCC Missing in Register Sheet",
        severity="Major",
        description="Client in KPLHIV sheet has a CCC number that does not exist in the primary Register sheet.",
        suggested_action="Verify client enrollment in primary cohort register.",
        sheet_target="Cross-sheet",
    ),
    "missing_age": DQARule(
        id="missing_age",
        name="Missing Client Age",
        severity="Major",
        description="Client record is missing numeric age.",
        suggested_action="Document client age or calculate from Date of Birth.",
        sheet_target="Register",
    ),
    "missing_sex": DQARule(
        id="missing_sex",
        name="Missing Biological Sex",
        severity="Major",
        description="Client record is missing biological sex.",
        suggested_action="Document client sex in register per national guidelines.",
        sheet_target="Register",
    ),
    "missing_dob": DQARule(
        id="missing_dob",
        name="Missing Date of Birth",
        severity="Major",
        description="Client record is missing Date of Birth.",
        suggested_action="Record client date of birth for age cohort validation.",
        sheet_target="Register",
    ),
    "missing_enrolment_date": DQARule(
        id="missing_enrolment_date",
        name="Missing Date of Enrolment",
        severity="Major",
        description="Client record is missing Date of Enrolment into key population program.",
        suggested_action="Verify and document date client was enrolled into cohort.",
        sheet_target="Register",
    ),
    "missing_pe_code": DQARule(
        id="missing_pe_code",
        name="Missing Peer Educator Code",
        severity="Major",
        description="Client record is missing Peer Educator Code.",
        suggested_action="Assign outreach peer educator code to client.",
        sheet_target="Register",
    ),
    "unparseable_date": DQARule(
        id="unparseable_date",
        name="Unparseable Date Format",
        severity="Minor",
        description="Date value does not conform to standard format and was coerced to null/NaT.",
        suggested_action="Format date as DD/MM/YYYY.",
        sheet_target="Register",
    ),
    "invalid_vocabulary": DQARule(
        id="invalid_vocabulary",
        name="Controlled Vocabulary Inconsistency",
        severity="Minor",
        description="Categorical value does not conform to national controlled vocabulary.",
        suggested_action="Standardize dropdown entry to national vocabulary standards.",
        sheet_target="Register",
    ),
}

# Add backward compatibility aliases so legacy uppercase lookups resolve seamlessly
for _k, _rule in list(RULE_DEFINITIONS.items()):
    RULE_DEFINITIONS[f"DQA_{_k.upper()}"] = _rule


# ---------------------------------------------------------------------------
# VECTORIZED DQA RULE IMPLEMENTATIONS
# ---------------------------------------------------------------------------


def _get_uic_series(df: pd.DataFrame) -> pd.Series:
    """Safely retrieves client UIC series."""
    for col in ["kp_vp_unique_identifier_code", "program_uic", "kp_vp_unique_identifier_code_"]:
        if col in df.columns:
            return df[col].astype(str).str.strip().mask(df[col].isna(), "")
    return pd.Series("", index=df.index)


def _get_geo_fields(df: pd.DataFrame, idx: int) -> tuple[str, str, str]:
    """Safely retrieves (region, sr_name, county) for a given row index."""
    region = (
        str(df.at[idx, "region"])
        if "region" in df.columns and pd.notna(df.at[idx, "region"])
        else "UNKNOWN"
    )
    sr_name = (
        str(df.at[idx, "sr_name"])
        if "sr_name" in df.columns and pd.notna(df.at[idx, "sr_name"])
        else "UNKNOWN"
    )
    county = (
        str(df.at[idx, "county"])
        if "county" in df.columns and pd.notna(df.at[idx, "county"])
        else "UNKNOWN"
    )
    return region, sr_name, county


def check_duplicate_uic(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags all rows sharing a duplicate UIC per D-017 (keep=False)."""
    uic_col = "kp_vp_unique_identifier_code"
    if uic_col not in reg_df.columns:
        return []

    uic_s = reg_df[uic_col].dropna()
    uic_s = uic_s[uic_s.astype(str).str.strip() != ""]
    dup_mask = reg_df[uic_col].isin(uic_s[uic_s.duplicated(keep=False)])

    records = []
    rule = RULE_DEFINITIONS["duplicate_uic"]
    for idx in reg_df[dup_mask].index:
        region, sr_name, county = _get_geo_fields(reg_df, idx)
        records.append(
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "severity": rule.severity,
                "sheet": "Register",
                "row_index": idx,
                "uic": str(reg_df.at[idx, uic_col]),
                "region": region,
                "sr_name": sr_name,
                "county": county,
                "offending_columns": uic_col,
                "suggested_action": rule.suggested_action,
            }
        )
    return records


def check_missing_demographic_field(
    reg_df: pd.DataFrame,
    col_name: str,
    rule_id: str,
    treat_unknown_as_missing: bool = False,
) -> list[dict[str, Any]]:
    """Generic check for missing required demographic fields."""
    if col_name not in reg_df.columns:
        return []

    s = reg_df[col_name]
    if treat_unknown_as_missing:
        mask = s.isna() | s.astype(str).str.strip().str.lower().isin(["", "nan", "none", "unknown"])
    else:
        mask = s.isna() | (s.astype(str).str.strip() == "")

    records = []
    rule = RULE_DEFINITIONS[rule_id]
    uic_s = _get_uic_series(reg_df)
    for idx in reg_df[mask].index:
        region, sr_name, county = _get_geo_fields(reg_df, idx)
        records.append(
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "severity": rule.severity,
                "sheet": "Register",
                "row_index": idx,
                "uic": uic_s.get(idx, ""),
                "region": region,
                "sr_name": sr_name,
                "county": county,
                "offending_columns": col_name,
                "suggested_action": rule.suggested_action,
            }
        )
    return records


def check_hiv_neg_on_art(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags HIV-negative clients receiving ART (D-014).

    Evaluates across all visit encounter columns: hiv_tested_results_* == 'Negative' and currently_on_art_* == 'Yes'.
    """
    rule = RULE_DEFINITIONS["hiv_neg_on_art"]
    hiv_cols = sorted([c for c in reg_df.columns if re.match(r"^hiv_tested_results.*", c)])
    art_cols = sorted([c for c in reg_df.columns if re.match(r"^currently_on_art.*", c)])

    if not hiv_cols or not art_cols:
        return []

    # Pair visit columns by index
    records = []
    uic_s = _get_uic_series(reg_df)
    for h_col, a_col in zip(hiv_cols, art_cols, strict=False):
        h_s = reg_df[h_col].astype(str).str.strip().str.lower()
        a_s = reg_df[a_col].astype(str).str.strip().str.lower()

        # Flag where HIV is Negative and ART is Yes
        mask = (h_s == "negative") & (a_s == "yes")
        for idx in reg_df[mask].index:
            region, sr_name, county = _get_geo_fields(reg_df, idx)
            records.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "sheet": "Register",
                    "row_index": idx,
                    "uic": uic_s.get(idx, ""),
                    "region": region,
                    "sr_name": sr_name,
                    "county": county,
                    "offending_columns": f"{h_col}, {a_col}",
                    "suggested_action": rule.suggested_action,
                }
            )
    return records


def check_prep_on_positive(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags HIV-positive clients initiated/refilled on PrEP (notebook cell 36)."""
    rule = RULE_DEFINITIONS["prep_on_positive"]
    prep_cols = sorted([c for c in reg_df.columns if re.match(r"^prep_status.*", c)])
    hiv_cols = sorted([c for c in reg_df.columns if re.match(r"^hiv_tested_results.*", c)])

    if not prep_cols:
        return []

    records = []
    uic_s = _get_uic_series(reg_df)
    active_prep_values = {"initiated", "restart", "refill", "switched"}

    # Base status check
    base_hiv_pos = pd.Series(False, index=reg_df.index)
    if "hiv_status_at_enrollment" in reg_df.columns:
        base_hiv_pos = (
            reg_df["hiv_status_at_enrollment"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["positive", "known positive"])
        )

    for i, p_col in enumerate(prep_cols):
        p_s = reg_df[p_col].astype(str).str.strip().str.lower()
        on_prep = p_s.isin(active_prep_values)

        # Check visit HIV result if available, else fallback to baseline HIV
        if i < len(hiv_cols):
            h_col = hiv_cols[i]
            h_s = reg_df[h_col].astype(str).str.strip().str.lower()
            is_pos = h_s.isin(["positive", "known positive"]) | base_hiv_pos
            offending = f"{p_col}, {h_col}"
        else:
            is_pos = base_hiv_pos
            offending = f"{p_col}, hiv_status_at_enrollment"

        mask = on_prep & is_pos
        for idx in reg_df[mask].index:
            region, sr_name, county = _get_geo_fields(reg_df, idx)
            records.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "sheet": "Register",
                    "row_index": idx,
                    "uic": uic_s.get(idx, ""),
                    "region": region,
                    "sr_name": sr_name,
                    "county": county,
                    "offending_columns": offending,
                    "suggested_action": rule.suggested_action,
                }
            )
    return records


def check_hiv_pos_no_art(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags HIV-positive clients who are not on ART (D-014)."""
    rule = RULE_DEFINITIONS["hiv_pos_no_art"]
    hiv_cols = sorted([c for c in reg_df.columns if re.match(r"^hiv_tested_results.*", c)])
    art_cols = sorted([c for c in reg_df.columns if re.match(r"^currently_on_art.*", c)])

    if not hiv_cols or not art_cols:
        return []

    records = []
    uic_s = _get_uic_series(reg_df)
    for h_col, a_col in zip(hiv_cols, art_cols, strict=False):
        h_s = reg_df[h_col].astype(str).str.strip().str.lower()
        a_s = reg_df[a_col].astype(str).str.strip().str.lower()

        # Flag where HIV is Positive and ART is No / missing
        mask = h_s.isin(["positive", "known positive"]) & (a_s != "yes")
        for idx in reg_df[mask].index:
            region, sr_name, county = _get_geo_fields(reg_df, idx)
            records.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "sheet": "Register",
                    "row_index": idx,
                    "uic": uic_s.get(idx, ""),
                    "region": region,
                    "sr_name": sr_name,
                    "county": county,
                    "offending_columns": f"{h_col}, {a_col}",
                    "suggested_action": rule.suggested_action,
                }
            )
    return records


def check_tb_unscreened(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags TB diagnosed without documented screening (D-015)."""
    rule = RULE_DEFINITIONS["tb_unscreened"]
    screen_cols = sorted([c for c in reg_df.columns if re.match(r"^screened_for_tb.*", c)])
    diag_cols = sorted([c for c in reg_df.columns if re.match(r"^diagnosed_with_tb.*", c)])

    if not diag_cols:
        return []

    records = []
    uic_s = _get_uic_series(reg_df)
    for i, d_col in enumerate(diag_cols):
        d_s = reg_df[d_col].astype(str).str.strip().str.lower()
        is_diag = d_s == "yes"

        if i < len(screen_cols):
            s_col = screen_cols[i]
            s_s = reg_df[s_col].astype(str).str.strip().str.lower()
            not_screened = s_s != "yes"
            offending = f"{s_col}, {d_col}"
        else:
            # Check across all screening columns
            not_screened = pd.Series(True, index=reg_df.index)
            if screen_cols:
                all_screened = (
                    reg_df[screen_cols]
                    .apply(lambda col: col.astype(str).str.strip().str.lower() == "yes")
                    .any(axis=1)
                )
                not_screened = ~all_screened
            offending = d_col

        mask = is_diag & not_screened
        for idx in reg_df[mask].index:
            region, sr_name, county = _get_geo_fields(reg_df, idx)
            records.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "sheet": "Register",
                    "row_index": idx,
                    "uic": uic_s.get(idx, ""),
                    "region": region,
                    "sr_name": sr_name,
                    "county": county,
                    "offending_columns": offending,
                    "suggested_action": rule.suggested_action,
                }
            )
    return records


def check_sti_unscreened(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags STI diagnosed/treated without documented screening (D-016)."""
    rule = RULE_DEFINITIONS["sti_unscreened"]
    screen_cols = sorted([c for c in reg_df.columns if re.match(r"^screened_for_stis.*", c)])
    diag_cols = sorted([c for c in reg_df.columns if re.match(r"^diagnosed_with_sti.*", c)])
    treat_cols = sorted([c for c in reg_df.columns if re.match(r"^treated_for_stis.*", c)])

    if not diag_cols and not treat_cols:
        return []

    records = []
    uic_s = _get_uic_series(reg_df)
    num_encounters = max(len(diag_cols), len(treat_cols))

    for i in range(num_encounters):
        d_col = diag_cols[i] if i < len(diag_cols) else None
        t_col = treat_cols[i] if i < len(treat_cols) else None
        s_col = screen_cols[i] if i < len(screen_cols) else None

        is_diag = pd.Series(False, index=reg_df.index)
        if d_col:
            is_diag |= reg_df[d_col].astype(str).str.strip().str.lower() == "yes"
        if t_col:
            is_diag |= reg_df[t_col].astype(str).str.strip().str.lower() == "yes"

        if s_col:
            s_s = reg_df[s_col].astype(str).str.strip().str.lower()
            not_screened = s_s != "yes"
            cols = [c for c in [s_col, d_col, t_col] if c]
            offending = ", ".join(cols)
        else:
            not_screened = pd.Series(True, index=reg_df.index)
            cols = [c for c in [d_col, t_col] if c]
            offending = ", ".join(cols)

        mask = is_diag & not_screened
        for idx in reg_df[mask].index:
            region, sr_name, county = _get_geo_fields(reg_df, idx)
            records.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "sheet": "Register",
                    "row_index": idx,
                    "uic": uic_s.get(idx, ""),
                    "region": region,
                    "sr_name": sr_name,
                    "county": county,
                    "offending_columns": offending,
                    "suggested_action": rule.suggested_action,
                }
            )
    return records


def check_multiple_prep_initiations(reg_df: pd.DataFrame, **kwargs: Any) -> list[dict[str, Any]]:
    """Flags clients with >1 PrEP Initiations in reporting period (notebook cell 34)."""
    rule = RULE_DEFINITIONS["multiple_prep_initiations"]
    prep_cols = sorted([c for c in reg_df.columns if re.match(r"^prep_status.*", c)])

    if not prep_cols:
        return []

    init_counts = (
        reg_df[prep_cols]
        .apply(lambda col: col.astype(str).str.strip().str.lower() == "initiated")
        .sum(axis=1)
    )

    mask = init_counts > 1
    records = []
    uic_s = _get_uic_series(reg_df)
    for idx in reg_df[mask].index:
        region, sr_name, county = _get_geo_fields(reg_df, idx)
        records.append(
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "severity": rule.severity,
                "sheet": "Register",
                "row_index": idx,
                "uic": uic_s.get(idx, ""),
                "region": region,
                "sr_name": sr_name,
                "county": county,
                "offending_columns": ", ".join(prep_cols),
                "suggested_action": rule.suggested_action,
            }
        )
    return records


def check_cross_sheet_ccc(
    reg_df: pd.DataFrame,
    kplhiv_df: pd.DataFrame,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Checks CCC reconciliation between Register and KPLHIV sheets in both directions (D-018)."""
    records = []

    # Identify CCC columns
    reg_ccc_col = None
    for c in ["ccc_number_nupi_n_a_10_digit_number_", "ccc_number", "ccc_no"]:
        if c in reg_df.columns:
            reg_ccc_col = c
            break

    kplhiv_ccc_col = None
    for c in [
        "ccc_number_nupi_n_a_10_digit_number_",
        "ccc_no_provided_by_art_centre_",
        "ccc_no",
        "ccc_number",
    ]:
        if c in kplhiv_df.columns:
            kplhiv_ccc_col = c
            break

    if not reg_ccc_col or not kplhiv_ccc_col:
        return []

    # Clean CCC sets
    reg_clean_ccc = reg_df[reg_ccc_col].dropna().astype(str).str.strip()
    reg_clean_ccc = reg_clean_ccc[~reg_clean_ccc.str.lower().isin(["", "nan", "none", "n/a"])]

    kp_clean_ccc = kplhiv_df[kplhiv_ccc_col].dropna().astype(str).str.strip()
    kp_clean_ccc = kp_clean_ccc[~kp_clean_ccc.str.lower().isin(["", "nan", "none", "n/a"])]

    kp_ccc_set = set(kp_clean_ccc)
    reg_ccc_set = set(reg_clean_ccc)

    # 1. Register CCC missing in KPLHIV (Critical per D-018)
    rule_reg_not_kp = RULE_DEFINITIONS["ccc_reg_not_kplhiv"]
    uic_reg = _get_uic_series(reg_df)
    mask_reg = reg_df[reg_ccc_col].isin(reg_clean_ccc[~reg_clean_ccc.isin(kp_ccc_set)])
    for idx in reg_df[mask_reg].index:
        region, sr_name, county = _get_geo_fields(reg_df, idx)
        records.append(
            {
                "rule_id": rule_reg_not_kp.id,
                "rule_name": rule_reg_not_kp.name,
                "severity": rule_reg_not_kp.severity,
                "sheet": "Register",
                "row_index": idx,
                "uic": uic_reg.get(idx, ""),
                "region": region,
                "sr_name": sr_name,
                "county": county,
                "offending_columns": reg_ccc_col,
                "suggested_action": rule_reg_not_kp.suggested_action,
            }
        )

    # 2. KPLHIV CCC missing in Register (Major per D-018)
    rule_kp_not_reg = RULE_DEFINITIONS["ccc_kplhiv_not_reg"]
    uic_kp = _get_uic_series(kplhiv_df)
    mask_kp = kplhiv_df[kplhiv_ccc_col].isin(kp_clean_ccc[~kp_clean_ccc.isin(reg_ccc_set)])
    for idx in kplhiv_df[mask_kp].index:
        region, sr_name, county = _get_geo_fields(kplhiv_df, idx)
        records.append(
            {
                "rule_id": rule_kp_not_reg.id,
                "rule_name": rule_kp_not_reg.name,
                "severity": rule_kp_not_reg.severity,
                "sheet": "KPLHIV",
                "row_index": idx,
                "uic": uic_kp.get(idx, ""),
                "region": region,
                "sr_name": sr_name,
                "county": county,
                "offending_columns": kplhiv_ccc_col,
                "suggested_action": rule_kp_not_reg.suggested_action,
            }
        )

    return records


# ---------------------------------------------------------------------------
# MAIN DQA PIPELINE RUNNER
# ---------------------------------------------------------------------------


def run_dqa(
    register_df: pd.DataFrame,
    kplhiv_df: pd.DataFrame | None = None,
    population: str = "FSW",
    block_on_critical: bool = True,
) -> DQAResults:
    """Executes all registered DQA rules on cleaned Register and KPLHIV DataFrames.

    Guarantees:
    - Pure execution: input DataFrames remain 100% immutable (no record is auto-resolved or deleted).
    - Returns structured DQAResults with exceptions_df and aggregate summary_df.
    - If block_on_critical is True, caller can inspect results.has_critical to halt export.
    """
    if kplhiv_df is None:
        kplhiv_df = pd.DataFrame()

    all_exceptions: list[dict[str, Any]] = []

    # 1. Duplicate UIC (Critical)
    all_exceptions.extend(check_duplicate_uic(register_df))

    # 2. Missing Key Demographic Columns
    all_exceptions.extend(
        check_missing_demographic_field(
            register_df, "kp_vp_unique_identifier_code", "missing_uic"
        )
    )
    all_exceptions.extend(
        check_missing_demographic_field(register_df, "county", "missing_county")
    )
    all_exceptions.extend(
        check_missing_demographic_field(
            register_df, "sr_name", "missing_sr_name", treat_unknown_as_missing=True
        )
    )
    all_exceptions.extend(check_missing_demographic_field(register_df, "age", "missing_age"))
    all_exceptions.extend(
        check_missing_demographic_field(register_df, "sex_m_f_", "missing_sex")
    )
    all_exceptions.extend(
        check_missing_demographic_field(register_df, "date_of_birth_dd_mm_yyyy_", "missing_dob")
    )
    all_exceptions.extend(
        check_missing_demographic_field(
            register_df, "date_of_enrolment", "missing_enrolment_date"
        )
    )
    all_exceptions.extend(
        check_missing_demographic_field(register_df, "peer_educator_code", "missing_pe_code")
    )

    # 3. Clinical Inconsistencies
    all_exceptions.extend(check_hiv_neg_on_art(register_df))
    all_exceptions.extend(check_prep_on_positive(register_df))
    all_exceptions.extend(check_hiv_pos_no_art(register_df))
    all_exceptions.extend(check_tb_unscreened(register_df))
    all_exceptions.extend(check_sti_unscreened(register_df))
    all_exceptions.extend(check_multiple_prep_initiations(register_df))

    # 4. Cross-Sheet Reconciliation
    if not kplhiv_df.empty:
        all_exceptions.extend(check_cross_sheet_ccc(register_df, kplhiv_df))

    # Build Exception DataFrame
    if all_exceptions:
        exceptions_df = pd.DataFrame(all_exceptions)
    else:
        exceptions_df = pd.DataFrame(
            columns=[
                "rule_id",
                "rule_name",
                "severity",
                "sheet",
                "row_index",
                "uic",
                "region",
                "sr_name",
                "county",
                "offending_columns",
                "suggested_action",
            ]
        )

    # Compute Summaries
    rule_counts = DQARuleCounts(
        exceptions_df["rule_id"].value_counts().to_dict() if not exceptions_df.empty else {}
    )
    severity_counts = (
        exceptions_df["severity"].value_counts().to_dict() if not exceptions_df.empty else {}
    )

    has_critical = severity_counts.get("Critical", 0) > 0
    total_exceptions = len(exceptions_df)

    if not exceptions_df.empty:
        summary_df = (
            exceptions_df.groupby(
                ["rule_id", "rule_name", "severity", "region", "sr_name", "county"],
                as_index=False,
            )
            .size()
            .rename(columns={"size": "exception_count"})
        )
    else:
        summary_df = pd.DataFrame(
            columns=[
                "rule_id",
                "rule_name",
                "severity",
                "region",
                "sr_name",
                "county",
                "exception_count",
            ]
        )

    return DQAResults(
        exceptions_df=exceptions_df,
        summary_df=summary_df,
        rule_counts=rule_counts,
        severity_counts=severity_counts,
        has_critical=has_critical,
        total_exceptions=total_exceptions,
    )


def format_aggregate_dqa_report(
    results: DQAResults,
    file_name: str = "Workbook",
    population: str = "FSW",
) -> str:
    """Formats an aggregate-only summary string for terminal output with zero client identifiers."""
    lines = [
        "=" * 70,
        f"DATAFLOW DQA AGGREGATE QUALITY REPORT: {file_name}",
        f"Population: {population.upper()} | Total Exceptions: {results.total_exceptions}",
        f"Severities -> Critical: {results.severity_counts.get('Critical', 0)} | Major: {results.severity_counts.get('Major', 0)} | Minor: {results.severity_counts.get('Minor', 0)}",
        "=" * 70,
    ]

    if results.total_exceptions == 0:
        lines.append("CONGRATULATIONS: 0 DQA quality exceptions found.")
        lines.append("=" * 70)
        return "\n".join(lines)

    lines.append("\nSummary by Rule & Severity:")
    lines.append(f"{'RULE ID':<30} | {'SEVERITY':<10} | {'COUNT':<6}")
    lines.append("-" * 52)
    seen_ids: set[str] = set()
    for _rule_id, rule_meta in RULE_DEFINITIONS.items():
        if rule_meta.id in seen_ids:
            continue
        seen_ids.add(rule_meta.id)
        cnt = results.rule_counts.get(rule_meta.id, 0)
        if cnt > 0:
            lines.append(f"{rule_meta.id:<30} | {rule_meta.severity:<10} | {cnt:<6}")

    lines.append("\n" + "=" * 70)
    lines.append("CONFIRMATION: Aggregate counts and rule IDs only. Zero client UICs printed.")
    lines.append("=" * 70)
    return "\n".join(lines)
