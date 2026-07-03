from pathlib import Path

import pandas as pd
import pytest

from attribution_model.data_loader import load_config, load_returns, make_synthetic_returns


def test_synthetic_data_validates(tmp_path):
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=60)
    path = tmp_path / "returns.csv"
    raw.to_csv(path, index=False)

    frame, report = load_returns(path, config)

    assert len(frame) == 60
    assert report.n_observations == 60
    assert not report.duplicate_dates


def test_missing_required_column_fails(tmp_path):
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=60).drop(columns=["Fund"])
    path = tmp_path / "returns.csv"
    raw.to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        load_returns(path, config)


def test_below_36_months_fails(tmp_path):
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=35)
    path = tmp_path / "returns.csv"
    raw.to_csv(path, index=False)

    with pytest.raises(ValueError, match="At least 36"):
        load_returns(path, config)


def test_calendar_gap_reported(tmp_path):
    config = load_config("config.yaml")
    raw = make_synthetic_returns(config, periods=60).drop(index=[5])
    path = tmp_path / "returns.csv"
    raw.to_csv(path, index=False)

    _, report = load_returns(path, config)

    assert report.calendar_gaps

