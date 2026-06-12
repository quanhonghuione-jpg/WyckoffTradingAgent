from __future__ import annotations


def test_market_report_includes_cash_account_metrics(tmp_path):
    from scripts.update_backtest_market_report import build_report, load_grid_cells

    artifact = tmp_path / "backtest-grid-h5-sl-6-tp0-tr0-37"
    artifact.mkdir()
    (artifact / "summary_20211213_20221031_h5_n4.md").write_text(
        "\n".join(
            [
                "# Wyckoff Funnel Daily Backtest",
                "",
                "- 区间: 2021-12-13 ~ 2022-10-31",
                "- 持有周期: 5 交易日",
                "- 每日候选上限: Top 4",
                "- 股票池: main_chinext (sample=0)",
                "- 绩效引擎: auto（wbt 可用）",
                "- 成交样本: 249",
                "",
                "## 收益统计",
                "- 胜率: 29.32%",
                "- 平均收益: -1.520%",
                "- 中位收益: -5.984%",
                "",
                "## 组合风险指标（单利口径 · 基于每日净值曲线）",
                "- 夏普比 (Sharpe Ratio): -1.040",
                "- 卡玛比 (Calmar Ratio): -0.563",
                "- 最大回撤: -66.98%",
                "- 组合总收益: -32.16%",
                "",
                "## 真实现金账户模拟",
                "- 初始现金: 100000.00",
                "- 最终现金: 53785.51",
                "- 总收益: -46.21%",
                "- 成交笔数: 151",
                "- 佣金合计: 1011.52",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "trades_20211213_20221031_h5_n4.csv").write_text(
        "signal_date,ret_pct,regime,trigger\n2022-01-01,-1.2,NEUTRAL,lps\n",
        encoding="utf-8",
    )

    cells = load_grid_cells(tmp_path)
    assert cells[0].cash_initial == 100000.0
    assert cells[0].cash_final == 53785.51

    report = build_report(cells)

    assert "现金账户: 初始 **100000.00**；最终 **53785.51**；盈亏 **-46214.49**" in report
    assert "| 排名 | 参数组合 | 夏普 | 胜率 | 均收 | 回撤 | 最终现金 | 现金收益 | 样本 |" in report
