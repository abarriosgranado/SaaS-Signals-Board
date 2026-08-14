from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_DATA_DIR = Path("data/raw")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def load_csv(data_dir: Path, stem: str) -> pd.DataFrame:
    matches = sorted(data_dir.glob(f"*{stem}*.csv"))
    if not matches:
        raise FileNotFoundError(
            f"Could not find a CSV containing '{stem}' in {data_dir.resolve()}"
        )
    return normalize_columns(pd.read_csv(matches[0]))


def find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    raise KeyError(
        "Missing expected column. Tried: "
        + ", ".join(candidates)
        + f". Available columns: {', '.join(df.columns)}"
    )


def load_ravenstack(data_dir: Path = RAW_DATA_DIR) -> dict[str, pd.DataFrame]:
    return {
        "subscriptions": load_csv(data_dir, "subscription"),
        "churn_events": load_csv(data_dir, "churn"),
    }

