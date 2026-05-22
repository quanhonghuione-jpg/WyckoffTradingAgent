#!/usr/bin/env python3
"""A-share L4 + ABC portfolio replay backtest."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

import pandas as pd

if __name__ == "__main__" or not __package__:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.funnel_pipeline import analyze_benchmark_and_tune_cfg, calc_market_breadth
from core.signal_confirmation import score_springboard_abc
from core.wyckoff_engine import FunnelConfig, run_funnel
from scripts.backtest_runner import (
    _apply_funnel_cfg_overrides,
    _board_match,
    _build_daily_ohlc_lookup,
    _load_snapshot_benchmark,
    _load_snapshot_hist_map,
    _load_snapshot_market_cap_map,
    _load_snapshot_name_map,
    _load_snapshot_sector_map,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignalCandidate:
    signal_date: date
    entry_date: date
    code: str
    name: str
    trigger: str
    score: float
    abc_grade: str
    abc_count: int
    regime: str
    track: str


@dataclass
class OpenPosition:
    code: str
    name: str
    signal_date: date
    entry_date: date
    entry_price: float
    shares: float
    trigger: str
    score: float
    abc_grade: str
    peak_close: float
    had_profit_run: bool = False


@dataclass(frozen=True)
class ReplayTrade:
    signal_date: str
    entry_date: str
    exit_date: str
    code: str
    name: str
    trigger: str
    abc_grade: str
    score: float
    entry_price: float
    exit_price: float
    ret_pct: float
    exit_reason: str


@dataclass(frozen=True)
class SnapshotContext:
    hist_map: dict[str, pd.DataFrame]
    bench_df: pd.DataFrame
    name_map: dict[str, str]
    sector_map: dict[str, str]
    market_cap_map: dict[str, float]
    rows_total: int


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(val) or math.isinf(val) else val


def _load_context(snapshot_dir: Path, board: str) -> SnapshotContext:
    name_map = _load_snapshot_name_map(snapshot_dir) or {}
    symbols = {code for code in name_map if _board_match(code, board) and "ST" not in name_map.get(code, "").upper()}
    hist_map, rows_total = _load_snapshot_hist_map(snapshot_dir, symbols_filter=symbols)
    bench_df = _load_snapshot_benchmark(snapshot_dir)
    if bench_df is None or bench_df.empty:
        raise RuntimeError(f"snapshot missing benchmark_main.csv: {snapshot_dir}")
    sector_map = _load_snapshot_sector_map(snapshot_dir) or {}
    market_cap_map = _load_snapshot_market_cap_map(snapshot_dir) or {}
    return SnapshotContext(hist_map, bench_df, name_map, sector_map, market_cap_map, rows_total)


def _trade_calendar(bench_df: pd.DataFrame, start: date, end: date) -> list[date]:
    dates = [d for d in bench_df["date"].tolist() if start <= d <= end]
    if len(dates) < 3:
        raise RuntimeError(f"回测区间交易日过少: {len(dates)}")
    return dates


def _day_df_map(
    hist_map: dict[str, pd.DataFrame], signal_date: date, trading_days: int, ma_long: int
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for code, df in hist_map.items():
        sliced = df[df["date"] <= signal_date].tail(trading_days)
        if len(sliced) >= ma_long:
            out[code] = sliced
    return out


def _day_cfg(
    base_cfg: FunnelConfig, day_df_map: dict[str, pd.DataFrame], bench_slice: pd.DataFrame
) -> tuple[FunnelConfig, str]:
    from dataclasses import replace

    cfg = replace(base_cfg)
    breadth = calc_market_breadth(day_df_map)
    context = analyze_benchmark_and_tune_cfg(bench_slice, None, cfg, breadth=breadth)
    return cfg, str(context.get("regime", "NEUTRAL") if context else "NEUTRAL")


def _track_for_triggers(triggers: list[str]) -> str:
    trend_keys = {"sos", "evr", "compression"}
    accum_keys = {"spring", "lps"}
    has_trend = bool(trend_keys.intersection(triggers))
    has_accum = bool(accum_keys.intersection(triggers))
    if has_trend and has_accum:
        return "Mixed"
    return "Trend" if has_trend else "Accum"


def _abc_best(df: pd.DataFrame, triggers: list[str]) -> tuple[str, int]:
    best_grade = "none"
    best_count = 0
    for trigger in triggers:
        abc = score_springboard_abc(df, trigger)
        count = int(abc.get("met_count", 0) or 0)
        if count > best_count:
            best_count = count
            best_grade = str(abc.get("grade", "none") or "none")
    return best_grade, best_count


def _extract_l4_abc_candidates(
    result: Any,
    day_df_map: dict[str, pd.DataFrame],
    name_map: dict[str, str],
    signal_date: date,
    entry_date: date,
    regime: str,
) -> list[SignalCandidate]:
    bucket: dict[str, dict[str, Any]] = {}
    for trigger, pairs in result.triggers.items():
        for raw_code, raw_score in pairs:
            code = str(raw_code).strip()
            if code not in day_df_map:
                continue
            item = bucket.setdefault(code, {"triggers": [], "score": 0.0})
            item["triggers"].append(str(trigger))
            item["score"] = max(float(item["score"]), _safe_float(raw_score))

    candidates = [
        _candidate_from_bucket(code, item, day_df_map, name_map, signal_date, entry_date, regime)
        for code, item in bucket.items()
    ]
    return sorted([c for c in candidates if c is not None], key=lambda x: (-x.score, -x.abc_count, x.code))


def _candidate_from_bucket(
    code: str,
    item: dict[str, Any],
    day_df_map: dict[str, pd.DataFrame],
    name_map: dict[str, str],
    signal_date: date,
    entry_date: date,
    regime: str,
) -> SignalCandidate | None:
    triggers = list(dict.fromkeys(item["triggers"]))
    abc_grade, abc_count = _abc_best(day_df_map[code], triggers)
    if abc_count < 2:
        return None
    return SignalCandidate(
        signal_date=signal_date,
        entry_date=entry_date,
        code=code,
        name=name_map.get(code, code),
        trigger="+".join(triggers),
        score=round(float(item["score"]), 4),
        abc_grade=abc_grade,
        abc_count=abc_count,
        regime=regime,
        track=_track_for_triggers(triggers),
    )


def generate_candidates(
    ctx: SnapshotContext,
    start: date,
    end: date,
    trading_days: int,
    daily_cap: int,
) -> tuple[list[SignalCandidate], dict[str, int]]:
    base_cfg = FunnelConfig(trading_days=trading_days)
    _apply_funnel_cfg_overrides(base_cfg)
    calendar = _trade_calendar(ctx.bench_df, start, end)
    next_day = {d: calendar[idx + 1] for idx, d in enumerate(calendar[:-1])}
    stats = {"eval_days": 0, "raw_l4_hits": 0}
    all_candidates: list[SignalCandidate] = []
    for signal_date in calendar[:-1]:
        day_map = _day_df_map(ctx.hist_map, signal_date, trading_days, base_cfg.ma_long)
        bench_slice = ctx.bench_df[ctx.bench_df["date"] <= signal_date].tail(trading_days)
        if not day_map or len(bench_slice) < base_cfg.ma_long:
            continue
        day_cfg, regime = _day_cfg(base_cfg, day_map, bench_slice)
        result = run_funnel(
            list(day_map), day_map, bench_slice, ctx.name_map, ctx.market_cap_map, ctx.sector_map, day_cfg
        )
        stats["eval_days"] += 1
        stats["raw_l4_hits"] += len({c for pairs in result.triggers.values() for c, _ in pairs})
        day_candidates = _extract_l4_abc_candidates(
            result, day_map, ctx.name_map, signal_date, next_day[signal_date], regime
        )
        all_candidates.extend(day_candidates[:daily_cap] if daily_cap > 0 else day_candidates)
    return all_candidates, stats


def _row_on(df: pd.DataFrame, day: date) -> pd.Series | None:
    rows = df[df["date"] == day]
    return None if rows.empty else rows.iloc[-1]


def _entry_price(df: pd.DataFrame, entry_date: date) -> float | None:
    row = _row_on(df, entry_date)
    if row is None or _entry_limit_up_locked(df, entry_date, row):
        return None
    px = _safe_float(row.get("open"))
    return px if px > 0 else None


def _entry_limit_up_locked(df: pd.DataFrame, entry_date: date, row: pd.Series) -> bool:
    prev = df[df["date"] < entry_date].tail(1)
    if prev.empty:
        return False
    prev_close = _safe_float(prev.iloc[-1].get("close"))
    open_px = _safe_float(row.get("open"))
    high = _safe_float(row.get("high"))
    low = _safe_float(row.get("low"))
    close = _safe_float(row.get("close"))
    return (
        open_px > 0
        and close > prev_close
        and abs(open_px - high) <= open_px * 1e-6
        and abs(open_px - low) <= open_px * 1e-6
    )


def _daily_pct(row: pd.Series, prev_close: float) -> float:
    if "pct_chg" in row and pd.notna(row.get("pct_chg")):
        return _safe_float(row.get("pct_chg"))
    close = _safe_float(row.get("close"))
    return (close / prev_close - 1.0) * 100.0 if prev_close > 0 and close > 0 else 0.0


def _limit_down_locked(row: pd.Series, prev_close: float) -> bool:
    open_px = _safe_float(row.get("open"))
    high = _safe_float(row.get("high"))
    low = _safe_float(row.get("low"))
    return (
        open_px > 0
        and abs(open_px - high) <= open_px * 1e-6
        and abs(open_px - low) <= open_px * 1e-6
        and open_px < prev_close
    )


def _exit_position(
    pos: OpenPosition,
    row: pd.Series,
    day: date,
    prev_close: float,
    stop_loss_pct: float,
    profit_drop_pct: float,
) -> tuple[ReplayTrade, float] | None:
    open_px = _safe_float(row.get("open"))
    low = _safe_float(row.get("low"))
    close = _safe_float(row.get("close"))
    if _limit_down_locked(row, prev_close):
        return None
    stop_px = pos.entry_price * (1.0 + stop_loss_pct / 100.0)
    if low > 0 and low <= stop_px:
        return _trade(pos, day, open_px if open_px <= stop_px else stop_px, "stop_loss")
    if pos.had_profit_run and _daily_pct(row, prev_close) <= profit_drop_pct:
        return _trade(pos, day, close, "profit_drop")
    pos.peak_close = max(pos.peak_close, close)
    pos.had_profit_run = pos.had_profit_run or pos.peak_close > pos.entry_price
    return None


def _trade(pos: OpenPosition, exit_date: date, exit_price: float, reason: str) -> tuple[ReplayTrade, float]:
    proceeds = pos.shares * exit_price
    ret_pct = (exit_price / pos.entry_price - 1.0) * 100.0 if pos.entry_price > 0 else 0.0
    trade = ReplayTrade(
        signal_date=pos.signal_date.isoformat(),
        entry_date=pos.entry_date.isoformat(),
        exit_date=exit_date.isoformat(),
        code=pos.code,
        name=pos.name,
        trigger=pos.trigger,
        abc_grade=pos.abc_grade,
        score=pos.score,
        entry_price=round(pos.entry_price, 4),
        exit_price=round(exit_price, 4),
        ret_pct=round(ret_pct, 4),
        exit_reason=reason,
    )
    return trade, proceeds


def _open_new_positions(
    candidates: list[SignalCandidate],
    hist_map: dict[str, pd.DataFrame],
    positions: list[OpenPosition],
    cash: float,
    nav: float,
    max_positions: int,
) -> tuple[list[OpenPosition], float]:
    held = {p.code for p in positions}
    slots = max_positions - len(positions)
    ranked = sorted(candidates, key=lambda x: (-x.score, -x.abc_count, x.code))
    for cand in ranked:
        if slots <= 0 or cand.code in held:
            continue
        entry_px = _entry_price(hist_map[cand.code], cand.entry_date)
        if entry_px is None:
            continue
        capital = min(cash, nav / max_positions)
        if capital <= 0:
            break
        positions.append(_position_from_candidate(cand, entry_px, capital))
        cash -= capital
        held.add(cand.code)
        slots -= 1
    return positions, cash


def _position_from_candidate(cand: SignalCandidate, entry_px: float, capital: float) -> OpenPosition:
    return OpenPosition(
        code=cand.code,
        name=cand.name,
        signal_date=cand.signal_date,
        entry_date=cand.entry_date,
        entry_price=entry_px,
        shares=capital / entry_px,
        trigger=cand.trigger,
        score=cand.score,
        abc_grade=cand.abc_grade,
        peak_close=entry_px,
    )


def _close_positions(
    positions: list[OpenPosition],
    hist_map: dict[str, pd.DataFrame],
    day: date,
    cash: float,
) -> tuple[list[ReplayTrade], float]:
    trades: list[ReplayTrade] = []
    for pos in positions:
        df = hist_map[pos.code]
        row = _row_on(df, day)
        prev = df[df["date"] < day].tail(1)
        prev_close = _safe_float(prev.iloc[-1].get("close")) if not prev.empty else pos.entry_price
        if row is not None and _limit_down_locked(row, prev_close):
            continue
        px = _safe_float(row.get("close")) if row is not None else pos.peak_close
        trade, proceeds = _trade(pos, day, px, "period_end")
        trades.append(trade)
        cash += proceeds
    return trades, cash


def _mark_nav(
    hist_map: dict[str, pd.DataFrame],
    positions: list[OpenPosition],
    cash: float,
    day: date,
) -> float:
    value = cash
    for pos in positions:
        row = _row_on(hist_map[pos.code], day)
        px = _safe_float(row.get("close")) if row is not None else pos.peak_close
        value += pos.shares * px
    return value


def replay_portfolio(
    hist_map: dict[str, pd.DataFrame],
    candidates: list[SignalCandidate],
    calendar: list[date],
    max_positions: int,
    stop_loss_pct: float,
    profit_drop_pct: float,
) -> tuple[list[ReplayTrade], list[dict[str, Any]]]:
    by_entry: dict[date, list[SignalCandidate]] = {}
    for cand in candidates:
        by_entry.setdefault(cand.entry_date, []).append(cand)
    cash = 1.0
    positions: list[OpenPosition] = []
    trades: list[ReplayTrade] = []
    nav_rows: list[dict[str, Any]] = []
    prev_nav = 1.0
    ohlc_cache = {code: _build_daily_ohlc_lookup(df) for code, df in hist_map.items()}
    for day in calendar:
        positions, cash = _open_new_positions(by_entry.get(day, []), hist_map, positions, cash, prev_nav, max_positions)
        positions, cash, closed = _evaluate_day_exits(positions, ohlc_cache, day, cash, stop_loss_pct, profit_drop_pct)
        trades.extend(closed)
        prev_nav = _mark_nav(hist_map, positions, cash, day)
        nav_rows.append(
            {"date": day.isoformat(), "nav": round(prev_nav, 8), "cash": round(cash, 8), "positions": len(positions)}
        )
    final_trades, cash = _close_positions(positions, hist_map, calendar[-1], cash)
    trades.extend(final_trades)
    return trades, nav_rows


def _evaluate_day_exits(
    positions: list[OpenPosition],
    ohlc_cache: dict[str, dict[date, tuple[float, float, float, float]]],
    day: date,
    cash: float,
    stop_loss_pct: float,
    profit_drop_pct: float,
) -> tuple[list[OpenPosition], float, list[ReplayTrade]]:
    kept: list[OpenPosition] = []
    closed: list[ReplayTrade] = []
    for pos in positions:
        lookup = ohlc_cache.get(pos.code, {})
        candle = lookup.get(day)
        prev_close = _prev_close(lookup, day, pos.entry_price)
        if candle is None:
            kept.append(pos)
            continue
        if pos.entry_date >= day:
            close = candle[3]
            pos.peak_close = max(pos.peak_close, close)
            pos.had_profit_run = pos.had_profit_run or pos.peak_close > pos.entry_price
            kept.append(pos)
            continue
        row = pd.Series({"open": candle[0], "high": candle[1], "low": candle[2], "close": candle[3]})
        result = _exit_position(pos, row, day, prev_close, stop_loss_pct, profit_drop_pct)
        if result is None:
            kept.append(pos)
        else:
            trade, proceeds = result
            cash += proceeds
            closed.append(trade)
    return kept, cash, closed


def _prev_close(lookup: dict[date, tuple[float, float, float, float]], day: date, default: float) -> float:
    prev_days = [d for d in lookup if d < day]
    if not prev_days:
        return default
    return lookup[max(prev_days)][3]


def _max_drawdown(nav_values: list[float]) -> float | None:
    if not nav_values:
        return None
    peak = nav_values[0]
    mdd = 0.0
    for nav in nav_values:
        peak = max(peak, nav)
        mdd = min(mdd, nav / peak - 1.0 if peak > 0 else 0.0)
    return mdd * 100.0


def _summary(
    trades: list[ReplayTrade],
    nav_rows: list[dict[str, Any]],
    candidates: list[SignalCandidate],
    args: argparse.Namespace,
    stats: dict[str, int],
    ctx: SnapshotContext,
) -> dict[str, Any]:
    returns = [t.ret_pct for t in trades]
    nav_values = [float(x["nav"]) for x in nav_rows]
    std = stdev(returns) if len(returns) > 1 else 0.0
    return {
        "source": "ashare_l4_abc_portfolio_replay",
        "strategy_id": "l4_abc2_next_open_sl8_drop5_max4",
        "strategy_desc": "正式L4且A/B/C至少满足2项，次日开盘买入，-8%止损，盈利段单日跌幅超过5%卖出，最多4仓位",
        "period_key": args.period_key,
        "period_label": args.period_label,
        "start": args.start,
        "end": args.end,
        "board": args.board,
        "max_positions": int(args.max_positions),
        "daily_candidate_cap": int(args.daily_candidate_cap),
        "stop_loss_pct": float(args.stop_loss_pct),
        "profit_drop_pct": float(args.profit_drop_pct),
        "trading_days": int(args.trading_days),
        "universe_ok": len(ctx.hist_map),
        "snapshot_rows_total": ctx.rows_total,
        "eval_days": stats.get("eval_days", 0),
        "raw_l4_hits": stats.get("raw_l4_hits", 0),
        "signal_candidates": len(candidates),
        "trades": len(trades),
        "win_rate_pct": sum(1 for r in returns if r > 0) / len(returns) * 100.0 if returns else None,
        "avg_ret_pct": mean(returns) if returns else None,
        "median_ret_pct": median(returns) if returns else None,
        "sharpe_ratio": mean(returns) / std if std > 0 else None,
        "max_drawdown_pct": _max_drawdown(nav_values),
        "portfolio_total_ret_pct": (nav_values[-1] - 1.0) * 100.0 if nav_values else None,
        "exit_counts": _exit_counts(trades),
    }


def _exit_counts(trades: list[ReplayTrade]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for trade in trades:
        counts[trade.exit_reason] = counts.get(trade.exit_reason, 0) + 1
    return counts


def _write_outputs(
    out_dir: Path,
    summary: dict[str, Any],
    candidates: list[SignalCandidate],
    trades: list[ReplayTrade],
    nav_rows: list[dict[str, Any]],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(out_dir / "signals.csv", [asdict(c) for c in candidates])
    _write_csv(out_dir / "trades.csv", [asdict(t) for t in trades])
    _write_csv(out_dir / "nav.csv", nav_rows)
    (out_dir / f"summary_{summary['period_key']}.md").write_text(_summary_md(summary), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _summary_md(summary: dict[str, Any]) -> str:
    def fmt(v: Any, spec: str = ".2f") -> str:
        return "-" if v is None else format(float(v), spec)

    return "\n".join(
        [
            "# A股 L4+ABC 组合回测",
            f"- 区间: {summary['period_label']} ({summary['start']} ~ {summary['end']})",
            f"- 策略: {summary['strategy_desc']}",
            f"- 信号候选: {summary['signal_candidates']}",
            f"- 成交样本: {summary['trades']}",
            f"- 胜率: {fmt(summary['win_rate_pct'], '.1f')}%",
            f"- 平均收益: {fmt(summary['avg_ret_pct'], '+.2f')}%",
            f"- 夏普比: {fmt(summary['sharpe_ratio'], '.3f')}",
            f"- 最大回撤: {fmt(summary['max_drawdown_pct'], '+.2f')}%",
            f"- 组合收益: {fmt(summary['portfolio_total_ret_pct'], '+.2f')}%",
        ]
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay A-share L4 + ABC portfolio strategy.")
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--period-key", required=True)
    parser.add_argument("--period-label", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--board", default="main_chinext")
    parser.add_argument("--trading-days", type=int, default=320)
    parser.add_argument("--daily-candidate-cap", type=int, default=0)
    parser.add_argument("--max-positions", type=int, default=4)
    parser.add_argument("--stop-loss-pct", type=float, default=-8.0)
    parser.add_argument("--profit-drop-pct", type=float, default=-5.0)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = _parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    ctx = _load_context(Path(args.snapshot_dir), args.board)
    calendar = _trade_calendar(ctx.bench_df, start, end)
    candidates, stats = generate_candidates(ctx, start, end, args.trading_days, args.daily_candidate_cap)
    trades, nav_rows = replay_portfolio(
        ctx.hist_map, candidates, calendar, args.max_positions, args.stop_loss_pct, args.profit_drop_pct
    )
    summary = _summary(trades, nav_rows, candidates, args, stats, ctx)
    _write_outputs(Path(args.output_dir), summary, candidates, trades, nav_rows)
    logger.info("A股L4+ABC回测完成: period=%s, candidates=%d, trades=%d", args.period_key, len(candidates), len(trades))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
