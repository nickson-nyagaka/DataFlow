"""DATAFLOW Configuration Page.

Implements Master Brief §11:
- Read-only viewer of effective YAML configurations, active compatibility switches,
  reporting templates, and validation rule registry.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.compat import CompatSwitches
from core.validation import RULE_DEFINITIONS
from ui.session import render_access_guard


def render_configuration() -> None:
    st.title("⚙️ System Configuration")
    st.caption(
        "Read-only inspection of effective configuration files, schema rules, and legacy compatibility switches."
    )

    if not render_access_guard("Configuration"):
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Population Configurations",
            "Excel Template Layouts",
            "Compatibility Switches",
            "DQA Rule Registry",
        ]
    )

    # Tab 1: Population Config
    with tab1:
        st.subheader("1. Population Schema Configuration")
        pop_choice = st.selectbox(
            "Select Population Schema",
            options=["FSW", "MSM", "PWID", "TG", "VP"],
            index=0,
        )
        pop_path = Path("config/populations") / f"{pop_choice.lower()}.yaml"
        if pop_path.exists():
            content = pop_path.read_text(encoding="utf-8")
            st.code(content, language="yaml")
        else:
            st.warning(f"Configuration file not found: `{pop_path}`")

    # Tab 2: Excel Templates
    with tab2:
        st.subheader("2. Excel Reporting Layout Templates")
        tmpl_path = Path("config/reporting/excel_templates.yaml")
        if tmpl_path.exists():
            tmpl_content = tmpl_path.read_text(encoding="utf-8")
            st.code(tmpl_content, language="yaml")
        else:
            st.warning(f"Template configuration file not found: `{tmpl_path}`")

    # Tab 3: Compatibility Switches
    with tab3:
        st.subheader("3. Legacy Compatibility Switches (Decisions D-020..D-028)")
        st.caption("Active bug-compatibility flags isolated from the legacy notebook oracle.")

        compat_path = Path("config/compat.yaml")
        if compat_path.exists():
            st.code(compat_path.read_text(encoding="utf-8"), language="yaml")
        else:
            # Fallback to CompatSwitches dataclass defaults
            switches = CompatSwitches()
            switch_data = [
                {"Switch": k, "Active Default": str(v)} for k, v in switches.__dict__.items()
            ]
            st.table(pd.DataFrame(switch_data))

    # Tab 4: DQA Rule Registry
    with tab4:
        st.subheader("4. DQA Validation Rules Registry")
        st.caption("The 19 clinical and demographic validation rules enforcing cohort integrity.")

        rule_data = [
            {
                "Rule ID": r.id,
                "Name": r.name,
                "Severity": r.severity,
                "Target Sheet": r.sheet_target,
                "Description": r.description,
            }
            for r in RULE_DEFINITIONS.values()
        ]
        st.dataframe(pd.DataFrame(rule_data), use_container_width=True, hide_index=True)


render_configuration()
