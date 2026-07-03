# Model Governance Map

This project is an explanatory return-based attribution model. It does not prove skill
or causality; it decomposes relative return into observable factor proxies and residuals.

| Governance check | Implementation | Dashboard surface |
|---|---|---|
| Benchmark appropriateness | `config.yaml` explicitly names fund, benchmark, market index, and factor parents. | Header and factor construction audit. |
| Factor rationale | Every factor is configured with name, index column, parent column, and block. | Factor construction audit and factor detail tables. |
| Data quality | `data_loader.py` checks missing values, duplicates, calendar gaps, stale returns, launch dates, and extreme returns. | Governance & Data panel. |
| Parsimony | Diagnostics flags factor count above the 10-12 guideline. | Governance summary. |
| Multicollinearity | `factor_builder.py` flags high pairwise correlations; `model.py` computes VIF. | Diagnostics coefficient and correlation tables. |
| Regression transparency | `model.py` fits staged OLS with HAC/Newey-West errors and reports incremental R2. | Stage R2 and coefficient tables. |
| Stability | `model.py` stores rolling 36-month betas and flags sign changes or large drift. | Diagnostics panel. |
| Reconciliation | `attribution.py` uses Carino-style geometric linking and warns on tolerance breaches. | Attribution and governance summary. |
| Residual review | `diagnostics.py` lists largest unexplained months as qualitative review items. | Diagnostics residual table. |
| Risk vs return distinction | `risk.py` decomposes tracking-error variance separately from return attribution. | Risk section. |

