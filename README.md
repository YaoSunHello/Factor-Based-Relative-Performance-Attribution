# Factor-Based Relative Performance Attribution

A return-based factor attribution pipeline that explains a fund's relative
performance versus a benchmark over trailing 1-year, 3-year, and 5-year horizons.
It decomposes active return into market, style, industry/sector, country/region,
alpha, and specific/residual components, then renders a single self-contained HTML
dashboard.

## Run

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run with synthetic data:

```bash
python3 run.py --synthetic --output demo.html
```

Run with your own returns:

```bash
python3 run.py --input monthly_returns.xlsx --config config.yaml --output dashboard.html
```

## Input Format

The input is a monthly total-return table in CSV or Excel format. Returns must be
decimal returns, aligned to month end, total return, and in the same currency.

Example columns:

```text
Date, Fund, Benchmark, MSCI_World, MSCI_World_Value, MSCI_World_Quality, ...
```

`config.yaml` maps the fund, benchmark, market index, and each factor index to its
parent index. Factor names are not hard-coded in the model.

## Model

- Dependent variable: `(1 + Fund) / (1 + Benchmark) - 1`
- Factors: `factor index return - parent index return`
- Staged regression: market, style, industry, then country
- Estimation: OLS with Newey-West/HAC standard errors
- Optional final estimator: ridge or lasso via config
- Attribution: beta times factor return, alpha separate by default
- Linking: Carino-style geometric linking to reconcile with compounded relative return
- Risk: tracking-error variance decomposition using `beta * Sigma * beta`

## Dashboard Sections

- Headline attribution summary
- Block and factor attribution across horizons
- Cumulative actual versus fitted relative return
- Tracking-error variance decomposition
- Regression diagnostics, VIF, correlations, residual review
- Governance and data-quality audit

## Limitations

This is an explanatory return-based model, not a holdings-based attribution engine.
With roughly 60 monthly observations and 10-12 factors, coefficients can be unstable.
Residual return is labelled for qualitative review and must not be interpreted as
manager skill without further evidence.
