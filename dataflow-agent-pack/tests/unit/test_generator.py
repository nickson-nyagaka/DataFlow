"""Unit tests for synthetic data generator (Phase 1)."""

import tempfile
from pathlib import Path

import pandas as pd

from tests.synthetic.generator import generate_synthetic_data, write_synthetic_workbook


def test_generator_determinism():
    """Verifies that identical seed produces identical DataFrames and bit-for-bit identical workbooks."""
    reg1, kp1, gt1 = generate_synthetic_data(population="FSW", seed=123, num_clients=50)
    reg2, kp2, gt2 = generate_synthetic_data(population="FSW", seed=123, num_clients=50)

    pd.testing.assert_frame_equal(reg1, reg2)
    pd.testing.assert_frame_equal(kp1, kp2)
    assert gt1 == gt2

    with tempfile.TemporaryDirectory() as tmp_dir:
        p1 = Path(tmp_dir) / "wb1.xlsx"
        p2 = Path(tmp_dir) / "wb2.xlsx"

        _, sha1, _ = write_synthetic_workbook(
            population="FSW", output_path=p1, seed=123, num_clients=50
        )
        _, sha2, _ = write_synthetic_workbook(
            population="FSW", output_path=p2, seed=123, num_clients=50
        )

        assert sha1 == sha2
        assert p1.read_bytes() == p2.read_bytes()


def test_generator_planted_defects():
    """Verifies that all required defect categories from Master Brief §13.1 are planted with ground truth."""
    _, _, gt = generate_synthetic_data(population="PWID", seed=42, num_clients=200)
    planted = gt["planted_defects"]

    # Verify each defect type has non-zero count
    assert planted["duplicate_uic_encounters"] > 0
    assert planted["float_formatted_ids"] > 0
    assert planted["mixed_case_known_positive"] > 0
    assert planted["missing_age"] > 0
    assert planted["missing_sex"] > 0
    assert planted["missing_county"] > 0
    assert planted["missing_sr_name"] > 0
    assert planted["negative_on_art"] > 0
    assert planted["positive_not_on_art"] > 0
    assert planted["prep_in_positive"] > 0
    assert planted["tb_diagnosed_not_screened"] > 0
    assert planted["sti_diagnosed_not_screened"] > 0
    assert planted["viral_load_ldl"] > 0
    assert planted["viral_load_numeric_suppressed"] > 0
    assert planted["viral_load_unsuppressed"] > 0
    assert planted["viral_load_unparseable"] > 0
    assert planted["ccc_kplhiv_not_in_register"] > 0


def test_generator_multi_visit_sort_traps():
    """Verifies that >= 10 visit columns exist to test lexicographical sort traps."""
    reg, _, _ = generate_synthetic_data(population="FSW", seed=42, num_clients=20)
    prep_cols = [c for c in reg.columns if c.startswith("prep_status_")]
    assert len(prep_cols) >= 10
    assert "prep_status_10" in prep_cols
    assert "prep_status_1" in prep_cols
