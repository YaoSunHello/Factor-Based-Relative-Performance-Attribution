import pandas as pd

from attribution_model.attribution import _carino_scale


def test_carino_scale_reconciles_hand_built_series():
    y = pd.Series([0.02, -0.01, 0.03])
    components = pd.Series([0.015, -0.006, 0.02])
    scale = _carino_scale(y)
    total = (1 + y).prod() - 1
    linked_total_y = (y * scale).sum()

    assert abs(linked_total_y - total) < 1e-12
    assert (components * scale).notna().all()

