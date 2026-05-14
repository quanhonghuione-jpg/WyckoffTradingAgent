from __future__ import annotations

import pandas as pd

from scripts.wyckoff_funnel import _append_etf_section, _rank_etf_candidates


def _frame(step: float, last_volume: float) -> pd.DataFrame:
    dates = pd.date_range("2026-04-01", periods=30, freq="B")
    close = pd.Series([100.0 + i * step for i in range(30)])
    volume = pd.Series([100.0] * 29 + [last_volume])
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "close": close,
            "volume": volume,
        }
    )


def test_rank_etf_candidates_orders_by_strength():
    rows = _rank_etf_candidates(
        ["512880", "512480"],
        {
            "512880": _frame(0.1, 100.0),
            "512480": _frame(1.0, 280.0),
        },
        {"512880": "证券", "512480": "半导体"},
        {"512880": "吸筹通道", "512480": "主升通道+点火破局"},
    )

    assert [row["code"] for row in rows] == ["512480", "512880"]
    assert rows[0]["name"] == "半导体ETF"
    assert rows[0]["ret20"] > rows[1]["ret20"]


def test_append_etf_section_renders_compact_rows():
    rows = [
        {
            "code": "512480",
            "name": "半导体ETF",
            "score": 12.3,
            "ret3": 2.1,
            "ret20": 10.5,
            "vol_ratio": 1.8,
            "channel": "主升通道",
        }
    ]
    lines: list[str] = []

    _append_etf_section(lines, {"pool": 2, "fetched": 2, "l2_passed": 1}, rows)

    text = "\n".join(lines)
    assert "ETF强势池" in text
    assert "512480 半导体ETF" in text
    assert "3日+2.1%" in text
