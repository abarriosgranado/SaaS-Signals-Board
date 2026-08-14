from __future__ import annotations

import pandas as pd


def add_signal_bands(
    df: pd.DataFrame,
    metric: str,
    window: int = 12,
    multiplier: float = 2.0,
) -> pd.DataFrame:
    if metric not in df.columns:
        raise KeyError(f"Metric '{metric}' not found. Available: {', '.join(df.columns)}")

    result = df.copy()
    rolling = result[metric].rolling(window=window, min_periods=max(3, window // 2))
    center = rolling.mean()
    std = rolling.std()

    result[f"{metric}_center_band"] = center
    result[f"{metric}_upper_band"] = center + multiplier * std
    result[f"{metric}_lower_band"] = center - multiplier * std
    result[f"{metric}_signal"] = "normal"
    result.loc[result[metric] > result[f"{metric}_upper_band"], f"{metric}_signal"] = (
        "above_band"
    )
    result.loc[result[metric] < result[f"{metric}_lower_band"], f"{metric}_signal"] = (
        "below_band"
    )
    result.loc[result[f"{metric}_center_band"].isna(), f"{metric}_signal"] = (
        "warming_up"
    )
    return result
