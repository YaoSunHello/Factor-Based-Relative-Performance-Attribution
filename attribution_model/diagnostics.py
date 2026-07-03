"""Governance and diagnostic outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from attribution_model.attribution import AttributionResult
from attribution_model.data_loader import DataQualityReport
from attribution_model.model import ModelResult


@dataclass(frozen=True)
class DiagnosticsResult:
    coefficient_table: pd.DataFrame
    stage_r2_table: pd.DataFrame
    correlation_matrix: pd.DataFrame
    correlation_flags: pd.DataFrame
    rolling_betas: pd.DataFrame
    stability_flags: pd.DataFrame
    residual_analysis: pd.DataFrame
    governance_summary: dict[str, Any]
    data_quality_report: DataQualityReport


def _stars(p_value: float) -> str:
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.1:
        return "*"
    return ""


def build_diagnostics(
    model: ModelResult,
    factor_data: pd.DataFrame,
    data_quality: DataQualityReport,
    attribution: AttributionResult,
    correlation_matrix: pd.DataFrame,
    correlation_flags: pd.DataFrame,
) -> DiagnosticsResult:
    """Assemble diagnostics as tidy tables for dashboard rendering."""

    final_stage = model.stages[-1]
    vif = model.vif.set_index("factor") if not model.vif.empty else pd.DataFrame()
    coefficient_rows = []
    for factor in model.factor_columns:
        p_value = final_stage.p_values.get(factor, float("nan"))
        coefficient_rows.append(
            {
                "factor": factor,
                "block": model.factor_blocks[factor],
                "beta": model.final_betas.get(factor, 0.0),
                "hac_t_stat": final_stage.t_stats.get(factor),
                "p_value": p_value,
                "significance": _stars(float(p_value)) if pd.notna(p_value) else "",
                "vif": float(vif.loc[factor, "vif"]) if not vif.empty and factor in vif.index else None,
                "flags": "VIF" if not vif.empty and factor in vif.index and bool(vif.loc[factor, "flag"]) else "",
            }
        )
    coefficient_table = pd.DataFrame(coefficient_rows)

    stage_r2_table = pd.DataFrame(
        [
            {
                "stage": stage.name,
                "r_squared": stage.r_squared,
                "adj_r_squared": stage.adj_r_squared,
                "incremental_r_squared": stage.incremental_r_squared,
                "residual_vol_annualized": stage.residual_vol_annualized,
            }
            for stage in model.stages
        ]
    )

    residuals = pd.DataFrame(
        {
            "Date": model.residuals.index,
            "actual": factor_data.set_index("Date")["Fund_Rel"].reindex(model.residuals.index),
            "fitted": model.fitted,
            "residual": model.residuals,
        }
    )
    residual_analysis = residuals.reindex(residuals["residual"].abs().sort_values(ascending=False).index).head(5)
    residual_analysis["label"] = "for qualitative review"

    active_flags: list[str] = []
    if data_quality.has_flags:
        active_flags.append("data_quality")
    if not correlation_flags.empty:
        active_flags.append("high_factor_correlation")
    if not model.vif.empty and model.vif["flag"].any():
        active_flags.append("high_vif")
    if attribution.reconciliation_warnings:
        active_flags.append("attribution_reconciliation")
    if not model.stability_flags.empty and (
        model.stability_flags["sign_change"].any() or model.stability_flags["two_se_drift"].any()
    ):
        active_flags.append("rolling_beta_stability")

    governance_summary = {
        "n_obs": int(len(factor_data)),
        "n_factors": int(len(model.factor_columns)),
        "parsimony_check": "pass" if len(model.factor_columns) <= 12 else "review",
        "estimator_used": model.estimator,
        "reconciliation_status": "warning" if attribution.reconciliation_warnings else "pass",
        "tracking_error_explained": model.tracking_error_explained,
        "active_flags": active_flags,
    }

    return DiagnosticsResult(
        coefficient_table=coefficient_table,
        stage_r2_table=stage_r2_table,
        correlation_matrix=correlation_matrix,
        correlation_flags=correlation_flags,
        rolling_betas=model.rolling_betas,
        stability_flags=model.stability_flags,
        residual_analysis=residual_analysis.reset_index(drop=True),
        governance_summary=governance_summary,
        data_quality_report=data_quality,
    )

