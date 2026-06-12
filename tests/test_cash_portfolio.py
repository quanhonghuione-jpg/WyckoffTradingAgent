from __future__ import annotations

import pandas as pd

from core.cash_portfolio import CashPortfolioConfig, calc_commission, simulate_cash_portfolio


def test_commission_uses_small_trade_fee() -> None:
    cfg = CashPortfolioConfig(
        commission_rate=0.0002,
        small_trade_threshold=10_000,
        small_trade_fee=5,
    )

    assert calc_commission(5_000, cfg) == 5.0
    assert calc_commission(10_000, cfg) == 2.0
    assert calc_commission(100_000, cfg) == 20.0


def test_cash_portfolio_limits_positions_and_lot_size() -> None:
    rows = []
    for idx in range(5):
        rows.append(
            {
                "code": f"00000{idx}",
                "name": f"S{idx}",
                "signal_date": "2026-01-02",
                "entry_date": "2026-01-05",
                "exit_date": "2026-01-10",
                "entry_close": 10.0,
                "exit_close": 11.0,
            }
        )

    closed, nav, summary = simulate_cash_portfolio(
        pd.DataFrame(rows),
        CashPortfolioConfig(
            initial_cash=100_000,
            max_positions=4,
            commission_rate=0.0002,
            small_trade_threshold=10_000,
            small_trade_fee=5,
            lot_size=100,
        ),
    )

    assert len(closed) == 4
    assert set(closed["shares"]) == {2400}
    assert summary["cash_portfolio_skipped_full"] == 1
    assert summary["cash_portfolio_win_rate_pct"] == 100.0
    assert summary["cash_portfolio_final_cash"] > 109_000
    assert not nav.empty


def test_cash_portfolio_accepts_empty_trade_frame() -> None:
    closed, nav, summary = simulate_cash_portfolio(pd.DataFrame(), CashPortfolioConfig(initial_cash=100_000))

    assert closed.empty
    assert nav.empty
    assert summary["cash_portfolio_final_cash"] == 100_000
    assert summary["cash_portfolio_trades"] == 0
