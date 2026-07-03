"""Tracking-error variance decomposition."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from attribution_model.model import ModelResult


@dataclass(frozen=True)
class RiskResult:
    block_table: pd.DataFrame
    factor_table: pd.DataFrame


def compute_risk_decomposition(factor_data: pd.DataFrame, model: ModelResult) -> RiskResult:
    """Decompose active variance into systematic factor blocks and specific risk."""

    if not model.factor_columns:
        return RiskResult(block_table=pd.DataFrame(), factor_table=pd.DataFrame())

    indexed = factor_data.set_index("Date")
    factors = indexed[model.factor_columns]
    beta = pd.Series(model.final_betas).reindex(model.factor_columns).fillna(0.0)
    sigma = factors.cov()
    sigma_beta = sigma.dot(beta)
    factor_var = beta * sigma_beta
    systematic_var = float(factor_var.sum())
    residual_var = float(model.residuals.var(ddof=1))
    total_var = max(systematic_var + residual_var, 1e-12)

    factor_rows = []
    for factor, contribution in factor_var.items():
        factor_rows.append(
            {
                "factor": factor,
                "block": model.factor_blocks[factor],
                "variance_contribution": float(contribution),
                "variance_share": float(contribution / total_var),
                "annualized_te_contribution": float(np.sqrt(max(contribution, 0.0) * 12.0)),
            }
        )
    factor_table = pd.DataFrame(factor_rows)

    block_rows = []
    for block in ["Market", "Style", "Industry", "Country"]:
        variance = float(factor_table.loc[factor_table["block"] == block, "variance_contribution"].sum())
        block_rows.append(
            {
                "block": block,
                "variance_share": variance / total_var,
                "annualized_te_contribution": float(np.sqrt(max(variance, 0.0) * 12.0)),
            }
        )
    block_rows.append(
        {
            "block": "Specific",
            "variance_share": residual_var / total_var,
            "annualized_te_contribution": float(np.sqrt(max(residual_var, 0.0) * 12.0)),
        }
    )
    return RiskResult(block_table=pd.DataFrame(block_rows), factor_table=factor_table)

