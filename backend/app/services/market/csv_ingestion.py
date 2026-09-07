"""
Historical CSV Ingestion & Data Quality Engine.
Provides secure, streaming-friendly ingestion for custom M1/M5/M15/H1 historical datasets.
"""

import io
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np

MAX_ALLOWED_FILE_SIZE = 25 * 1024 * 1024  # 25 MB Max
MAX_SUPPORTED_BARS = 150000
MIN_REQUIRED_BARS = 50

HEADER_SYNONYMS = {
    "datetime": ["datetime", "date_time", "timestamp", "ts", "dt"],
    "date_only": ["date", "<date>", "d"],
    "time_only": ["time", "<time>", "t"],
    "open": ["open", "o", "<open>", "open_price"],
    "high": ["high", "h", "<high>", "high_price"],
    "low": ["low", "l", "<low>", "low_price"],
    "close": ["close", "c", "<close>", "close_price"],
    "volume": ["volume", "vol", "v", "<vol>", "<tickvol>", "tick_volume", "real_volume"]
}


def _match_column(col_name: str, synonyms: List[str]) -> bool:
    cleaned = col_name.strip().lower().replace(" ", "_").replace("-", "_")
    return cleaned in synonyms


def parse_and_validate_csv(
    file_bytes: bytes,
    expected_symbol: Optional[str] = None,
    expected_timeframe: Optional[str] = None,
    max_bars: int = MAX_SUPPORTED_BARS
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if len(file_bytes) == 0:
        raise ValueError("Uploaded CSV file is empty (0 bytes).")

    if len(file_bytes) > MAX_ALLOWED_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise ValueError(f"File size ({size_mb:.2f}MB) exceeds maximum allowed limit of 25MB.")

    try:
        content_str = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content_str = file_bytes.decode("latin-1")
        except Exception as e:
            raise ValueError(f"Unable to decode CSV text: {e}")

    first_few_lines = "\n".join(content_str.splitlines()[:5])
    delimiter = ","
    if "\t" in first_few_lines and first_few_lines.count("\t") > first_few_lines.count(","):
        delimiter = "\t"
    elif ";" in first_few_lines and first_few_lines.count(";") > first_few_lines.count(","):
        delimiter = ";"

    try:
        raw_df = pd.read_csv(
            io.StringIO(content_str),
            sep=delimiter,
            nrows=max_bars + 1000,
            dtype=str,
            on_bad_lines="skip"
        )
    except Exception as e:
        raise ValueError(f"Malformed CSV structure: {e}")

    if raw_df.empty or len(raw_df.columns) < 4:
        raise ValueError("Missing mandatory columns: CSV must contain at least 4 columns (Date/Time, Open, High, Low, Close).")

    raw_cols = list(raw_df.columns)
    col_mapping = {}
    found_types = set()

    for col in raw_cols:
        for target, syns in HEADER_SYNONYMS.items():
            if target not in found_types and _match_column(col, syns):
                col_mapping[col] = target
                found_types.add(target)
                break

    # Handle separate Date and Time columns (MetaTrader format)
    if "date_only" in found_types and "time_only" in found_types:
        date_col = next(c for c in raw_cols if _match_column(c, HEADER_SYNONYMS["date_only"]))
        time_col = next(c for c in raw_cols if _match_column(c, HEADER_SYNONYMS["time_only"]))
        raw_df["datetime_combined"] = raw_df[date_col].astype(str).str.strip() + " " + raw_df[time_col].astype(str).str.strip()
        col_mapping["datetime_combined"] = "datetime"
        found_types.add("datetime")
    elif "date_only" in found_types and "datetime" not in found_types:
        date_col = next(c for c in raw_cols if _match_column(c, HEADER_SYNONYMS["date_only"]))
        col_mapping[date_col] = "datetime"
        found_types.add("datetime")

    required = {"open", "high", "low", "close"}
    missing = required - found_types
    if missing:
        raise ValueError(f"Missing mandatory OHLC columns: {missing}. Available columns: {raw_cols}")

    df = raw_df.rename(columns=col_mapping)
    valid_cols = ["datetime", "open", "high", "low", "close", "volume"]
    df = df[[c for c in valid_cols if c in df.columns]].copy()

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 1000.0

    initial_row_count = len(df)

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
        df = df.dropna(subset=["datetime"])
    else:
        df["datetime"] = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=len(df), freq="1h")

    df = df.dropna(subset=["open", "high", "low", "close"])

    valid_mask = (
        (df["open"] > 0) &
        (df["high"] > 0) &
        (df["low"] > 0) &
        (df["close"] > 0) &
        (df["high"] >= df["low"]) &
        (df["high"] >= df["open"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["open"]) &
        (df["low"] <= df["close"])
    )
    invalid_rows_count = int((~valid_mask).sum())
    df = df[valid_mask].copy()

    df = df.sort_values(by="datetime", ascending=True)

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["datetime"], keep="last")
    duplicates_dropped = before_dedup - len(df)

    final_bar_count = len(df)

    if final_bar_count < MIN_REQUIRED_BARS:
        raise ValueError(
            f"Insufficient valid bars in dataset ({final_bar_count} bars). Minimum required is {MIN_REQUIRED_BARS}."
        )

    if final_bar_count > max_bars:
        df = df.tail(max_bars).copy()

    start_date = df["datetime"].iloc[0].isoformat()
    end_date = df["datetime"].iloc[-1].isoformat()

    diagnostics = {
        "initial_rows": initial_row_count,
        "valid_bars": len(df),
        "invalid_bars_dropped": invalid_rows_count,
        "duplicates_dropped": duplicates_dropped,
        "start_date": start_date,
        "end_date": end_date,
        "detected_symbol": expected_symbol or "CUSTOM_CSV",
        "detected_timeframe": expected_timeframe or "UNKNOWN",
        "has_volume": "volume" in col_mapping.values()
    }

    df = df.reset_index(drop=True)
    return df, diagnostics


# Backward-compatible alias
ingest_csv = parse_and_validate_csv
