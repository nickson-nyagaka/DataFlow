"""Unit tests for configuration models and YAML validation (Phase 1)."""

import tempfile
from pathlib import Path

import pytest

from core.config_models import (
    load_compat_config,
    load_population_config,
    load_settings_config,
)
from core.exceptions import ConfigValidationError

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class TestPopulationConfigPositive:
    """Validates that all five production population YAMLs pass schema validation."""

    @pytest.mark.parametrize("pop", ["fsw", "msm", "tg", "pwid", "vp"])
    def test_production_population_yamls(self, pop: str):
        yaml_path = CONFIG_DIR / "populations" / f"{pop}.yaml"
        cfg = load_population_config(yaml_path)
        assert cfg.code == pop.upper()
        assert len(cfg.sheet_aliases_register) >= 1
        assert len(cfg.sheet_aliases_kplhiv) >= 1
        if pop == "pwid":
            assert cfg.defined_package.require_nsp is True
            assert cfg.reporting.include_nsp_block is True
        else:
            assert cfg.defined_package.require_nsp is False
            assert cfg.reporting.include_nsp_block is False

    def test_settings_config(self):
        cfg = load_settings_config(CONFIG_DIR / "settings.yaml")
        assert cfg.app_name == "DATAFLOW"
        assert cfg.max_upload_size_mb >= 10

    def test_compat_config(self):
        cfg = load_compat_config(CONFIG_DIR / "compat.yaml")
        assert cfg.legacy_missing_age_below_15 is True
        assert cfg.legacy_impute_missing_sex_f is True


class TestConfigNegative:
    """Negative tests asserting invalid configurations raise ConfigValidationError with file and key."""

    def _write_tmp(self, content: str) -> Path:
        t = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        t.write(content)
        t.close()
        return Path(t.name)

    def test_neg_01_missing_file(self):
        with pytest.raises(ConfigValidationError) as exc:
            load_population_config("non_existent_file.yaml")
        assert "file" in str(exc.value)

    def test_neg_02_invalid_yaml_syntax(self):
        p = self._write_tmp("code: [unclosed list")
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_03_non_dict_top_level(self):
        p = self._write_tmp("- item 1\n- item 2")
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_04_invalid_population_code(self):
        raw = """
code: "INVALID_CODE"
name: "Invalid Population"
sheet_aliases_register: ["Register"]
sheet_aliases_kplhiv: ["KPLHIV"]
defined_package:
  require_nsp: false
reporting:
  include_nsp_block: false
  sheet_name_q1: "Summary"
  sheet_name_sem: "Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert exc.value.key == "code"
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_05_missing_required_key(self):
        raw = """
name: "Missing Code Field"
sheet_aliases_register: ["Register"]
sheet_aliases_kplhiv: ["KPLHIV"]
defined_package:
  require_nsp: false
reporting:
  include_nsp_block: false
  sheet_name_q1: "Summary"
  sheet_name_sem: "Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert "code" in str(exc.value.key)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_06_pwid_without_nsp(self):
        raw = """
code: "PWID"
name: "People Who Inject Drugs"
sheet_aliases_register: ["Register"]
sheet_aliases_kplhiv: ["KPLHIV"]
defined_package:
  require_nsp: false
reporting:
  include_nsp_block: true
  sheet_name_q1: "PWID_Summary"
  sheet_name_sem: "PWID_Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert "BR-001" in str(exc.value)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_07_fsw_with_nsp(self):
        raw = """
code: "FSW"
name: "Female Sex Workers"
sheet_aliases_register: ["Register"]
sheet_aliases_kplhiv: ["KPLHIV"]
defined_package:
  require_nsp: true
reporting:
  include_nsp_block: false
  sheet_name_q1: "Summary"
  sheet_name_sem: "Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert "BR-001" in str(exc.value)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_08_empty_sheet_aliases(self):
        raw = """
code: "MSM"
name: "Men who have Sex with Men"
sheet_aliases_register: []
sheet_aliases_kplhiv: ["KPLHIV"]
defined_package:
  require_nsp: false
reporting:
  include_nsp_block: false
  sheet_name_q1: "Summary"
  sheet_name_sem: "Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert "sheet_aliases_register" in str(exc.value.key)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_09_invalid_header_skiprows_range(self):
        raw = """
code: "TG"
name: "Transgender"
sheet_aliases_register: ["Register"]
sheet_aliases_kplhiv: ["KPLHIV"]
header_skiprows: 99
defined_package:
  require_nsp: false
reporting:
  include_nsp_block: false
  sheet_name_q1: "Summary"
  sheet_name_sem: "Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert "header_skiprows" in str(exc.value.key)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_10_invalid_settings_max_upload(self):
        raw = """
app_name: "DATAFLOW"
max_upload_size_mb: -5
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_settings_config(p)
            assert "max_upload_size_mb" in str(exc.value.key)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()

    def test_neg_11_pwid_reporting_missing_nsp_block(self):
        raw = """
code: "PWID"
name: "People Who Inject Drugs"
sheet_aliases_register: ["Register"]
sheet_aliases_kplhiv: ["KPLHIV"]
defined_package:
  require_nsp: true
reporting:
  include_nsp_block: false
  sheet_name_q1: "PWID_Summary"
  sheet_name_sem: "PWID_Summary"
"""
        p = self._write_tmp(raw)
        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_population_config(p)
            assert "BR-001" in str(exc.value)
            assert str(p) in str(exc.value)
        finally:
            p.unlink()
