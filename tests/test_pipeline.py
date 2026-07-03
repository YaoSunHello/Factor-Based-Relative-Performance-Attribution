from pathlib import Path

from attribution_model.attribution import compute_attribution
from attribution_model.dashboard import render_dashboard
from attribution_model.data_loader import load_config, load_returns, make_synthetic_returns
from attribution_model.diagnostics import build_diagnostics
from attribution_model.factor_builder import build_factors
from attribution_model.model import fit_model
from attribution_model.risk import compute_risk_decomposition


def test_synthetic_pipeline_outputs_dashboard(tmp_path):
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=72)
    csv_path = tmp_path / "returns.csv"
    raw.to_csv(csv_path, index=False)
    loaded, quality = load_returns(csv_path, config)
    factors = build_factors(loaded, config)
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
    output = render_dashboard(tmp_path / "demo.html", config, attribution, risk, diagnostics, factors.audit_table)

    assert output.exists()
    assert "Relative Performance Attribution" in output.read_text()
    assert abs(risk.block_table["variance_share"].sum() - 1.0) < 1e-8

