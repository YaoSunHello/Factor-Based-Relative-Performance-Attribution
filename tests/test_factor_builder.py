import pandas as pd

from attribution_model.data_loader import load_config, make_synthetic_returns
from attribution_model.factor_builder import build_factors


def test_relative_return_arithmetic():
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=60)
    raw.loc[0, "Fund"] = 0.12
    raw.loc[0, "Benchmark"] = 0.10

    result = build_factors(raw, config)

    expected = (1.12 / 1.10) - 1.0
    assert abs(result.factor_data.loc[0, "Fund_Rel"] - expected) < 1e-12


def test_null_market_factor_omits_mkt():
    config = load_config("config.yaml")
    config["market_factor"] = None
    raw = make_synthetic_returns(config, periods=60)

    result = build_factors(raw, config)

    assert "MKT" not in result.factor_data.columns
    assert all(block != "Market" for block in result.factor_blocks.values())


def test_staggered_launch_dates_intersect():
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=60)
    raw.loc[:4, "MSCI_World_Value"] = pd.NA

    result = build_factors(raw, config)

    assert len(result.factor_data) == 55

