"""Self-contained HTML dashboard rendering."""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from attribution_model.attribution import AttributionResult
from attribution_model.diagnostics import DiagnosticsResult
from attribution_model.risk import RiskResult


def _table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if df is None or df.empty:
        return "<p class='muted'>No rows.</p>"
    shown = df.head(max_rows) if max_rows else df
    return shown.to_html(index=False, classes="data-table", border=0, float_format=lambda value: f"{value:.4f}")


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _plot_divs(attribution: AttributionResult, risk: RiskResult) -> str:
    import plotly.graph_objects as go
    import plotly.io as pio

    summary = attribution.horizon_summary
    latest_horizon = int(summary["horizon_months"].max())
    latest = summary[summary["horizon_months"] == latest_horizon]
    bar = go.Figure(
        data=[
            go.Bar(
                x=latest["component"],
                y=latest["geometric_contribution"],
                marker_color="#2f6f73",
            )
        ]
    )
    bar.update_layout(title=f"{latest_horizon}m Block Attribution", template="plotly_white")

    cumulative = attribution.cumulative_actual_fitted
    line = go.Figure()
    line.add_trace(go.Scatter(x=cumulative["Date"], y=cumulative["Actual"], name="Actual relative"))
    line.add_trace(go.Scatter(x=cumulative["Date"], y=cumulative["Fitted"], name="Fitted relative"))
    line.update_layout(title="Cumulative Actual vs Fitted Relative Return", template="plotly_white")

    risk_fig = go.Figure(
        data=[
            go.Bar(
                x=risk.block_table["block"],
                y=risk.block_table["variance_share"],
                marker_color="#725c9a",
            )
        ]
    )
    risk_fig.update_layout(title="Tracking Error Variance Share", template="plotly_white")
    return "\n".join(
        [
            pio.to_html(bar, include_plotlyjs="inline", full_html=False),
            pio.to_html(line, include_plotlyjs=False, full_html=False),
            pio.to_html(risk_fig, include_plotlyjs=False, full_html=False),
        ]
    )


def render_dashboard(
    output_path: str | Path,
    config: dict[str, Any],
    attribution: AttributionResult,
    risk: RiskResult,
    diagnostics: DiagnosticsResult,
    factor_audit: pd.DataFrame,
) -> Path:
    """Render a single self-contained offline HTML report."""

    output = Path(output_path)
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
    fund = config["columns"]["fund"]
    benchmark = config["columns"]["benchmark"]
    summary = attribution.horizon_summary
    five_year = summary[summary["horizon_months"] == max(config.get("horizons", [60]))]
    total = float(five_year["total_relative_return"].iloc[0]) if not five_year.empty else 0.0
    component_map = {
        row["component"]: row["geometric_contribution"]
        for _, row in five_year.iterrows()
    }
    headline = (
        f"Over the longest configured horizon the fund returned {total:.2%} relative to "
        f"{benchmark}; style {component_map.get('Style', 0.0):.2%}, sector "
        f"{component_map.get('Industry', 0.0):.2%}, country {component_map.get('Country', 0.0):.2%}, "
        f"market {component_map.get('Market', 0.0):.2%}, specific/residual "
        f"{component_map.get('Specific', 0.0):.2%}."
    )
    try:
        plots = _plot_divs(attribution, risk)
    except ModuleNotFoundError as exc:
        raise RuntimeError("plotly is required to render the offline dashboard") from exc

    payload = {
        "governance": diagnostics.governance_summary,
        "data_quality": diagnostics.data_quality_report.to_dict(),
    }
    style = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; color: #172126; background: #f7f8f6; }
    header { background: #18383b; color: white; padding: 28px 40px; }
    main { max-width: 1180px; margin: 0 auto; padding: 28px 24px 60px; }
    section { background: white; border: 1px solid #d9dfdc; border-radius: 6px; padding: 22px; margin: 18px 0; }
    h1, h2 { margin: 0 0 12px; }
    .muted { color: #66737a; }
    .headline { font-size: 20px; line-height: 1.45; }
    .data-table { border-collapse: collapse; width: 100%; font-size: 13px; }
    .data-table th, .data-table td { border-bottom: 1px solid #e5e9e7; padding: 7px 8px; text-align: left; }
    .data-table th { background: #eef3f1; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    details { margin: 12px 0; }
    summary { cursor: pointer; font-weight: 650; }
    code { background: #eef3f1; padding: 2px 5px; border-radius: 3px; }
    """
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Factor Attribution Dashboard</title>
  <style>{style}</style>
</head>
<body>
<header>
  <h1>{html.escape(fund)} Relative Performance Attribution</h1>
  <div>Benchmark: {html.escape(benchmark)} | Run: {datetime.now(timezone.utc).isoformat()} | Config hash: <code>{config_hash}</code></div>
</header>
<main>
  <section><h2>Headline</h2><p class="headline">{html.escape(headline)}</p></section>
  <section><h2>Charts</h2>{plots}</section>
  <section><h2>Attribution</h2>{_table(attribution.horizon_summary)}</section>
  <section><h2>Factor Detail</h2>{_table(attribution.factor_horizon_detail)}</section>
  <section><h2>Risk</h2><div class="grid"><div>{_table(risk.block_table)}</div><div>{_table(risk.factor_table)}</div></div></section>
  <section><h2>Diagnostics</h2>
    <h3>Coefficients</h3>{_table(diagnostics.coefficient_table)}
    <h3>Stage R2</h3>{_table(diagnostics.stage_r2_table)}
    <h3>Largest Residual Months</h3>{_table(diagnostics.residual_analysis)}
  </section>
  <section><h2>Governance & Data</h2>
    <pre>{html.escape(json.dumps(payload, indent=2, default=_json_default))}</pre>
    <h3>Factor Construction Audit</h3>{_table(factor_audit)}
  </section>
</main>
</body>
</html>"""
    output.write_text(body, encoding="utf-8")
    return output

