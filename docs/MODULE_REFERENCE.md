# Module Reference

## Package Layout

```text
attribution_model/
  __init__.py
  data_loader.py
  factor_builder.py
  model.py
  attribution.py
  risk.py
  diagnostics.py
  dashboard.py
run.py
config.yaml
tests/
```

## `run.py`

CLI entry point. It wires the full pipeline:

```text
load config
load or synthesize returns
build factors
fit model
compute attribution
compute risk decomposition
build diagnostics
render dashboard
```

Public command:

```bash
python3 run.py --input monthly_returns.xlsx --config config.yaml --output dashboard.html
python3 run.py --synthetic --output demo.html
```

## `data_loader.py`

Responsibilities:

- Load YAML config.
- Load Excel or CSV input.
- Normalize dates to month end.
- Validate configured columns.
- Validate observation count.
- Detect duplicate dates and calendar gaps.
- Report missing values.
- Report stale return runs.
- Report leading missing values for factor launch-date limitations.
- Report extreme returns above 25% in absolute value.
- Generate synthetic monthly return data.

Key objects:

- `DataQualityReport`

Key functions:

- `load_config(path)`
- `configured_return_columns(config)`
- `load_returns(input_path, config, sheet_name=None)`
- `make_synthetic_returns(config, periods=72, seed=7)`

## `factor_builder.py`

Responsibilities:

- Compute geometric fund relative return.
- Compute market, style, industry, and country active factor returns.
- Drop rows that are not usable across all configured factors.
- Build factor construction audit table.
- Build factor correlation matrix.
- Flag high factor correlations.

Key objects:

- `FactorBuildResult`

Key functions:

- `factor_column_name(block, name)`
- `build_factors(raw_returns, config)`

## `model.py`

Responsibilities:

- Fit staged OLS regressions.
- Use HAC/Newey-West covariance for OLS diagnostics.
- Store stage-level coefficients and diagnostics.
- Fit optional ridge or lasso final model.
- Back-transform regularized betas to original return scale.
- Compute VIF.
- Compute tracking-error explained and residual volatility.
- Compute rolling 36-month beta stability flags.

Key objects:

- `StageResult`
- `ModelResult`

Key functions:

- `fit_model(factor_data, factor_blocks, config)`

## `attribution.py`

Responsibilities:

- Compute monthly factor contributions.
- Compute alpha and specific/residual attribution.
- Roll factors into Market, Style, Industry, Country, Alpha, and Specific blocks.
- Compute trailing horizon attribution.
- Apply Carino-style geometric linking.
- Report arithmetic attribution as secondary view.
- Emit reconciliation warnings.
- Build cumulative actual versus fitted relative return series.

Key objects:

- `AttributionResult`

Key functions:

- `compute_attribution(factor_data, model, config)`

Internal helper:

- `_carino_scale(y)`

## `risk.py`

Responsibilities:

- Compute factor covariance matrix.
- Compute factor risk contribution using `beta_i * (Sigma beta)_i`.
- Aggregate risk by block.
- Add specific/residual variance share.

Key objects:

- `RiskResult`

Key functions:

- `compute_risk_decomposition(factor_data, model)`

## `diagnostics.py`

Responsibilities:

- Build coefficient table.
- Add significance stars and VIF flags.
- Build staged R2 table.
- Pass through correlation and rolling beta diagnostics.
- Select largest residual months for qualitative review.
- Build governance summary.
- Pass through data-quality report.

Key objects:

- `DiagnosticsResult`

Key functions:

- `build_diagnostics(...)`

## `dashboard.py`

Responsibilities:

- Render a single self-contained HTML report.
- Embed Plotly inline for offline use.
- Render headline, charts, attribution, risk, diagnostics, and governance tables.
- Include config hash for audit traceability.

Key functions:

- `render_dashboard(output_path, config, attribution, risk, diagnostics, factor_audit)`

## Tests

| Test file | Coverage |
|---|---|
| `tests/test_data_loader.py` | Input validation, synthetic data, missing columns, observation count, calendar gaps. |
| `tests/test_factor_builder.py` | Relative-return arithmetic, null market factor, staggered factor launch dates. |
| `tests/test_attribution.py` | Carino scaling reconciliation helper. |
| `tests/test_pipeline.py` | End-to-end synthetic pipeline and dashboard output. |

