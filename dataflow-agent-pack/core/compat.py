"""Compatibility layer isolating legacy notebook defects and quirks.

Allows running in 100% bug-compatible legacy mode (for differential testing against oracle)
or modern corrected mode (where each defect is corrected one decision at a time).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CompatSwitches:
    """Typed switches corresponding to config/compat.yaml."""

    legacy_missing_age_below_15: bool = True
    legacy_impute_missing_sex_f: bool = True
    legacy_row_sum_flags: bool = True
    legacy_hts_sem_month_ge_7: bool = True
    legacy_comment_out_pwid_nsp: bool = True
    legacy_capitalize_vocabulary: bool = False
    legacy_lexicographic_column_sort: bool = True

    @classmethod
    def load(cls, config_path: str | Path = "config/compat.yaml") -> CompatSwitches:
        p = Path(config_path).resolve()
        if not p.exists():
            return cls()

        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(
            legacy_missing_age_below_15=data.get("legacy_missing_age_below_15", True),
            legacy_impute_missing_sex_f=data.get("legacy_impute_missing_sex_f", True),
            legacy_row_sum_flags=data.get("legacy_row_sum_flags", True),
            legacy_hts_sem_month_ge_7=data.get("legacy_hts_sem_month_ge_7", True),
            legacy_comment_out_pwid_nsp=data.get("legacy_comment_out_pwid_nsp", True),
            legacy_capitalize_vocabulary=data.get("legacy_capitalize_vocabulary", False),
            legacy_lexicographic_column_sort=data.get("legacy_lexicographic_column_sort", True),
        )

    def with_override(self, **kwargs: bool) -> CompatSwitches:
        """Returns a new CompatSwitches instance with specified switches overridden."""
        current = {
            "legacy_missing_age_below_15": self.legacy_missing_age_below_15,
            "legacy_impute_missing_sex_f": self.legacy_impute_missing_sex_f,
            "legacy_row_sum_flags": self.legacy_row_sum_flags,
            "legacy_hts_sem_month_ge_7": self.legacy_hts_sem_month_ge_7,
            "legacy_comment_out_pwid_nsp": self.legacy_comment_out_pwid_nsp,
            "legacy_capitalize_vocabulary": self.legacy_capitalize_vocabulary,
            "legacy_lexicographic_column_sort": self.legacy_lexicographic_column_sort,
        }
        current.update(kwargs)
        return CompatSwitches(**current)

    @classmethod
    def all_disabled(cls) -> CompatSwitches:
        """Returns instance with all legacy bug-compatibility switches disabled (modern mode)."""
        return cls(
            legacy_missing_age_below_15=False,
            legacy_impute_missing_sex_f=False,
            legacy_row_sum_flags=False,
            legacy_hts_sem_month_ge_7=False,
            legacy_comment_out_pwid_nsp=False,
            legacy_capitalize_vocabulary=False,
            legacy_lexicographic_column_sort=False,
        )

    @classmethod
    def all_enabled(cls) -> CompatSwitches:
        """Returns instance with all legacy switches enabled (bug-compatible legacy mode)."""
        return cls(
            legacy_missing_age_below_15=True,
            legacy_impute_missing_sex_f=True,
            legacy_row_sum_flags=True,
            legacy_hts_sem_month_ge_7=True,
            legacy_comment_out_pwid_nsp=True,
            legacy_capitalize_vocabulary=True,
            legacy_lexicographic_column_sort=True,
        )
