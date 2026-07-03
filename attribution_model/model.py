"""Staged return-based regression engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import Lasso, Ridge
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class StageResult:
    name: str
    factors: list[str]
    betas: dict[str, float]
    t_stats: dict[str, float]
    p_values: dict[str, float]
    r_squared: float
    adj_r_squared: float
    incremental_r_squared: float
    residual_vol_annualized: float


@dataclass(frozen=True)
class ModelResult:
    """All model outputs needed by attribution, risk, and diagnostics."""

    estimator: str
    stages: list[StageResult]
    final_betas: dict[str, float]
    alpha_monthly: float
    alpha_annualized: float
    residuals: pd.Series
    fitted: pd.Series
    factor_columns: list[str]
    factor_blocks: dict[str, str]
    vif: pd.DataFrame
    rolling_betas: pd.DataFrame
    stability_flags: pd.DataFrame
    tracking_error_explained: float
    annualized_tracking_error: float
    annualized_residual_vol: float


def _stage_factor_lists(factor_columns: list[str], factor_blocks: dict[str, str]) -> list[tuple[str, list[str]]]:
    market = [factor for factor in factor_columns if factor_blocks[factor] == "Market"]
    style = [factor for factor in factor_columns if factor_blocks[factor] == "Style"]
    industry = [factor for factor in factor_columns if factor_blocks[factor] == "Industry"]
    country = [factor for factor in factor_columns if factor_blocks[factor] == "Country"]
    return [
        ("Stage 1 Market", market),
        ("Stage 2 Style", market + style),
        ("Stage 3 Industry", market + style + industry),
        ("Stage 4 Country", market + style + industry + country),
    ]


def _fit_ols(y: pd.Series, x: pd.DataFrame, nw_lags: int) -> Any:
    design = sm.add_constant(x, has_constant="add")
    return sm.OLS(y, design).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags})


def _stage_result(name: str, factors: list[str], result: Any, previous_r2: float) -> StageResult:
    betas = {factor: float(result.params.get(factor, 0.0)) for factor in factors}
    t_stats = {factor: float(result.tvalues.get(factor, np.nan)) for factor in factors}
    p_values = {factor: float(result.pvalues.get(factor, np.nan)) for factor in factors}
    residual_vol = float(result.resid.std(ddof=1) * np.sqrt(12))
    return StageResult(
        name=name,
        factors=factors,
        betas=betas,
        t_stats=t_stats,
        p_values=p_values,
        r_squared=float(result.rsquared),
        adj_r_squared=float(result.rsquared_adj),
        incremental_r_squared=float(result.rsquared - previous_r2),
        residual_vol_annualized=residual_vol,
    )


def _compute_vif(x: pd.DataFrame, threshold: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in x.columns:
        others = [other for other in x.columns if other != column]
        if not others:
            vif = 1.0
        else:
            result = sm.OLS(x[column], sm.add_constant(x[others], has_constant="add")).fit()
            vif = float(1.0 / max(1.0 - result.rsquared, 1e-12))
        rows.append({"factor": column, "vif": vif, "flag": bool(vif > threshold)})
    return pd.DataFrame(rows)


def _regularized_fit(
    y: pd.Series,
    x: pd.DataFrame,
    method: str,
    alpha: float,
) -> tuple[float, dict[str, float], pd.Series, pd.Series]:
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    if method == "ridge":
        estimator = Ridge(alpha=alpha)
    elif method == "lasso":
        estimator = Lasso(alpha=alpha, max_iter=10000)
    else:
        raise ValueError(f"Unsupported regularisation method: {method}")
    estimator.fit(x_scaled, y)
    betas = estimator.coef_ / scaler.scale_
    intercept = float(estimator.intercept_ - np.sum(estimator.coef_ * scaler.mean_ / scaler.scale_))
    beta_map = {column: float(beta) for column, beta in zip(x.columns, betas)}
    fitted = pd.Series(intercept + np.dot(x, betas), index=y.index, name="Fitted")
    residuals = pd.Series(y - fitted, index=y.index, name="Residual")
    return intercept, beta_map, fitted, residuals


def _rolling_betas(y: pd.Series, x: pd.DataFrame, window: int = 36) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if len(y) < window or x.empty:
        return pd.DataFrame()
    for end in range(window, len(y) + 1):
        y_slice = y.iloc[end - window : end]
        x_slice = x.iloc[end - window : end]
        result = sm.OLS(y_slice, sm.add_constant(x_slice, has_constant="add")).fit()
        row = {"Date": y.index[end - 1]}
        for factor in x.columns:
            row[factor] = float(result.params.get(factor, np.nan))
        rows.append(row)
    return pd.DataFrame(rows)


def fit_model(
    factor_data: pd.DataFrame,
    factor_blocks: dict[str, str],
    config: dict[str, Any],
) -> ModelResult:
    """Fit staged OLS and optional final regularized model."""

    factor_columns = list(factor_blocks)
    indexed = factor_data.set_index("Date")
    y = indexed["Fund_Rel"]
    x = indexed[factor_columns]
    nw_lags = int(config.get("regression", {}).get("nw_lags", 3))
    previous_r2 = 0.0
    stages: list[StageResult] = []
    final_ols = None
    final_stage_factors: list[str] = []
    for stage_name, factors in _stage_factor_lists(factor_columns, factor_blocks):
        design = x[factors] if factors else pd.DataFrame(index=x.index)
        result = _fit_ols(y, design, nw_lags)
        stages.append(_stage_result(stage_name, factors, result, previous_r2))
        previous_r2 = float(result.rsquared)
        final_ols = result
        final_stage_factors = factors

    regularisation = config.get("regression", {}).get("regularisation", "none")
    if regularisation in {"ridge", "lasso"} and final_stage_factors:
        alpha, betas, fitted, residuals = _regularized_fit(
            y,
            x[final_stage_factors],
            regularisation,
            float(config.get("regression", {}).get("ridge_alpha", 1.0)),
        )
        estimator = regularisation
    else:
        if final_ols is None:
            raise ValueError("No fitted model was produced")
        estimator = "ols_hac"
        alpha = float(final_ols.params.get("const", 0.0))
        betas = {factor: float(final_ols.params.get(factor, 0.0)) for factor in final_stage_factors}
        fitted = pd.Series(final_ols.fittedvalues, index=y.index, name="Fitted")
        residuals = pd.Series(final_ols.resid, index=y.index, name="Residual")

    explained = 1.0 - float(np.var(residuals, ddof=1) / max(np.var(y, ddof=1), 1e-12))
    realized_te = float(y.std(ddof=1) * np.sqrt(12))
    residual_vol = float(residuals.std(ddof=1) * np.sqrt(12))
    rolling = _rolling_betas(y, x[final_stage_factors])
    stability_rows: list[dict[str, Any]] = []
    if not rolling.empty:
        se_by_factor = {
            factor: float(final_ols.bse.get(factor, np.nan)) if final_ols is not None else np.nan
            for factor in final_stage_factors
        }
        for factor in final_stage_factors:
            series = rolling[factor].dropna()
            if series.empty:
                continue
            full_beta = betas.get(factor, 0.0)
            sign_change = bool((series * full_beta < 0).any())
            drift = float((series - full_beta).abs().max())
            se = se_by_factor.get(factor, np.nan)
            stability_rows.append(
                {
                    "factor": factor,
                    "sign_change": sign_change,
                    "max_abs_drift": drift,
                    "two_se_drift": bool(pd.notna(se) and drift > 2.0 * se),
                }
            )

    return ModelResult(
        estimator=estimator,
        stages=stages,
        final_betas=betas,
        alpha_monthly=alpha,
        alpha_annualized=float((1.0 + alpha) ** 12 - 1.0),
        residuals=residuals,
        fitted=fitted,
        factor_columns=final_stage_factors,
        factor_blocks=factor_blocks,
        vif=_compute_vif(x[final_stage_factors], config.get("thresholds", {}).get("vif_flag", 5.0))
        if final_stage_factors
        else pd.DataFrame(),
        rolling_betas=rolling,
        stability_flags=pd.DataFrame(stability_rows),
        tracking_error_explained=explained,
        annualized_tracking_error=realized_te,
        annualized_residual_vol=residual_vol,
    )

