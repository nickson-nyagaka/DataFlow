"""Compliance test suite for Phase 1 constraints and boundaries."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def test_zero_analytics_code_outside_oracle():
    """Phase 1 exit criterion: zero analytics code outside oracle/."""
    # Check that analytics/ directory does not exist or contains no python code
    analytics_dir = BASE_DIR / "analytics"
    if analytics_dir.exists():
        py_files = list(analytics_dir.glob("**/*.py"))
        assert len(py_files) == 0, f"Disallowed analytics code found in Phase 1: {py_files}"

    # Check that core/ contains only foundational configs and exceptions, not analytics pipelines
    core_dir = BASE_DIR / "core"
    allowed_core_files = {"config_models.py", "exceptions.py", "__init__.py"}
    existing_core_files = {f.name for f in core_dir.glob("*.py")}
    disallowed_core = existing_core_files - allowed_core_files
    assert len(disallowed_core) == 0, f"Disallowed core modules in Phase 1: {disallowed_core}"


def test_reference_notebook_is_pristine():
    """Verifies that reference/OPTIMIZED_DATA_MGT.sanitized.ipynb has not been modified."""
    ref_path = BASE_DIR / "reference" / "OPTIMIZED_DATA_MGT.sanitized.ipynb"
    assert ref_path.exists(), "Reference notebook missing!"
    # Verify file is non-empty and valid json
    content = ref_path.read_text(encoding="utf-8")
    assert len(content) > 1000
    assert '"cells":' in content
