"""Build relative factor returns for the regression model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactorBuildResult:
    """Regression-ready factors and construction diagnostics."""

    factor_data: pd.DataFrame
    factor_blocks: dict[str, str]
    audit_table: pd.DataFrame
    correlation_matrix: pd.DataFrame
    correlation_flags: pd.DataFrame


def factor_column_name(block: str, name: str) -> str:
    return f"{block}_{name}".replace(" ", "_").replace("/", "_").replace("-", "_")


def _ann_vol(series: pd.Series) -> float:
    return float(series.std(ddof=1) * np.sqrt(12)) if series.count() > 1 else 0.0


def build_factors(raw_returns: pd.DataFrame, config: dict[str, Any]) -> FactorBuildResult:
    """Transform raw index returns into active factor returns."""

    date = raw_returns["Date"]
    fund = config["columns"]["fund"]
    benchmark = config["columns"]["benchmark"]
    output = pd.DataFrame(
        {
            "Date": date,
            "Fund_Rel": (1.0 + raw_returns[fund]) / (1.0 + raw_returns[benchmark]) - 1.0,
        }
    )
    factor_blocks: dict[str, str] = {}
    audit_rows: list[dict[str, Any]] = []

    market = config.get("market_factor")
    if market and market.get("index_column") and market["index_column"] != benchmark:
        output["MKT"] = raw_returns[market["index_column"]] - raw_returns[benchmark]
        factor_blocks["MKT"] = "Market"
        audit_rows.append(
            {
                "factor": "MKT",
                "block": "Market",
                "index_column": market["index_column"],
                "parent_column": benchmark,
                "first_usable_date": output.loc[output["MKT"].first_valid_index(), "Date"].strftime("%Y-%m-%d"),
                "n_obs": int(output["MKT"].count()),
                "mean": float(output["MKT"].mean()),
                "ann_vol": _ann_vol(output["MKT"]),
            }
        )

    for block, factors in config.get("factors", {}).items():
        block_label = block.title()
        for factor in factors:
            column = factor_column_name(block, factor["name"])
            output[column] = raw_returns[factor["index_column"]] - raw_returns[factor["parent_column"]]
            factor_blocks[column] = block_label
            first_valid = output[column].first_valid_index()
            audit_rows.append(
                {
                    "factor": column,
                    "block": block_label,
                    "index_column": factor["index_column"],
                    "parent_column": factor["parent_column"],
                    "first_usable_date": (
                        output.loc[first_valid, "Date"].strftime("%Y-%m-%d")
                        if first_valid is not None
                        else None
                    ),
                    "n_obs": int(output[column].count()),
                    "mean": float(output[column].mean()),
                    "ann_vol": _ann_vol(output[column]),
                }
            )

    factor_columns = list(factor_blocks)
    factor_data = output[["Date", "Fund_Rel", *factor_columns]].dropna().reset_index(drop=True)
    audit_table = pd.DataFrame(audit_rows)
    correlation_matrix = factor_data[factor_columns].corr() if factor_columns else pd.DataFrame()

    threshold = config.get("thresholds", {}).get("corr_flag", 0.75)
    flags: list[dict[str, Any]] = []
    for i, left in enumerate(factor_columns):
        for right in factor_columns[i + 1 :]:
            corr = correlation_matrix.loc[left, right]
            if pd.notna(corr) and abs(corr) > threshold:
                flags.append({"factor_1": left, "factor_2": right, "correlation": float(corr)})

    return FactorBuildResult(
        factor_data=factor_data,
        factor_blocks=factor_blocks,
        audit_table=audit_table,
        correlation_matrix=correlation_matrix,
        correlation_flags=pd.DataFrame(flags),
    )

