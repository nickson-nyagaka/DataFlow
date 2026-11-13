"""Central Typology & Reporting Period Rules for DATAFLOW.

Governs population-specific demographic breakdowns, sex disaggregations,
and period-aware analytical aggregation and reporting per Master Brief.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Canonical in-memory fallback rules
TYPOLOGY_AGE_SEX_RULES: dict[str, dict[str, Any]] = {
    "FSW": {
        "sexes": ["F"],
        "age_groups": ["15-19", "20-24", "25+"],
        "include_total": True,
        "expected_sex": "F",
    },
    "MSM": {
        "sexes": ["M"],
        "age_groups": ["15-19", "20-24", "25+"],
        "include_total": True,
        "expected_sex": "M",
    },
    "PWID": {
        "sexes": ["M", "F"],
        "age_groups": ["15-19", "20-24", "25+"],
        "include_total": True,
        "expected_sex": None,
    },
    "TG": {
        "sexes": ["M", "F"],
        "age_groups": ["15-19", "20-24", "25+"],
        "include_total": True,
        "expected_sex": None,
    },
    "VP": {
        "sexes": ["M", "F"],
        "age_groups": ["15-19", "20-24", "25+"],
        "include_total": True,
        "expected_sex": None,
    },
}

PERIOD_RULES: dict[str, dict[str, Any]] = {
    "Q1": {
        "months": ["jul", "aug", "sep"],
        "description": "Quarter 1 (July - September)",
        "indicator_suffix": "_q1",
    },
    "Q2": {
        "months": ["oct", "nov", "dec"],
        "description": "Quarter 2 (October - December)",
        "indicator_suffix": "_q2",
    },
    "SEM": {
        "months": ["jul", "aug", "sep", "oct", "nov", "dec"],
        "description": "Semester (July - December)",
        "indicator_suffix": "_sem",
    },
}


def _load_typology_yaml() -> dict[str, Any]:
    p = Path(__file__).resolve().parent.parent / "config" / "reporting" / "typology_disaggregation.yaml"
    if p.is_file():
        try:
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data
        except Exception:
            return {}
    return {}


_YAML_CONFIG = _load_typology_yaml()
_LOADED_TYPOLOGIES: dict[str, dict[str, Any]] = _YAML_CONFIG.get("typologies", TYPOLOGY_AGE_SEX_RULES)
_LOADED_PERIODS: dict[str, dict[str, Any]] = _YAML_CONFIG.get("periods", PERIOD_RULES)


def get_typology_rule(population: str) -> dict[str, Any]:
    """Returns rule configuration dictionary for given population."""
    pop = population.strip().upper()
    if pop in _LOADED_TYPOLOGIES:
        return _LOADED_TYPOLOGIES[pop]
    if pop in TYPOLOGY_AGE_SEX_RULES:
        return TYPOLOGY_AGE_SEX_RULES[pop]
    # Default fallback for unmapped populations
    return {
        "sexes": ["M", "F"],
        "age_groups": ["15-19", "20-24", "25+"],
        "include_total": True,
        "expected_sex": None,
    }


def get_typology_sexes(population: str) -> list[str]:
    """Returns list of applicable sexes for the population (e.g. ['F'] for FSW, ['M'] for MSM)."""
    return list(get_typology_rule(population).get("sexes", ["M", "F"]))


def get_typology_age_groups(population: str) -> list[str]:
    """Returns standard age bands for the population."""
    return list(get_typology_rule(population).get("age_groups", ["15-19", "20-24", "25+"]))


def get_typology_age_sex_labels(population: str) -> list[str]:
    """Generates ordered age x sex combination labels for the given population.

    FSW: ['15-19_F', '20-24_F', '25+_F']
    MSM: ['15-19_M', '20-24_M', '25+_M']
    PWID/TG/VP: ['15-19_M', '15-19_F', '20-24_M', '20-24_F', '25+_M', '25+_F']
    """
    rule = get_typology_rule(population)
    sexes = rule.get("sexes", ["M", "F"])
    age_groups = rule.get("age_groups", ["15-19", "20-24", "25+"])

    labels: list[str] = []
    for ag in age_groups:
        for s in sexes:
            labels.append(f"{ag}_{s}")
    return labels


def get_typology_subheaders(population: str) -> list[str]:
    """Returns the indicator subheaders including 'Total' if configured."""
    labels = get_typology_age_sex_labels(population)
    rule = get_typology_rule(population)
    if rule.get("include_total", True):
        return labels + ["Total"]
    return labels


def get_typology_column_count(population: str) -> int:
    """Returns the total number of columns expected for the KPI summary table.

    Demographics: 3 columns (SR Name, Region, County)
    Indicators: 3 indicators (Defined Package, HTS, PrEP) * len(subheaders)
    FSW: 3 + 3 * 4 = 15 columns
    MSM: 3 + 3 * 4 = 15 columns
    PWID / TG / VP: 3 + 3 * 7 = 24 columns
    """
    sub_count = len(get_typology_subheaders(population))
    return 3 + 3 * sub_count


def get_kpi_indicators_for_period(period_mode: str) -> dict[str, str]:
    """Maps period-specific DataFrame columns to KPI indicator display names."""
    mode = period_mode.strip().upper()
    if mode in ["Q1", "Q2"]:
        sfx = f"_{mode.lower()}"
        return {
            f"definedpackage{sfx}": "DEFINED PACKAGE",
            f"hts{sfx}": "HTS",
            f"prep{sfx}": "PREP",
        }
    return {
        "definedpackage_sem": "DEFINED PACKAGE",
        "hts_sem_any": "HTS",
        "prep_sem": "PREP",
    }
