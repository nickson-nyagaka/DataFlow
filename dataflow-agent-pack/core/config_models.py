"""Typed configuration models and YAML validation for DATAFLOW using Pydantic v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from core.exceptions import ConfigValidationError


class DefinedPackageConfig(BaseModel):
    """Configuration for Defined Package pathway requirements."""

    require_nsp: bool = Field(
        ...,
        description="Whether Needle & Syringe Programme is mandatory for Defined Package (PWID only).",
    )
    require_hts: bool = True
    require_sti: bool = True
    require_tb: bool = True
    require_condoms: bool = True
    require_he_rrc: bool = True


class ReportingSpecConfig(BaseModel):
    """Reporting export specifications for a population."""

    include_nsp_block: bool = Field(
        ..., description="Whether to include the NSP block in Excel summary outputs."
    )
    sheet_name_q1: str = Field(..., min_length=1)
    sheet_name_sem: str = Field(..., min_length=1)


class PopulationConfig(BaseModel):
    """Complete specification for a Key Population cohort."""

    code: Literal["FSW", "MSM", "PWID", "TG", "VP"]
    name: str = Field(..., min_length=2)
    sheet_aliases_register: list[str] = Field(..., min_length=1)
    sheet_aliases_kplhiv: list[str] = Field(..., min_length=1)
    header_skiprows: int = Field(default=2, ge=0, le=10)
    defined_package: DefinedPackageConfig
    reporting: ReportingSpecConfig

    @model_validator(mode="after")
    def validate_pwid_nsp_consistency(self) -> PopulationConfig:
        """Enforces BR-001 / D-001: NSP is mandatory for PWID and prohibited for other populations."""
        if self.code == "PWID":
            if not self.defined_package.require_nsp:
                raise ValueError(
                    "PWID configuration must have defined_package.require_nsp = true per BR-001."
                )
            if not self.reporting.include_nsp_block:
                raise ValueError(
                    "PWID configuration must have reporting.include_nsp_block = true per BR-001."
                )
        else:
            if self.defined_package.require_nsp:
                raise ValueError(
                    f"{self.code} must not have defined_package.require_nsp = true (NSP is PWID-only per BR-001)."
                )
            if self.reporting.include_nsp_block:
                raise ValueError(
                    f"{self.code} must not have reporting.include_nsp_block = true (NSP is PWID-only per BR-001)."
                )
        return self


class PeriodConfig(BaseModel):
    """Configuration for reporting periods and explicit column mapping."""

    reporting_cycle: str = Field(..., min_length=2)
    q1_columns_count: int = Field(default=3, ge=1)
    q2_columns_count: int = Field(default=3, ge=1)
    q1_months: list[str] = Field(..., min_length=1)
    q2_months: list[str] = Field(..., min_length=1)


class VocabularyConfig(BaseModel):
    """Allowed values and canonical spelling mappings for categorical columns."""

    field: str = Field(..., min_length=1)
    canonical_values: list[str] = Field(..., min_length=1)
    case_variants: dict[str, str] = Field(default_factory=dict)


class SettingsConfig(BaseModel):
    """Global system execution settings."""

    app_name: str = "DATAFLOW"
    version: str = "0.1.0"
    max_upload_size_mb: int = Field(default=200, ge=10)
    block_on_critical_dqa: bool = True
    mask_identifiers_by_default: bool = False
    temp_dir: str = "runtime/temporary"
    export_dir: str = "runtime/exports"
    log_dir: str = "runtime/logs"


class CompatConfig(BaseModel):
    """Switches for reproducing legacy notebook behaviors during differential testing."""

    legacy_missing_age_below_15: bool = True
    legacy_impute_missing_sex_f: bool = True
    legacy_row_sum_flags: bool = True
    legacy_hts_sem_month_ge_7: bool = True
    legacy_comment_out_pwid_nsp: bool = True
    legacy_capitalize_vocabulary: bool = True


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Reads a YAML file safely from disk."""
    p = Path(path)
    if not p.exists():
        raise ConfigValidationError(f"Configuration file not found: {p}", file=str(p))
    try:
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise ConfigValidationError(
                    "Top-level YAML structure must be a mapping", file=str(p)
                )
            return data
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"YAML syntax error: {exc}", file=str(p)) from exc


def load_population_config(path: str | Path) -> PopulationConfig:
    """Loads and validates a population YAML against PopulationConfig."""
    p = Path(path)
    raw = load_yaml(p)
    try:
        return PopulationConfig.model_validate(raw)
    except ValidationError as err:
        first_error = err.errors()[0]
        loc = ".".join(str(x) for x in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation failed")
        raise ConfigValidationError(msg, file=str(p), key=loc) from err


def load_settings_config(path: str | Path) -> SettingsConfig:
    """Loads and validates settings.yaml."""
    p = Path(path)
    raw = load_yaml(p)
    try:
        return SettingsConfig.model_validate(raw)
    except ValidationError as err:
        first_error = err.errors()[0]
        loc = ".".join(str(x) for x in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation failed")
        raise ConfigValidationError(msg, file=str(p), key=loc) from err


def load_compat_config(path: str | Path) -> CompatConfig:
    """Loads and validates compat.yaml."""
    p = Path(path)
    raw = load_yaml(p)
    try:
        return CompatConfig.model_validate(raw)
    except ValidationError as err:
        first_error = err.errors()[0]
        loc = ".".join(str(x) for x in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation failed")
        raise ConfigValidationError(msg, file=str(p), key=loc) from err
