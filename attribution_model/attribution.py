"""Monthly and horizon factor attribution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from attribution_model.model import ModelResult


@dataclass(frozen=True)
class AttributionResult:
    monthly_factor_contributions: pd.DataFrame
    monthly_block_contributions: pd.DataFrame
    horizon_summary: pd.DataFrame
    factor_horizon_detail: pd.DataFrame
    cumulative_actual_fitted: pd.DataFrame
    reconciliation_warnings: list[dict[str, Any]]


def _carino_scale(y: pd.Series) -> pd.Series:
    total = float(np.prod(1.0 + y) - 1.0)
    denominator = np.log1p(total) / total if abs(total) > 1e-12 else 1.0
    monthly = y.apply(lambda value: np.log1p(value) / value if abs(value) > 1e-12 else 1.0)
    return monthly / denominator


def _horizon_months(total_rows: int, requested: int) -> tuple[int, bool]:
    if total_rows >= requested:
        return requested, False
    return total_rows, True


def compute_attribution(
    factor_data: pd.DataFrame,
    model: ModelResult,
    config: dict[str, Any],
) -> AttributionResult:
    """Compute monthly, cumulative, and horizon attribution."""

    indexed = factor_data.set_index("Date")
    monthly = pd.DataFrame(index=indexed.index)
    for factor in model.factor_columns:
        monthly[factor] = indexed[factor] * model.final_betas.get(factor, 0.0)
    monthly["Alpha"] = model.alpha_monthly
    monthly["Specific"] = model.residuals.reindex(monthly.index)
    monthly["Actual"] = indexed["Fund_Rel"]
    monthly["Fitted"] = model.fitted.reindex(monthly.index)

    block_monthly = pd.DataFrame(index=monthly.index)
    for block in ["Market", "Style", "Industry", "Country"]:
        members = [factor for factor in model.factor_columns if model.factor_blocks.get(factor) == block]
        block_monthly[block] = monthly[members].sum(axis=1) if members else 0.0
    block_monthly["Alpha"] = monthly["Alpha"]
    block_monthly["Specific"] = monthly["Specific"]
    block_monthly["Actual"] = monthly["Actual"]
    block_monthly["Fitted"] = monthly["Fitted"]

    horizons = config.get("horizons", [12, 36, 60])
    tolerance = float(config.get("thresholds", {}).get("reconciliation_tol_bps", 1.0)) / 10000.0
    summary_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    component_columns = ["Market", "Style", "Industry", "Country", "Alpha", "Specific"]
    for requested in horizons:
        months, partial = _horizon_months(len(block_monthly), int(requested))
        window = block_monthly.iloc[-months:]
        y = window["Actual"]
        total = float(np.prod(1.0 + y) - 1.0)
        scale = _carino_scale(y)
        component_values = {
            component: float((window[component] * scale).sum()) for component in component_columns
        }
        arithmetic_values = {component: float(window[component].sum()) for component in component_columns}
        gap = float(sum(component_values.values()) - total)
        if abs(gap) > tolerance:
            warnings.append({"horizon": requested, "gap": gap, "tolerance": tolerance})
        for component in component_columns:
            summary_rows.append(
                {
                    "horizon_months": requested,
                    "used_months": months,
                    "partial": partial,
                    "component": component,
                    "geometric_contribution": component_values[component],
                    "arithmetic_contribution": arithmetic_values[component],
                    "total_relative_return": total,
                    "reconciliation_gap": gap,
                }
            )
        for factor in model.factor_columns:
            detail_rows.append(
                {
                    "horizon_months": requested,
                    "used_months": months,
                    "partial": partial,
                    "block": model.factor_blocks[factor],
                    "factor": factor,
                    "geometric_contribution": float((monthly.iloc[-months:][factor] * scale).sum()),
                    "arithmetic_contribution": float(monthly.iloc[-months:][factor].sum()),
                }
            )

    cumulative = pd.DataFrame(index=monthly.index)
    cumulative["Actual"] = (1.0 + monthly["Actual"]).cumprod() - 1.0
    cumulative["Fitted"] = (1.0 + monthly["Fitted"]).cumprod() - 1.0
    cumulative = cumulative.reset_index()

    return AttributionResult(
        monthly_factor_contributions=monthly.reset_index(),
        monthly_block_contributions=block_monthly.reset_index(),
        horizon_summary=pd.DataFrame(summary_rows),
        factor_horizon_detail=pd.DataFrame(detail_rows),
        cumulative_actual_fitted=cumulative,
        reconciliation_warnings=warnings,
    )

