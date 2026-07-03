# Dashboard Guide

The dashboard is a single offline HTML file. It embeds Plotly and data directly into
the file, so it can be opened from email, a network drive, or a local folder without a
server.

## Header

The header shows:

- fund column name;
- benchmark column name;
- UTC run timestamp;
- config hash.

Use the config hash to confirm whether two reports were generated from the same
configuration.

## Headline

The headline summarizes the longest configured horizon. With the default config, this
is 60 months.

It reports:

- total relative return;
- market contribution;
- style contribution;
- sector/industry contribution;
- country contribution;
- specific/residual contribution.

The headline is a summary, not a substitute for reviewing diagnostics.

## Charts

### Block Attribution Bar Chart

Shows geometric linked contribution by block for the longest configured horizon.

Positive bars helped relative return. Negative bars detracted.

### Cumulative Actual vs Fitted Relative Return

Compares compounded actual relative return against compounded fitted relative return.

Use this to assess whether the model broadly follows the relative return path or only
matches the full-period endpoint.

### Tracking Error Variance Share

Shows active risk contribution by block and specific/residual risk.

Risk contribution is not the same as return contribution.

## Attribution Table

The attribution table contains one row per component per horizon.

Important fields:

- `horizon_months`: requested horizon.
- `used_months`: actual number of months used.
- `partial`: whether the requested horizon was longer than available history.
- `component`: Market, Style, Industry, Country, Alpha, or Specific.
- `geometric_contribution`: linked contribution that reconciles to compounded relative return.
- `arithmetic_contribution`: simple sum of monthly contributions.
- `total_relative_return`: compounded relative return for the horizon.
- `reconciliation_gap`: difference between summed geometric components and total relative return.

## Factor Detail

The factor detail table decomposes block totals into configured factor-level
contributions.

Use it to identify which style, sector, or country proxies drove a block result.

## Risk Section

The block table shows tracking-error variance share by block. The factor table shows
factor-level risk contributions.

Review this beside return attribution:

- high return and high risk can indicate intentional exposure;
- low return and high risk can indicate inefficient exposure;
- high residual risk can indicate missing factors or unstable active behavior.

## Diagnostics

### Coefficients

Shows final model betas, HAC t-statistics, p-values, significance stars, VIF, and
flags.

High VIF means factor exposures are hard to distinguish statistically.

### Stage R2

Shows how explanatory power changes as factor blocks are added:

1. Market
2. Style
3. Industry
4. Country

Incremental R2 identifies whether a block adds explanatory value.

### Largest Residual Months

Lists the months with the largest unexplained active returns. These rows are labelled
for qualitative review. They should not be automatically interpreted as skill or error.

## Governance & Data

This section shows:

- data-quality report;
- active governance flags;
- factor construction audit;
- model observation count;
- factor count;
- estimator used;
- reconciliation status;
- tracking-error explained.

Review this section before using the attribution result in an investment discussion.

