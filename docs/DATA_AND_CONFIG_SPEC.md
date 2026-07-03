# Data And Config Specification

## Input Data Contract

The model expects one monthly return table in CSV or Excel format.

Required properties:

- One row per month.
- One date column.
- Returns are decimal returns, not percentages.
- Dates can be any date within the month; they are normalized to month end.
- All series are total return.
- All series are in the same currency.
- Fund and benchmark cannot have missing values.
- Factor columns may have leading missing values to represent launch-date limitations.

Example:

```csv
Date,Fund,Benchmark,MSCI_World,MSCI_World_Value,MSCI_World_Quality
2020-01-31,0.012,0.010,0.011,0.008,0.013
2020-02-29,-0.081,-0.079,-0.080,-0.086,-0.074
```

## Observation Requirements

| Observations | Behavior |
|---:|---|
| `< 36` | Fail. |
| `36-59` | Continue with warning. |
| `>= 60` | Preferred minimum. |

## Data Quality Checks

`data_loader.py` creates a `DataQualityReport` containing:

- missing values by column and date;
- duplicate monthly dates;
- missing calendar months;
- stale returns, defined as 3 or more identical consecutive returns;
- leading missing values that imply index launch-date limitations;
- extreme monthly returns where absolute return is greater than 25%.

Extreme values are flagged but not dropped.

## `config.yaml`

### `input`

```yaml
input:
  file: monthly_returns.xlsx
  sheet_name: Returns
```

`file` is informational for the default template. The CLI `--input` controls the actual
input path. `sheet_name` is used for Excel files.

### `columns`

```yaml
columns:
  date: Date
  fund: Fund
  benchmark: Benchmark
```

These names must match the input file.

### `market_factor`

```yaml
market_factor:
  index_column: MSCI_World
```

The market factor is:

```text
MKT = market_index_return - benchmark_return
```

If the benchmark is the market index, set:

```yaml
market_factor: null
```

### `horizons`

```yaml
horizons: [12, 36, 60]
```

The dashboard reports trailing windows ending at the latest input date. If the history
is shorter than a configured horizon, the horizon is marked partial.

### `regression`

```yaml
regression:
  se_type: newey_west
  nw_lags: 3
  regularisation: none
  ridge_alpha: 1.0
```

Supported final estimators:

- `none`: staged OLS with Newey-West/HAC standard errors;
- `ridge`: final model uses standardized ridge regression and back-transformed betas;
- `lasso`: final model uses standardized lasso regression and back-transformed betas.

`nw_lags` controls HAC covariance lags for OLS diagnostics.

### `thresholds`

```yaml
thresholds:
  vif_flag: 5
  corr_flag: 0.75
  reconciliation_tol_bps: 1
```

- `vif_flag`: VIF threshold for multicollinearity review.
- `corr_flag`: absolute pairwise factor-correlation threshold.
- `reconciliation_tol_bps`: maximum allowed geometric attribution reconciliation gap.

### `attribution`

```yaml
attribution:
  linking: geometric
  alpha_treatment: separate
```

Current implementation reports geometric attribution and arithmetic attribution. Alpha is
reported as a separate attribution line by default.

### `factors`

```yaml
factors:
  style:
    - {name: Value, index_column: MSCI_World_Value, parent_column: MSCI_World}
  industry:
    - {name: Technology, index_column: MSCI_World_IT, parent_column: MSCI_World}
  country:
    - {name: UnitedStates, index_column: MSCI_USA, parent_column: MSCI_World}
```

Each factor creates:

```text
factor_return = index_column_return - parent_column_return
```

Factor names are converted into stable internal columns by combining block and name,
for example `style_Value`.

## Generated Files

The standard generated dashboard names are ignored by git:

- `demo.html`
- `dashboard.html`

