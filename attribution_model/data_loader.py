"""Load, validate, and synthesize monthly return data."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


@dataclass(frozen=True)
class DataQualityReport:
    """Structured data-quality report for dashboard and governance output."""

    n_observations: int
    date_start: str | None
    date_end: str | None
    warnings: list[str] = field(default_factory=list)
    missing_values: list[dict[str, Any]] = field(default_factory=list)
    duplicate_dates: list[str] = field(default_factory=list)
    calendar_gaps: list[str] = field(default_factory=list)
    stale_return_flags: list[dict[str, Any]] = field(default_factory=list)
    launch_date_flags: list[dict[str, Any]] = field(default_factory=list)
    extreme_value_flags: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_flags(self) -> bool:
        return any(
            [
                self.warnings,
                self.missing_values,
                self.duplicate_dates,
                self.calendar_gaps,
                self.stale_return_flags,
                self.launch_date_flags,
                self.extreme_value_flags,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_observations": self.n_observations,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "warnings": self.warnings,
            "missing_values": self.missing_values,
            "duplicate_dates": self.duplicate_dates,
            "calendar_gaps": self.calendar_gaps,
            "stale_return_flags": self.stale_return_flags,
            "launch_date_flags": self.launch_date_flags,
            "extreme_value_flags": self.extreme_value_flags,
        }


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML configuration file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")
    return config


def configured_return_columns(config: dict[str, Any]) -> list[str]:
    """Return the configured non-date input return columns."""

    columns = [
        config["columns"]["fund"],
        config["columns"]["benchmark"],
    ]
    market = config.get("market_factor")
    if market and market.get("index_column"):
        columns.append(market["index_column"])
    for block_name in ("style", "industry", "country"):
        for factor in config.get("factors", {}).get(block_name, []):
            columns.extend([factor["index_column"], factor["parent_column"]])
    return sorted(set(columns))


def _month_end_dates(raw_dates: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(raw_dates, errors="raise")
    return parsed.dt.to_period("M").dt.to_timestamp("M")


def _read_input(path: str | Path, sheet_name: str | None) -> pd.DataFrame:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(input_path, sheet_name=sheet_name)
    if input_path.suffix.lower() in {".csv", ".txt"}:
        return pd.read_csv(input_path)
    raise ValueError("Input must be an Excel or CSV file")


def _find_calendar_gaps(dates: pd.Series) -> list[str]:
    if dates.empty:
        return []
    expected = pd.date_range(dates.min(), dates.max(), freq="ME")
    missing = expected.difference(pd.DatetimeIndex(dates))
    return [date.strftime("%Y-%m-%d") for date in missing]


def _find_stale_runs(series: pd.Series, column: str, dates: pd.Series) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    run_start = None
    run_value = None
    run_length = 1
    values = series.to_list()
    for idx in range(1, len(values)):
        current = values[idx]
        previous = values[idx - 1]
        if pd.notna(current) and pd.notna(previous) and current == previous:
            if run_start is None:
                run_start = idx - 1
                run_value = current
                run_length = 2
            else:
                run_length += 1
        else:
            if run_start is not None and run_length >= 3:
                flags.append(
                    {
                        "column": column,
                        "start": dates.iloc[run_start].strftime("%Y-%m-%d"),
                        "end": dates.iloc[idx - 1].strftime("%Y-%m-%d"),
                        "value": float(run_value),
                        "length": run_length,
                    }
                )
            run_start = None
            run_value = None
            run_length = 1
    if run_start is not None and run_length >= 3:
        flags.append(
            {
                "column": column,
                "start": dates.iloc[run_start].strftime("%Y-%m-%d"),
                "end": dates.iloc[len(values) - 1].strftime("%Y-%m-%d"),
                "value": float(run_value),
                "length": run_length,
            }
        )
    return flags


def load_returns(
    input_path: str | Path,
    config: dict[str, Any],
    sheet_name: str | None = None,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Load monthly returns and return a clean DataFrame plus quality report."""

    configured_sheet = sheet_name or config.get("input", {}).get("sheet_name")
    raw = _read_input(input_path, configured_sheet)
    date_column = config.get("columns", {}).get("date", "Date")
    required_columns = [date_column, *configured_return_columns(config)]
    missing_columns = [column for column in required_columns if column not in raw.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    frame = raw[required_columns].copy()
    frame[date_column] = _month_end_dates(frame[date_column])
    frame = frame.sort_values(date_column).reset_index(drop=True)

    duplicate_dates = [
        date.strftime("%Y-%m-%d")
        for date in frame.loc[frame[date_column].duplicated(), date_column]
    ]
    if duplicate_dates:
        raise ValueError(f"Duplicate monthly dates found: {duplicate_dates}")

    for column in configured_return_columns(config):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    n_observations = len(frame)
    warnings: list[str] = []
    if n_observations < 36:
        raise ValueError("At least 36 monthly observations are required")
    if n_observations < 60:
        warnings.append("Fewer than 60 monthly observations; model results are less stable")

    missing_values: list[dict[str, Any]] = []
    for column in configured_return_columns(config):
        missing_dates = frame.loc[frame[column].isna(), date_column]
        if not missing_dates.empty:
            missing_values.append(
                {
                    "column": column,
                    "dates": [date.strftime("%Y-%m-%d") for date in missing_dates],
                    "count": int(missing_dates.shape[0]),
                }
            )

    fund = config["columns"]["fund"]
    benchmark = config["columns"]["benchmark"]
    if frame[fund].isna().any() or frame[benchmark].isna().any():
        raise ValueError("Fund and benchmark returns cannot contain missing values")

    calendar_gaps = _find_calendar_gaps(frame[date_column])
    stale_flags: list[dict[str, Any]] = []
    extreme_flags: list[dict[str, Any]] = []
    launch_flags: list[dict[str, Any]] = []
    for column in configured_return_columns(config):
        stale_flags.extend(_find_stale_runs(frame[column], column, frame[date_column]))
        extreme_rows = frame.loc[frame[column].abs() > 0.25, [date_column, column]]
        for _, row in extreme_rows.iterrows():
            extreme_flags.append(
                {
                    "column": column,
                    "date": row[date_column].strftime("%Y-%m-%d"),
                    "value": float(row[column]),
                }
            )
        if frame[column].isna().any():
            first_valid = frame[column].first_valid_index()
            if first_valid not in (None, 0):
                launch_flags.append(
                    {
                        "column": column,
                        "first_usable_date": frame.loc[first_valid, date_column].strftime("%Y-%m-%d"),
                    }
                )

    clean = frame.rename(columns={date_column: "Date"})
    report = DataQualityReport(
        n_observations=n_observations,
        date_start=clean["Date"].min().strftime("%Y-%m-%d"),
        date_end=clean["Date"].max().strftime("%Y-%m-%d"),
        warnings=warnings,
        missing_values=missing_values,
        duplicate_dates=duplicate_dates,
        calendar_gaps=calendar_gaps,
        stale_return_flags=stale_flags,
        launch_date_flags=launch_flags,
        extreme_value_flags=extreme_flags,
    )
    return clean, report


def make_synthetic_returns(
    config: dict[str, Any],
    periods: int = 72,
    seed: int = 7,
) -> pd.DataFrame:
    """Generate plausible correlated monthly returns for configured columns."""

    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-31", periods=periods, freq="ME")
    market = rng.normal(0.006, 0.04, periods)
    benchmark = market + rng.normal(0.0005, 0.012, periods)
    frame = pd.DataFrame(
        {
            "Date": dates,
            config["columns"]["benchmark"]: benchmark,
            config["columns"]["fund"]: benchmark + 0.0015 + 0.25 * market + rng.normal(0, 0.015, periods),
        }
    )

    market_cfg = config.get("market_factor")
    if market_cfg and market_cfg.get("index_column"):
        frame[market_cfg["index_column"]] = market + rng.normal(0, 0.006, periods)

    for block_name, block_factors in config.get("factors", {}).items():
        block_scale = {"style": 0.018, "industry": 0.022, "country": 0.02}.get(block_name, 0.02)
        for idx, factor in enumerate(block_factors):
            parent = factor["parent_column"]
            if parent not in frame:
                frame[parent] = benchmark + rng.normal(0, 0.004, periods)
            active = rng.normal(0.0003 * (idx + 1), block_scale, periods)
            frame[factor["index_column"]] = frame[parent] + active
    return frame

