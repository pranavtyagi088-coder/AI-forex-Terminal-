import pytest
import io
import pandas as pd
from fastapi.testclient import TestClient
from app.services.market.csv_ingestion import parse_and_validate_csv
from app.main import app

client = TestClient(app)

def create_sample_csv(rows: int = 100, reversed_order: bool = False, add_duplicates: bool = False, add_bad_rows: bool = False) -> bytes:
    lines = ["datetime,open,high,low,close,volume"]
    base = 1.0800
    dates = pd.date_range("2026-01-01 00:00:00", periods=rows, freq="1h")
    if reversed_order:
        dates = dates[::-1]

    for i, dt in enumerate(dates):
        t_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        o = base + (i * 0.0001)
        h = o + 0.0010
        l = o - 0.0010
        c = o + 0.0005
        lines.append(f"{t_str},{o:.5f},{h:.5f},{l:.5f},{c:.5f},1000")

    if add_duplicates:
        lines.append(lines[-1])
    if add_bad_rows:
        lines.append("2026-02-15 00:00:00,1.0800,1.0700,1.0900,1.0850,1000")
        lines.append("2026-02-15 01:00:00,-1.0800,1.0900,1.0700,1.0850,1000")
        lines.append("corrupt,row,extra,columns,not,matching,schema,extra")

    return "\n".join(lines).encode("utf-8")


def test_csv_ingestion_standard_dataset():
    csv_bytes = create_sample_csv(rows=120)
    df, diag = parse_and_validate_csv(csv_bytes, expected_symbol="EUR/USD")
    assert len(df) == 120
    assert diag["valid_bars"] == 120
    assert diag["invalid_bars_dropped"] == 0
    assert "open" in df.columns
    assert "high" in df.columns
    assert "low" in df.columns
    assert "close" in df.columns


def test_csv_ingestion_metatrader_separate_date_time():
    dates = pd.date_range("2026-01-01 00:00:00", periods=80, freq="1h")
    mt_lines = ["<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>"]
    for i, dt in enumerate(dates):
        d_str = dt.strftime("%Y.%m.%d")
        t_str = dt.strftime("%H:%M:%S")
        o = 1.0850 + (i * 0.0001)
        h = o + 0.0010
        l = o - 0.0010
        c = o + 0.0005
        mt_lines.append(f"{d_str}\t{t_str}\t{o:.5f}\t{h:.5f}\t{l:.5f}\t{c:.5f}\t500")

    mt_csv = "\n".join(mt_lines).encode("utf-8")
    df, diag = parse_and_validate_csv(mt_csv)
    assert len(df) == 80
    assert diag["valid_bars"] == 80
    assert df["open"].iloc[0] == 1.0850


def test_csv_ingestion_chronological_auto_sort():
    csv_bytes = create_sample_csv(rows=80, reversed_order=True)
    df, diag = parse_and_validate_csv(csv_bytes)
    assert len(df) == 80
    assert df["datetime"].iloc[0] < df["datetime"].iloc[-1]


def test_csv_ingestion_drops_bad_rows_and_duplicates():
    csv_bytes = create_sample_csv(rows=100, add_duplicates=True, add_bad_rows=True)
    df, diag = parse_and_validate_csv(csv_bytes)
    assert diag["duplicates_dropped"] >= 1
    assert diag["invalid_bars_dropped"] >= 2
    assert len(df) == 100


def test_csv_ingestion_rejects_insufficient_bars():
    csv_bytes = create_sample_csv(rows=20)
    with pytest.raises(ValueError, match="Insufficient valid bars"):
        parse_and_validate_csv(csv_bytes)


def test_csv_ingestion_rejects_empty_file():
    with pytest.raises(ValueError, match="empty"):
        parse_and_validate_csv(b"")


def test_api_run_backtest_with_valid_csv():
    csv_bytes = create_sample_csv(rows=250)
    files = {"file": ("test_eurusd.csv", io.BytesIO(csv_bytes), "text/csv")}
    data = {
        "symbol": "EUR/USD",
        "strategy_name": "Liquidity Sweep Continuation",
        "timeframe": "1H",
        "initial_balance": 10000.0,
        "risk_percent": 1.0,
        "slippage_pips": 0.5,
        "commission_per_lot": 7.0,
        "split_oos": True
    }
    response = client.post("/api/backtest/run-csv", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["symbol"] == "EUR/USD"
    assert res_data["bars_analyzed"] == 250
    assert "overall_metrics" in res_data
    assert res_data["overall_metrics"]["win_rate"] >= 0.0
    assert len(res_data["equity_curve"]) > 0
    assert any("Custom CSV Ingested" in note for note in res_data["notes"])


def test_api_run_backtest_with_corrupt_csv_returns_400():
    corrupt_bytes = b"not_a_csv,no_ohlc_columns\n1,2"
    files = {"file": ("corrupt.csv", io.BytesIO(corrupt_bytes), "text/csv")}
    response = client.post("/api/backtest/run-csv", files=files, data={"symbol": "EUR/USD"})
    assert response.status_code == 400
    assert "Missing mandatory" in response.json()["detail"] or "at least 4 columns" in response.json()["detail"]
