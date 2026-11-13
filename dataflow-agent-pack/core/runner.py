"""DATAFLOW Pipeline Execution Engine and Run Metadata Tracker.

Orchestrates all pipeline stages: Ingestion -> Cleaning -> DQA -> Analytics -> Reports.
Calculates per-stage timings, pre-computes presentation analytics for the UI (zero indicator
logic in ui/), and writes run metadata to runtime/run_metadata.json.
Supports SHA-256 caching keyed by input file hash and active config hash.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from analytics.demographics import compute_kpi_demographic_summary
from analytics.display_summary import compute_display_analytics
from analytics.engine import run_analytics
from analytics.kplhiv import compute_kplhiv_summary, process_kplhiv_frame
from core.cleaning import clean_kplhiv_frame, clean_register_frame
from core.config_models import load_population_config
from core.ingestion import ingest_workbook
from core.progress_manager import ProgressManager
from core.validation import RULE_DEFINITIONS, DQAResults, run_dqa
from reporting.package_builder import build_export_summary, build_reporting_package

RUN_METADATA_PATH = Path("runtime/run_metadata.json")
_PIPELINE_CACHE: dict[tuple[str, str, str, str], PipelineResult] = {}


@dataclass
class PipelineResult:
    """Complete result bundle produced by the pipeline runner."""

    input_file_name: str
    input_file_hash: str
    config_hash: str
    population: str
    period_mode: str
    cleaned_register: pd.DataFrame
    cleaned_kplhiv: pd.DataFrame
    dqa_results: DQAResults
    summary_df: pd.DataFrame
    kplhiv_summary_df: pd.DataFrame
    package_paths: dict[str, Path]
    display_analytics: dict[str, Any]
    stage_timings: dict[str, float]
    total_cohort: int
    active_kplhiv: int
    total_dqa_exceptions: int
    critical_dqa_count: int
    major_dqa_count: int
    minor_dqa_count: int
    duration_seconds: float
    timestamp: str
    cached: bool = False
    progress_snapshot: dict[str, Any] = field(default_factory=dict)


def compute_file_hash(source: bytes | Path | str) -> str:
    """Calculates SHA-256 hash of a file or byte stream."""
    sha = hashlib.sha256()
    if isinstance(source, bytes):
        sha.update(source)
    else:
        path = Path(source)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
    return sha.hexdigest()


def compute_config_hash(
    population: str, period_mode: str, config_dir: str = "config/populations"
) -> str:
    """Calculates SHA-256 hash of active configuration files."""
    sha = hashlib.sha256()
    sha.update(population.encode("utf-8"))
    sha.update(period_mode.encode("utf-8"))

    pop_file = Path(config_dir) / f"{population.lower()}.yaml"
    if pop_file.exists():
        sha.update(pop_file.read_bytes())

    tmpl_file = Path("config/reporting/excel_templates.yaml")
    if tmpl_file.exists():
        sha.update(tmpl_file.read_bytes())

    return sha.hexdigest()[:16]


def get_cached_result(
    file_hash: str,
    config_hash: str,
    population: str,
    period_mode: str,
) -> PipelineResult | None:
    """Returns cached pipeline result if available, else None."""
    key = (file_hash, config_hash, population, period_mode)
    res = _PIPELINE_CACHE.get(key)
    if res:
        # Return a copy marked cached
        res.cached = True
    return res


def clear_pipeline_cache() -> None:
    """Wipes the in-memory pipeline run cache."""
    _PIPELINE_CACHE.clear()


def run_full_pipeline(
    file_source: Path | str | bytes,
    file_name: str,
    population: str = "FSW",
    period_mode: str = "SEM",
    config_dir: str = "config/populations",
    mask_identifiers: bool = False,
    force_rerun: bool = False,
    provisional_indicators: list[str] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> PipelineResult:
    """
    Executes the complete DATAFLOW pipeline across all stages with per-stage timings.
    Pre-computes presentation analytics for the UI layer (zero logic in UI).
    Writes runtime/run_metadata.json.
    """
    start_total = time.perf_counter()
    stage_timings: dict[str, float] = {}
    pm = ProgressManager(callback=progress_callback)

    # 1. Compute file hash and config hash
    file_hash = compute_file_hash(file_source)
    config_hash = compute_config_hash(population, period_mode, config_dir=config_dir)

    if not force_rerun:
        cached = get_cached_result(file_hash, config_hash, population, period_mode)
        if cached is not None:
            for s_id in ["ingestion", "cleaning", "dqa", "analytics", "reporting"]:
                pm.complete_stage(s_id, "Completed (Retrieved from cache)")
            cached.progress_snapshot = pm.snapshot()
            return cached

    # Save bytes to temporary file if bytes provided
    temp_file: Path | None = None
    if isinstance(file_source, bytes):
        temp_dir = Path("runtime/temporary")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"upload_{file_hash[:10]}_{file_name}"
        temp_file.write_bytes(file_source)
        work_path = temp_file
    else:
        work_path = Path(file_source)

    try:
        # Stage 1: Ingestion
        pm.start_stage("ingestion", f"Ingesting {population} register and KPLHIV worksheets...")
        t0 = time.perf_counter()
        pop_config = load_population_config(population, config_dir=config_dir)
        reg_raw, kp_raw, audit = ingest_workbook(work_path, pop_config)
        stage_timings["ingestion"] = round(time.perf_counter() - t0, 3)
        pm.complete_stage(
            "ingestion",
            f"Ingested {len(reg_raw):,} register records & {len(kp_raw):,} KPLHIV records",
            metrics={
                "register_rows": len(reg_raw),
                "kplhiv_rows": len(kp_raw),
                "duration_seconds": stage_timings["ingestion"],
            },
        )

        # Stage 2: Cleaning
        pm.start_stage("cleaning", "Applying vectorized cleaning and missing geography standardization...")
        t0 = time.perf_counter()
        reg_clean = clean_register_frame(reg_raw)
        pm.update_progress("cleaning", 50.0, "Cleaning KPLHIV records...", completed_op="Register cleaning completed")
        kp_clean = clean_kplhiv_frame(kp_raw) if not kp_raw.empty else kp_raw
        stage_timings["cleaning"] = round(time.perf_counter() - t0, 3)
        pm.complete_stage(
            "cleaning",
            f"Standardized {len(reg_clean):,} records with normalized geography",
            metrics={"cleaned_rows": len(reg_clean), "duration_seconds": stage_timings["cleaning"]},
        )

        # Stage 3: Data Quality Assurance
        rule_count = len(RULE_DEFINITIONS)
        pm.start_stage("dqa", f"Evaluating {rule_count} DQA rules across demographic and clinical fields...")
        t0 = time.perf_counter()
        dqa_results = run_dqa(
            reg_clean,
            kp_clean,
            population=population,
            block_on_critical=False,
        )
        stage_timings["dqa"] = round(time.perf_counter() - t0, 3)
        crit_n = dqa_results.severity_counts.get("Critical", 0)
        pm.complete_stage(
            "dqa",
            f"Evaluated {rule_count} rules. Found {dqa_results.total_exceptions:,} exceptions ({crit_n} Critical)",
            metrics={
                "rules_total": rule_count,
                "total_exceptions": dqa_results.total_exceptions,
                "critical_count": crit_n,
                "duration_seconds": stage_timings["dqa"],
            },
        )

        # Stage 4: Analytical Calculations
        pm.start_stage("analytics", f"Calculating cascade indicators and service metrics for {population}...")
        t0 = time.perf_counter()
        analytics_dict = run_analytics(reg_clean, kp_clean, population=population)
        reg_analyzed = analytics_dict.get("cleaned_register", reg_clean)
        kp_analyzed = analytics_dict.get("cleaned_kplhiv", kp_clean)

        # KPLHIV processing & summary
        if not kp_clean.empty:
            kp_processed = process_kplhiv_frame(kp_clean)
            kp_summary_df = compute_kplhiv_summary(kp_processed)
            active_kplhiv = len(kp_processed)
        else:
            kp_summary_df = pd.DataFrame()
            active_kplhiv = 0

        pm.update_progress("analytics", 70.0, "Compiling summary tables and age/sex disaggregations...")
        # Build standardized summary table with (MISSING) retention
        summary_df = build_export_summary(
            cleaned_register=reg_analyzed,
            cleaned_kplhiv=kp_analyzed,
            population=population,
            period_mode=period_mode,
        )
        # Compute KPI age x sex disaggregation summary
        kpi_summary_df = compute_kpi_demographic_summary(
            reg_analyzed,
            population=population,
            period_mode=period_mode,
        )
        stage_timings["analytics"] = round(time.perf_counter() - t0, 3)
        pm.complete_stage(
            "analytics",
            f"Calculated 48 indicators across {len(summary_df):,} geographic groupings",
            metrics={"summary_rows": len(summary_df), "duration_seconds": stage_timings["analytics"]},
        )

        # Stage 5: Reporting Package Generation
        pm.start_stage("reporting", "Assembling Master Multi-Tab Excel Workbook and Modular ZIP Package...")
        t0 = time.perf_counter()
        package_paths = build_reporting_package(
            cleaned_register=reg_analyzed,
            cleaned_kplhiv=kp_analyzed,
            population=population,
            period_mode=period_mode,
            dqa_exceptions_df=dqa_results.exceptions_df,
            input_file_hash=file_hash,
            config_hash=config_hash,
            mask_identifiers=mask_identifiers,
            provisional_indicators=provisional_indicators,
        )
        stage_timings["reporting"] = round(time.perf_counter() - t0, 3)
        pm.complete_stage(
            "reporting",
            "Master Excel Workbook and Modular ZIP Package successfully assembled",
            metrics={"package_count": len(package_paths), "duration_seconds": stage_timings["reporting"]},
        )

        total_duration = round(time.perf_counter() - start_total, 3)

        # Pre-compute Presentation Analytics (ZERO formulas in ui/)
        total_cohort = len(reg_clean)
        crit_count = dqa_results.severity_counts.get("Critical", 0)
        major_count = dqa_results.severity_counts.get("Major", 0)
        minor_count = dqa_results.severity_counts.get("Minor", 0)

        display_analytics = compute_display_analytics(
            summary_df=summary_df,
            reg_analyzed=reg_analyzed,
            kp_analyzed=kp_analyzed,
            population=population,
            period_mode=period_mode,
            total_cohort=total_cohort,
            active_kplhiv=active_kplhiv,
            kpi_summary_df=kpi_summary_df,
        )

        ts = datetime.now(UTC).isoformat()
        result = PipelineResult(
            input_file_name=file_name,
            input_file_hash=file_hash,
            config_hash=config_hash,
            population=population,
            period_mode=period_mode,
            cleaned_register=reg_analyzed,
            cleaned_kplhiv=kp_clean,
            dqa_results=dqa_results,
            summary_df=summary_df,
            kplhiv_summary_df=kp_summary_df,
            package_paths=package_paths,
            display_analytics=display_analytics,
            stage_timings=stage_timings,
            total_cohort=total_cohort,
            active_kplhiv=active_kplhiv,
            total_dqa_exceptions=dqa_results.total_exceptions,
            critical_dqa_count=crit_count,
            major_dqa_count=major_count,
            minor_dqa_count=minor_count,
            duration_seconds=total_duration,
            timestamp=ts,
            cached=False,
            progress_snapshot=pm.snapshot(),
        )

        # Cache result
        cache_key = (file_hash, config_hash, population, period_mode)
        _PIPELINE_CACHE[cache_key] = result

        # Write latest run metadata (JSON in runtime/, no identifiers)
        write_run_metadata(result)

        return result

    except Exception as exc:
        active_stage = "ingestion"
        if "ingestion" in stage_timings:
            active_stage = "cleaning"
        if "cleaning" in stage_timings:
            active_stage = "dqa"
        if "dqa" in stage_timings:
            active_stage = "analytics"
        if "analytics" in stage_timings:
            active_stage = "reporting"
        pm.fail_stage(active_stage, str(exc))
        raise exc

    finally:
        # Clean up temporary uploaded file if created
        if temp_file and temp_file.exists():
            temp_file.unlink(missing_ok=True)


def write_run_metadata(result: PipelineResult, path: Path | str = RUN_METADATA_PATH) -> None:
    """Writes run metadata JSON containing aggregate statistics and display cascades (zero client identifiers)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    serializable_disp = {}
    if result.display_analytics:
        for k, v in result.display_analytics.items():
            if k != "kpi_summary_df" and not isinstance(v, pd.DataFrame):
                serializable_disp[k] = v

    meta = {
        "timestamp": result.timestamp,
        "input_file_name": result.input_file_name,
        "input_file_hash": result.input_file_hash,
        "config_hash": result.config_hash,
        "population": result.population,
        "period_mode": result.period_mode,
        "total_cohort": result.total_cohort,
        "active_kplhiv": result.active_kplhiv,
        "total_dqa_exceptions": result.total_dqa_exceptions,
        "critical_dqa_count": result.critical_dqa_count,
        "major_dqa_count": result.major_dqa_count,
        "minor_dqa_count": result.minor_dqa_count,
        "duration_seconds": result.duration_seconds,
        "stage_timings": result.stage_timings,
        "display_analytics": serializable_disp,
        "status": "SUCCESS",
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def read_latest_run_metadata(path: Path | str = RUN_METADATA_PATH) -> dict[str, Any] | None:
    """Reads the latest run metadata JSON if available, else None."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
