"""Pytest test suite for Phase 0 verification."""

from scripts.audit.verify_phase0_compliance import (
    check_indicator_dictionary,
    check_indicator_naming_consistency,
    check_known_issues,
    check_no_application_code,
    check_notebook_analysis,
    check_population_rules_and_excel_spec,
)


def test_notebook_analysis():
    check_notebook_analysis()


def test_indicator_dictionary():
    check_indicator_dictionary()


def test_known_issues():
    check_known_issues()


def test_population_rules_and_excel_spec():
    check_population_rules_and_excel_spec()


def test_indicator_naming_consistency():
    check_indicator_naming_consistency()


def test_no_application_code():
    check_no_application_code()
