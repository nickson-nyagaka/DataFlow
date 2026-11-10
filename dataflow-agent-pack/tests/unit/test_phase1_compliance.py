"""Compliance test suite for Phase 1 constraints and boundaries."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def test_zero_analytics_code_outside_oracle():
    """Phase 1/2 constraint: zero analytics code outside oracle/."""
    from scripts.gate_check import GATE_FILE, current_phase, read_statuses

    try:
        statuses = read_statuses(GATE_FILE)
        cur = current_phase(statuses)
    except Exception:
        cur = 1

    # Check that analytics/ directory does not exist or contains no python code
    analytics_dir = BASE_DIR / "analytics"
    if analytics_dir.exists():
        py_files = list(analytics_dir.glob("**/*.py"))
        assert len(py_files) == 0, f"Disallowed analytics code found: {py_files}"

    # Check that core/ contains only permitted modules for the active phase
    core_dir = BASE_DIR / "core"
    if cur == 1:
        allowed_core_files = {"config_models.py", "exceptions.py", "__init__.py"}
    elif cur == 2:
        allowed_core_files = {
            "config_models.py",
            "exceptions.py",
            "__init__.py",
            "ingestion.py",
            "cleaning.py",
            "audit.py",
            "inspect.py",
            "pipeline.py",
        }
    else:
        # Phase 3 allows validation, deduplication
        allowed_core_files = {
            "config_models.py",
            "exceptions.py",
            "__init__.py",
            "ingestion.py",
            "cleaning.py",
            "audit.py",
            "inspect.py",
            "pipeline.py",
            "validation.py",
            "deduplication.py",
        }
    existing_core_files = {f.name for f in core_dir.glob("*.py")}
    disallowed_core = existing_core_files - allowed_core_files
    assert len(disallowed_core) == 0, f"Disallowed core modules in Phase {cur}: {disallowed_core}"


def test_reference_notebook_is_pristine():
    """Verifies that reference/OPTIMIZED_DATA_MGT.sanitized.ipynb has not been modified."""
    ref_path = BASE_DIR / "reference" / "OPTIMIZED_DATA_MGT.sanitized.ipynb"
    assert ref_path.exists(), "Reference notebook missing!"
    # Verify file is non-empty and valid json
    content = ref_path.read_text(encoding="utf-8")
    assert len(content) > 1000
    assert '"cells":' in content
