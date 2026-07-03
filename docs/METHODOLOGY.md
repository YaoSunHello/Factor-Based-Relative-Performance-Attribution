# Methodology

## Model Objective

The model explains fund active return using returns of observable factor proxy indices.
It answers:

```text
How much of the fund's relative return can be associated with configured market,
style, industry, and country return factors?
```

It does not answer:

```text
Which exact holdings or trades created the relative return?
```

## Dependent Variable

The dependent variable is geometric relative return:

```text
y_t = (1 + r_fund,t) / (1 + r_benchmark,t) - 1
```

This is preferred to arithmetic active return because it is consistent with compounded
relative performance.

## Factor Returns

Each factor is defined relative to a configured parent index:

```text
x_i,t = r_factor_index,t - r_parent_index,t
```

Examples:

- Value factor: `MSCI_World_Value - MSCI_World`
- Sector factor: `MSCI_World_IT - MSCI_World`
- Country factor: `MSCI_USA - MSCI_World`

The market factor is:

```text
MKT_t = r_market_index,t - r_benchmark,t
```

If benchmark and market are the same index, the market factor is omitted.

## Staged Regression

The model uses cumulative staged regression for interpretability:

| Stage | Formula |
|---|---|
| Stage 1 | `Fund_Rel ~ const + MKT` |
| Stage 2 | Stage 1 + style factors |
| Stage 3 | Stage 2 + industry factors |
| Stage 4 | Stage 3 + country factors |

For each stage the model reports:

- beta coefficients;
- HAC/Newey-West t-statistics;
- p-values;
- R2;
- adjusted R2;
- incremental R2 versus prior stage;
- annualized residual volatility.

## HAC Standard Errors

Monthly return residuals can have heteroskedasticity and autocorrelation. The OLS
coefficient estimates are ordinary least squares, while standard errors use
Newey-West/HAC covariance with configured `nw_lags`.

## Regularized Fallback

The final model can optionally use ridge or lasso:

```yaml
regression:
  regularisation: ridge
```

The implementation standardizes factors for fitting, then back-transforms coefficients
to the original return scale so attribution remains:

```text
contribution_i,t = beta_i * x_i,t
```

## Monthly Attribution

For each factor:

```text
C_i,t = beta_i * x_i,t
```

Fitted relative return:

```text
yhat_t = alpha + sum_i C_i,t
```

Specific/residual:

```text
specific_t = y_t - yhat_t
```

Alpha is reported separately by default.

## Horizon Attribution

For each configured trailing horizon, total compounded relative return is:

```text
Y = product(1 + y_t) - 1
```

The project uses a Carino-style geometric linking adjustment so component sums reconcile
to compounded return.

Monthly scale:

```text
k_t = ln(1 + y_t) / y_t
```

Total-period scale:

```text
K = ln(1 + Y) / Y
```

Linked contribution:

```text
linked C_i = sum_t C_i,t * (k_t / K)
```

When returns are zero, the limit is treated as `1`.

## Risk Decomposition

The model also decomposes active risk. Let:

```text
Sigma_F = factor covariance matrix
beta = final model beta vector
```

Systematic variance approximation:

```text
Var_systematic = beta' Sigma_F beta
```

Factor variance contribution:

```text
contribution_i = beta_i * (Sigma_F beta)_i
```

Block contributions are sums of factor contributions by block. Specific risk is:

```text
Var_specific = Var(residual)
```

Risk shares are expressed relative to:

```text
Var_systematic + Var_specific
```

## Diagnostics

The model surfaces:

- coefficient table;
- VIF;
- pairwise factor correlations;
- staged R2 progression;
- rolling 36-month beta stability;
- largest unexplained residual months;
- data-quality report;
- governance summary.

## Limitations

- Regression attribution is not causal proof.
- Coefficients can be unstable with short history or many factors.
- Highly correlated factors can shift attribution between factors.
- Residual return is not automatically skill.
- Return-based attribution cannot replace holdings-based attribution when holdings data
  are available and reliable.

