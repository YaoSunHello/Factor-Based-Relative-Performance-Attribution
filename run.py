"""CLI entry point for the factor attribution pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from attribution_model.attribution import compute_attribution
from attribution_model.dashboard import render_dashboard
from attribution_model.data_loader import load_config, load_returns, make_synthetic_returns
from attribution_model.diagnostics import build_diagnostics
from attribution_model.factor_builder import build_factors
from attribution_model.model import fit_model
from attribution_model.risk import compute_risk_decomposition


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a factor attribution dashboard")
    parser.add_argument("--input", help="Monthly returns Excel/CSV input")
    parser.add_argument("--config", default="config.yaml", help="YAML configuration path")
    parser.add_argument("--output", default="dashboard.html", help="Output HTML path")
    parser.add_argument("--synthetic", action="store_true", help="Run with synthetic data")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.synthetic:
        raw = make_synthetic_returns(config)
        quality = load_returns_from_frame(raw, config)[1]
    else:
        if not args.input:
            raise SystemExit("--input is required unless --synthetic is used")
        raw, quality = load_returns(args.input, config)

    factors = build_factors(raw, config)
    model = fit_model(factors.factor_data, factors.factor_blocks, config)
    attribution = compute_attribution(factors.factor_data, model, config)
    risk = compute_risk_decomposition(factors.factor_data, model)
    diagnostics = build_diagnostics(
        model,
        factors.factor_data,
        quality,
        attribution,
        factors.correlation_matrix,
        factors.correlation_flags,
    )
    output = render_dashboard(args.output, config, attribution, risk, diagnostics, factors.audit_table)
    print(
        f"Wrote {output} | obs={len(factors.factor_data)} | factors={len(model.factor_columns)} | "
        f"TE explained={model.tracking_error_explained:.1%}"
    )


def load_returns_from_frame(raw, config):
    """Validate synthetic data by round-tripping through the public loader contract."""

    temp_path = Path(".synthetic_returns.csv")
    raw.to_csv(temp_path, index=False)
    try:
        return load_returns(temp_path, config)
    finally:
        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

