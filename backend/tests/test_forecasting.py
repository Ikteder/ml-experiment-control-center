from __future__ import annotations

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from app.services.presets import get_preset
from app.services.runner import build_demand_frame, chronological_split


def test_demand_features_are_deterministic_and_use_only_prior_targets() -> None:
    config = get_preset("demand-forecasting")["config"]
    first, feature_names = build_demand_frame(config)
    second, _ = build_demand_frame(config)

    assert_frame_equal(first, second)
    assert {"lag_1", "lag_7", "rolling_mean_7"} <= set(feature_names)

    full_series = first.set_index("date")["target"]
    for row in first.iloc[7:25].itertuples():
        assert row.lag_1 == full_series.loc[row.date - pd.Timedelta(days=1)]
        assert row.lag_7 == full_series.loc[row.date - pd.Timedelta(days=7)]
        prior_week = full_series.loc[row.date - pd.Timedelta(days=7) : row.date - pd.Timedelta(days=1)]
        assert row.rolling_mean_7 == pytest.approx(prior_week.mean())


def test_chronological_split_keeps_future_dates_out_of_training() -> None:
    config = get_preset("demand-forecasting")["config"]
    frame, _ = build_demand_frame(config)
    train, test = chronological_split(frame, config["test_size"])

    assert len(train) + len(test) == len(frame)
    assert train["date"].max() < test["date"].min()
    assert test["date"].is_monotonic_increasing
