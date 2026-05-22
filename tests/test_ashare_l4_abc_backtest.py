from __future__ import annotations

from datetime import date

import pandas as pd

from scripts.ashare_l4_abc_backtest import SignalCandidate, replay_portfolio


def _hist(rows: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": date.fromisoformat(day),
                "open": open_px,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000,
            }
            for day, open_px, high, low, close in rows
        ]
    )


def _candidate(code: str, signal_day: str, entry_day: str, score: float = 10.0) -> SignalCandidate:
    return SignalCandidate(
        signal_date=date.fromisoformat(signal_day),
        entry_date=date.fromisoformat(entry_day),
        code=code,
        name=code,
        trigger="sos",
        score=score,
        abc_grade="A+B",
        abc_count=2,
        regime="NEUTRAL",
        track="Trend",
    )


def test_portfolio_caps_positions_at_four():
    hist_map = {
        str(i): _hist(
            [("2026-01-01", 10, 10, 10, 10), ("2026-01-02", 10, 11, 9, 10.5), ("2026-01-03", 11, 11, 10, 10.8)]
        )
        for i in range(5)
    }
    candidates = [_candidate(str(i), "2026-01-01", "2026-01-02", 100 - i) for i in range(5)]

    trades, nav = replay_portfolio(
        hist_map, candidates, [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)], 4, -8, -5
    )

    assert len(trades) == 4
    assert max(row["positions"] for row in nav) == 4
    assert {trade.code for trade in trades} == {"0", "1", "2", "3"}


def test_entry_day_does_not_exit_same_day():
    hist_map = {
        "A": _hist(
            [
                ("2026-01-01", 10, 10, 10, 10),
                ("2026-01-02", 10, 10, 8, 8),
                ("2026-01-03", 8, 8, 7, 7.5),
            ]
        )
    }
    candidates = [_candidate("A", "2026-01-01", "2026-01-02")]

    trades, _ = replay_portfolio(
        hist_map, candidates, [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)], 4, -8, -5
    )

    assert trades[0].exit_date == "2026-01-03"
    assert trades[0].exit_reason == "stop_loss"


def test_profit_drop_exit_after_profit_run():
    hist_map = {
        "A": _hist(
            [
                ("2026-01-01", 10, 10, 10, 10),
                ("2026-01-02", 10, 12, 10, 12),
                ("2026-01-03", 12, 12, 11, 11.2),
            ]
        )
    }
    candidates = [_candidate("A", "2026-01-01", "2026-01-02")]

    trades, _ = replay_portfolio(
        hist_map, candidates, [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)], 4, -8, -5
    )

    assert trades[0].exit_reason == "profit_drop"
    assert trades[0].exit_price == 11.2


def test_limit_down_locked_day_cannot_exit():
    hist_map = {
        "A": _hist(
            [
                ("2026-01-01", 10, 10, 10, 10),
                ("2026-01-02", 10, 10, 10, 10),
                ("2026-01-03", 8, 8, 8, 8),
                ("2026-01-04", 8, 8, 7, 7.5),
            ]
        )
    }

    trades, _ = replay_portfolio(
        hist_map,
        [_candidate("A", "2026-01-01", "2026-01-02")],
        [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3), date(2026, 1, 4)],
        4,
        -8,
        -5,
    )

    assert trades[0].exit_date == "2026-01-04"
    assert trades[0].exit_reason == "stop_loss"


def test_period_end_limit_down_locked_position_stays_open():
    hist_map = {
        "A": _hist(
            [
                ("2026-01-01", 10, 10, 10, 10),
                ("2026-01-02", 10, 10, 10, 10),
                ("2026-01-03", 8, 8, 8, 8),
            ]
        )
    }

    trades, nav = replay_portfolio(
        hist_map,
        [_candidate("A", "2026-01-01", "2026-01-02")],
        [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)],
        4,
        -8,
        -5,
    )

    assert trades == []
    assert nav[-1]["positions"] == 1
