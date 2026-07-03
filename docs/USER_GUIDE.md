# User Guide

## Purpose

The project explains a fund's relative return versus a benchmark using observable
market, style, industry, country, alpha, and specific/residual components.

It is a return-based attribution model. It does not use portfolio holdings, security
transactions, benchmark constituents, or holdings-level Brinson attribution. It is best
used as an internal investment-risk oversight and manager-review tool.

## Installation

Use Python 3.11 or later.

```bash
python3 -m pip install -r requirements.txt
```

The declared dependencies are:

- `pandas`
- `numpy`
- `statsmodels`
- `scikit-learn`
- `plotly`
- `PyYAML`
- `openpyxl`
- `pytest`

## Run With Synthetic Data

The project includes a synthetic data generator so the full pipeline can run without
licensed index data.

```bash
python3 run.py --synthetic --output demo.html
```

Expected console output:

```text
Wrote demo.html | obs=<number> | factors=<number> | TE explained=<percent>
```

Open `demo.html` in a browser.

## Run With Your Own Data

```bash
python3 run.py --input monthly_returns.xlsx --config config.yaml --output dashboard.html
```

CSV input is also supported:

```bash
python3 run.py --input monthly_returns.csv --config config.yaml --output dashboard.html
```

## Command Line Options

| Option | Required | Meaning |
|---|---:|---|
| `--input` | No when `--synthetic` is used; otherwise yes | Excel or CSV monthly returns file. |
| `--config` | No | YAML config path. Defaults to `config.yaml`. |
| `--output` | No | Output HTML file. Defaults to `dashboard.html`. |
| `--synthetic` | No | Use generated data instead of an input file. |

## Expected Workflow

1. Prepare monthly total returns for fund, benchmark, market index, and factor indices.
2. Confirm all returns are decimal returns, same currency, and month-end aligned.
3. Edit `config.yaml` so every column mapping matches the input file.
4. Run the pipeline.
5. Review the dashboard's governance and data-quality section first.
6. Review attribution, risk, and diagnostics.
7. Treat residual months as qualitative review items, not automatic skill labels.

## Common Errors

### Missing Required Columns

The loader raises an error if the input file does not contain a configured column.
Check `config.yaml` against the input file header.

### Fewer Than 36 Months

The loader fails below 36 monthly observations. Between 36 and 59 observations it
continues but emits a warning because regression estimates are less stable.

### Excel Dependencies

Excel input requires `openpyxl`. Install dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

### Dashboard Rendering

The dashboard requires `plotly`. The generated HTML embeds Plotly inline, so the final
HTML file does not require internet access.

## Interpretation Rules

- Positive component contribution means the component helped relative return.
- Negative component contribution means the component detracted from relative return.
- Alpha is the regression intercept converted into attribution form.
- Specific/residual is unexplained active return after the configured factors and alpha.
- Tracking-error variance contribution is risk contribution, not return contribution.
- A factor can contribute little return but a large share of active risk.

