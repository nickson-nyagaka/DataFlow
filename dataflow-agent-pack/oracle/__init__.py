"""DATAFLOW Oracle: Frozen, bug-compatible Python transcription of legacy notebook logic.

Used exclusively for verification and differential testing against the refactored engine.
"""

from oracle.runner import run_oracle, run_oracle_from_dfs

__all__ = ["run_oracle", "run_oracle_from_dfs"]
