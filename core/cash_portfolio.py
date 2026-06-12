"""Cash-account portfolio simulation for backtest trades."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CashPortfolioConfig:
    initial_cash: float = 100_000.0
    max_positions: int = 4
    commission_rate: float = 0.0002
    small_trade_threshold: float = 10_000.0
    small_trade_fee: float = 5.0
    lot_size: int = 100


def calc_commission(amount: float, config: CashPortfolioConfig) -> float:
    gross = max(float(amount), 0.0)
    if gross <= 0:
        return 0.0
    if gross < float(config.small_trade_threshold):
        return float(config.small_trade_fee)
    return gross * float(config.commission_rate)


def _portfolio_equity(cash: float, active: list[dict[str, Any]]) -> float:
    return float(cash) + sum(float(pos["shares"]) * float(pos["entry_price"]) for pos in active)


def _shares_for_budget(price: float, cash: float, budget: float, config: CashPortfolioConfig) -> int:
    lot_size = max(int(config.lot_size), 1)
    usable = max(min(float(cash), float(budget)), 0.0)
    shares = int(usable // (float(price) * lot_size)) * lot_size
    while shares > 0:
        gross = shares * float(price)
        if gross + calc_commission(gross, config) <= usable:
            return shares
        shares -= lot_size
    return 0


def _normalize_trade_dates(trades_df: pd.DataFrame) -> pd.DataFrame:
    required_cols = {"entry_date", "exit_date", "entry_close", "exit_close"}
    if trades_df is None or trades_df.empty or not required_cols.issubset(trades_df.columns):
        return pd.DataFrame()
    df = trades_df.copy()
    for col in ("signal_date", "entry_date", "exit_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df["entry_close"] = pd.to_numeric(df.get("entry_close"), errors="coerce")
    df["exit_close"] = pd.to_numeric(df.get("exit_close"), errors="coerce")
    return df.dropna(subset=["entry_date", "exit_date", "entry_close", "exit_close"]).reset_index(drop=True)


def _numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _close_due_positions(
    active: list[dict[str, Any]],
    cash: float,
    day: date,
    config: CashPortfolioConfig,
    closed_rows: list[dict[str, Any]],
) -> float:
    keep: list[dict[str, Any]] = []
    for pos in active:
        if pos["exit_date"] > day:
            keep.append(pos)
            continue
        sell_gross = float(pos["shares"]) * float(pos["exit_price"])
        sell_fee = calc_commission(sell_gross, config)
        sell_net = sell_gross - sell_fee
        pnl = sell_net - float(pos["cost_total"])
        cash += sell_net
        closed_rows.append({**pos, "sell_fee": sell_fee, "pnl": pnl, "ret_pct": pnl / pos["cost_total"] * 100.0})
    active[:] = keep
    return cash


def _try_open_position(
    row: pd.Series,
    cash: float,
    active: list[dict[str, Any]],
    config: CashPortfolioConfig,
) -> tuple[float, bool]:
    price = float(row["entry_close"])
    if price <= 0 or cash <= 0:
        return cash, False
    slot_budget = _portfolio_equity(cash, active) / max(int(config.max_positions), 1)
    shares = _shares_for_budget(price, cash, slot_budget, config)
    if shares <= 0:
        return cash, False
    buy_gross = shares * price
    buy_fee = calc_commission(buy_gross, config)
    active.append(
        {
            "code": str(row.get("code", "")).strip(),
            "name": str(row.get("name", "") or row.get("code", "")).strip(),
            "signal_date": row.get("signal_date"),
            "entry_date": row["entry_date"],
            "exit_date": row["exit_date"],
            "entry_price": price,
            "exit_price": float(row["exit_close"]),
            "shares": shares,
            "buy_gross": buy_gross,
            "buy_fee": buy_fee,
            "cost_total": buy_gross + buy_fee,
        }
    )
    return cash - buy_gross - buy_fee, True


def _portfolio_summary(
    closed_df: pd.DataFrame,
    cash: float,
    config: CashPortfolioConfig,
    skipped: dict[str, int],
) -> dict[str, Any]:
    ret = _numeric_column(closed_df, "ret_pct").dropna()
    wins = ret[ret > 0]
    losses = ret[ret < 0]
    return {
        "cash_portfolio_initial_cash": float(config.initial_cash),
        "cash_portfolio_final_cash": float(cash),
        "cash_portfolio_total_return_pct": (float(cash) / float(config.initial_cash) - 1.0) * 100.0,
        "cash_portfolio_trades": int(len(ret)),
        "cash_portfolio_win_rate_pct": float((ret > 0).mean() * 100.0) if len(ret) else None,
        "cash_portfolio_avg_profit_pct": float(wins.mean()) if len(wins) else None,
        "cash_portfolio_avg_loss_pct": float(losses.mean()) if len(losses) else None,
        "cash_portfolio_commission_total": float(_numeric_column(closed_df, "buy_fee").sum())
        + float(_numeric_column(closed_df, "sell_fee").sum()),
        "cash_portfolio_skipped_full": int(skipped.get("full", 0)),
        "cash_portfolio_skipped_cash": int(skipped.get("cash", 0)),
        "cash_portfolio_max_positions": int(config.max_positions),
    }


def simulate_cash_portfolio(
    trades_df: pd.DataFrame,
    config: CashPortfolioConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    cfg = config or CashPortfolioConfig()
    df = _normalize_trade_dates(trades_df)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), _portfolio_summary(pd.DataFrame(), cfg.initial_cash, cfg, {})

    cash = float(cfg.initial_cash)
    active: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    skipped = {"full": 0, "cash": 0}

    ordered = df.assign(_order=range(len(df))).sort_values(["entry_date", "_order"])
    for _, row in ordered.iterrows():
        day = row["entry_date"]
        cash = _close_due_positions(active, cash, day, cfg, closed)
        if len(active) >= max(int(cfg.max_positions), 1):
            skipped["full"] += 1
            continue
        if str(row.get("code", "")).strip() in {pos["code"] for pos in active}:
            skipped["full"] += 1
            continue
        cash, opened = _try_open_position(row, cash, active, cfg)
        skipped["cash"] += 0 if opened else 1
        equity_rows.append(
            {"date": day, "equity": _portfolio_equity(cash, active), "cash": cash, "positions": len(active)}
        )

    for day in sorted({pos["exit_date"] for pos in active}):
        cash = _close_due_positions(active, cash, day, cfg, closed)
        equity_rows.append(
            {"date": day, "equity": _portfolio_equity(cash, active), "cash": cash, "positions": len(active)}
        )

    closed_df = pd.DataFrame(closed)
    nav_df = pd.DataFrame(equity_rows)
    if not nav_df.empty:
        nav_df = nav_df.drop_duplicates(subset=["date"], keep="last")
    summary = _portfolio_summary(closed_df, cash, cfg, skipped)
    return closed_df, nav_df, summary
