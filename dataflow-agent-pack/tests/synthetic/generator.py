"""Deterministic Synthetic Data Generator for DATAFLOW Key Population registers.

Generates realistic Register and KPLHIV dataframes with planted defects and anomalies
per Master Brief §13.1, and emits ground_truth.json for verification.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def generate_synthetic_data(
    population: str = "FSW",
    num_clients: int = 200,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Generates synthetic Register and KPLHIV DataFrames with planted defects."""
    rng = np.random.default_rng(seed)

    counties = ["MOMBASA", "KILIFI", "KWALE", "NAIROBI", "KISUMU"]
    regions = ["COAST", "COAST", "COAST", "NRR", "WESTERN"]
    county_to_region = dict(zip(counties, regions, strict=True))
    sr_names = ["SR_ALPHA", "SR_BETA", "SR_GAMMA"]

    # Client IDs
    uics = [f"{population}{i + 1000:04d}" for i in range(num_clients)]

    # Ground truth counters
    ground_truth = {
        "population": population,
        "seed": seed,
        "total_unique_clients": num_clients,
        "planted_defects": {
            "duplicate_uic_encounters": 0,
            "float_formatted_ids": 0,
            "mixed_case_known_positive": 0,
            "missing_age": 0,
            "missing_sex": 0,
            "missing_county": 0,
            "missing_sr_name": 0,
            "negative_on_art": 0,
            "positive_not_on_art": 0,
            "prep_in_positive": 0,
            "tb_diagnosed_not_screened": 0,
            "sti_diagnosed_not_screened": 0,
            "viral_load_ldl": 0,
            "viral_load_numeric_suppressed": 0,
            "viral_load_unsuppressed": 0,
            "viral_load_unparseable": 0,
            "ccc_register_not_in_kplhiv": 0,
            "ccc_kplhiv_not_in_register": 0,
        },
    }

    # Build base Register rows
    reg_rows = []
    kplhiv_rows = []

    # Visit columns count (10 visits to test lexicographic sort trap)
    num_visits = 10

    for i, uic in enumerate(uics):
        county = rng.choice(counties)
        region = county_to_region[county]
        sr = rng.choice(sr_names)
        age = int(rng.integers(16, 48))
        sex = (
            "F" if population == "FSW" else ("M" if population == "MSM" else rng.choice(["M", "F"]))
        )
        pe_code = f"PE{rng.integers(1, 20):02d}"
        enrolment_month = int(rng.integers(1, 13))
        enrolment_date = f"2024-{enrolment_month:02d}-15"
        dob = f"{2024 - age}-05-12"

        # Plant defects systematically:
        # 1. Missing age (5 clients)
        if i in [5, 6, 7, 8, 9]:
            age = np.nan
            ground_truth["planted_defects"]["missing_age"] += 1

        # 2. Missing sex (3 clients)
        if i in [15, 16, 17]:
            sex = np.nan
            ground_truth["planted_defects"]["missing_sex"] += 1

        # 3. Missing geography (4 clients)
        if i in [22, 23]:
            county = np.nan
            ground_truth["planted_defects"]["missing_county"] += 1
        if i in [24, 25]:
            sr = np.nan
            ground_truth["planted_defects"]["missing_sr_name"] += 1

        # CCC number
        ccc_num = f"{rng.integers(10000, 99999)}{rng.integers(10000, 99999)}"
        # Plant float formatted ID (3 clients)
        if i in [30, 31, 32]:
            ccc_num = f"{ccc_num}.0"
            ground_truth["planted_defects"]["float_formatted_ids"] += 1

        # Initial baseline status
        hiv_status = "Negative"
        if i < 40:
            # 40 clients are positive / KPLHIV
            if i % 2 == 0:
                hiv_status = "Known positive"
            else:
                hiv_status = "Known Positive"  # Mixed case defect
                ground_truth["planted_defects"]["mixed_case_known_positive"] += 1

        row = {
            "kp_vp_unique_identifier_code": uic,
            "county": county,
            "region": region,
            "sr_name": sr,
            "age": age,
            "sex_m_f_": sex,
            "date_of_birth_dd_mm_yyyy_": dob,
            "date_of_enrolment": enrolment_date,
            "peer_educator_code": pe_code,
            "hiv_status_at_enrollment": hiv_status,
            "ccc_number_nupi_n_a_10_digit_number_": ccc_num
            if hiv_status in ["Known positive", "Known Positive"]
            else np.nan,
        }

        # Visit-level columns
        for v in range(1, num_visits + 1):
            # PrEP status
            prep = "Refill" if (i % 3 == 0 and hiv_status == "Negative") else "None"
            # Plant PrEP in Positive defect (clients 35, 36)
            if i in [35, 36] and v == 1:
                prep = "Initiated"
                hiv_status_v = "Positive"
                ground_truth["planted_defects"]["prep_in_positive"] += 1
            else:
                hiv_status_v = hiv_status

            # ART status
            art = (
                "Yes"
                if "Positive" in str(hiv_status_v) or "positive" in str(hiv_status_v)
                else "No"
            )

            # Plant Negative on ART (clients 50, 51)
            if i in [50, 51] and v == 1:
                hiv_status_v = "Negative"
                art = "Yes"
                ground_truth["planted_defects"]["negative_on_art"] += 1

            # Plant Positive not on ART (clients 38, 39)
            if i in [38, 39] and v == 1:
                hiv_status_v = "Positive"
                art = "No"
                ground_truth["planted_defects"]["positive_not_on_art"] += 1

            # TB screening and diagnosis
            tb_screen = "Yes" if i % 2 == 0 else "No"
            tb_diag = "No"
            # Plant TB diagnosed not screened (clients 60, 61)
            if i in [60, 61] and v == 1:
                tb_screen = "No"
                tb_diag = "Yes"
                ground_truth["planted_defects"]["tb_diagnosed_not_screened"] += 1

            # STI screening and diagnosis
            sti_screen = "Yes" if i % 2 == 0 else "No"
            sti_diag = "No"
            sti_treat = "No"
            # Plant STI diagnosed not screened (clients 70, 71)
            if i in [70, 71] and v == 1:
                sti_screen = "No"
                sti_diag = "Yes"
                sti_treat = "Yes"
                ground_truth["planted_defects"]["sti_diagnosed_not_screened"] += 1

            peer_ed = "Yes" if i % 4 != 0 else "No"
            rrc = "Yes" if i % 3 != 0 else "No"
            condoms = int(rng.integers(10, 50)) if i % 2 == 0 else 0
            nsp = int(rng.integers(5, 30)) if (population == "PWID" and i % 2 == 0) else 0

            row[f"prep_status_{v}"] = prep
            row[f"hiv_tested_results_p_n_nd_na_{v}"] = hiv_status_v
            row[f"currently_on_art_y_n_n_a_{v}"] = art
            row[f"screened_for_stis_y_n_{v}"] = sti_screen
            row[f"diagnosed_with_sti_y_n_{v}"] = sti_diag
            row[f"treated_for_stis_y_n_na_r_referred_{v}"] = sti_treat
            row[f"screened_for_tb_{v}"] = tb_screen
            row[f"diagnosed_with_tb_{v}"] = tb_diag
            row[f"received_peer_education_y_n_{v}"] = peer_ed
            row[f"provided_with_risk_reduction_counselling_y_n_{v}"] = rrc
            row[f"condoms_distributed_indicate_number_n_a_for_inmates_{v}"] = condoms
            row[f"needles_and_syringes_distributed_indicate_number_n_a_for_inmates_{v}"] = nsp
            row[f"art_outcome_{v}"] = "Active" if art == "Yes" else "None"

        reg_rows.append(row)

        # Plant duplicate UIC encounter (clients 80, 81, 82 have a second row)
        if i in [80, 81, 82]:
            dup_row = row.copy()
            dup_row["date_of_enrolment"] = "2024-09-20"
            dup_row["condoms_distributed_indicate_number_n_a_for_inmates_1"] = 15
            reg_rows.append(dup_row)
            ground_truth["planted_defects"]["duplicate_uic_encounters"] += 1

        # Populate KPLHIV sheet for positive clients
        if i < 40:
            vl_formats = ["LDL", "<LDL", "50", "150", "1,200", "9250cp/ml", "UNKNOWN", "junk_text"]
            vl_choice = vl_formats[i % len(vl_formats)]

            # Classify viral load ground truth
            if vl_choice in ["LDL", "<LDL"]:
                ground_truth["planted_defects"]["viral_load_ldl"] += 1
            elif vl_choice in ["50", "150"]:
                ground_truth["planted_defects"]["viral_load_numeric_suppressed"] += 1
            elif vl_choice in ["1,200", "9250cp/ml"]:
                ground_truth["planted_defects"]["viral_load_unsuppressed"] += 1
            else:
                ground_truth["planted_defects"]["viral_load_unparseable"] += 1

            kplhiv_ccc = ccc_num
            # Plant CCC mismatch: KPLHIV client not in Register (client 3)
            if i == 3:
                kplhiv_ccc = "9999988888"
                ground_truth["planted_defects"]["ccc_kplhiv_not_in_register"] += 1

            k_row = {
                "program_uic": uic,
                "county": county,
                "region": region,
                "sr_name": sr,
                "ccc_no_provided_by_art_centre_": kplhiv_ccc,
                "levels_copies_ml_": vl_choice,
                "jul": "Active" if i % 2 == 0 else "None",
                "aug": "Active" if i % 2 == 0 else "None",
                "sep": "Active" if i % 2 == 0 else "None",
                "oct": "Active" if i % 2 == 0 else "None",
                "nov": "Active" if i % 2 == 0 else "None",
                "dec": "Active" if i % 2 == 0 else "None",
            }
            kplhiv_rows.append(k_row)

    # Convert to DataFrames
    reg_df = pd.DataFrame(reg_rows)
    kplhiv_df = pd.DataFrame(kplhiv_rows)

    return reg_df, kplhiv_df, ground_truth


def write_synthetic_workbook(
    population: str,
    output_path: str | Path,
    seed: int = 42,
    num_clients: int = 200,
) -> tuple[Path, str, dict[str, Any]]:
    """Writes Register and KPLHIV sheets to Excel with metadata header rows (skiprows=2)."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    reg_df, kplhiv_df, ground_truth = generate_synthetic_data(
        population=population, seed=seed, num_clients=num_clients
    )

    # Register sheet name: MSM uses 'MSM', others use 'Register'
    reg_sheet = "MSM" if population.upper() == "MSM" else "Register"
    kp_sheet = "KPLHIV"

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        writer.book.properties.created = datetime.datetime(2026, 1, 1, 0, 0, 0)
        writer.book.properties.modified = datetime.datetime(2026, 1, 1, 0, 0, 0)

        # Write 2 dummy header rows to emulate skiprows=2
        dummy_header = pd.DataFrame([["METADATA ROW 1", ""], ["METADATA ROW 2", ""]])
        dummy_header.to_excel(writer, sheet_name=reg_sheet, index=False, header=False)
        reg_df.to_excel(writer, sheet_name=reg_sheet, startrow=2, index=False)

        dummy_header.to_excel(writer, sheet_name=kp_sheet, index=False, header=False)
        kplhiv_df.to_excel(writer, sheet_name=kp_sheet, startrow=2, index=False)

    # Normalize zip timestamps and XML metadata for bit-for-bit reproducibility
    raw_bytes = buf.getvalue()
    in_buf = io.BytesIO(raw_bytes)
    out_buf = io.BytesIO()
    with (
        zipfile.ZipFile(in_buf, "r") as zin,
        zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in sorted(zin.infolist(), key=lambda x: x.filename):
            data = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                data = re.sub(
                    rb"<dcterms:modified[^>]*>.*?</dcterms:modified>",
                    b'<dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>',
                    data,
                )
                data = re.sub(
                    rb"<dcterms:created[^>]*>.*?</dcterms:created>",
                    b'<dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>',
                    data,
                )
            item.date_time = (2026, 1, 1, 0, 0, 0)
            zout.writestr(item, data)

    deterministic_bytes = out_buf.getvalue()
    p.write_bytes(deterministic_bytes)

    # Compute SHA-256
    sha256 = hashlib.sha256(deterministic_bytes).hexdigest()

    # Emit ground truth JSON
    gt_path = p.parent / f"ground_truth_{population.lower()}.json"
    ground_truth["file_sha256"] = sha256
    ground_truth["file_path"] = str(p)
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    return p, sha256, ground_truth


def main():
    parser = argparse.ArgumentParser(description="DATAFLOW Synthetic Data Generator")
    parser.add_argument("--population", default="FSW", choices=["FSW", "MSM", "PWID", "TG", "VP"])
    parser.add_argument("--clients", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="tests/synthetic/fixtures/synthetic_register.xlsx")
    args = parser.parse_args()

    wb_path, sha, gt = write_synthetic_workbook(
        population=args.population,
        output_path=args.output,
        seed=args.seed,
        num_clients=args.clients,
    )
    print(f"Generated synthetic {args.population} workbook at: {wb_path}")
    print(f"File SHA-256: {sha}")
    print(f"Total planted defect types: {len(gt['planted_defects'])}")


if __name__ == "__main__":
    main()
