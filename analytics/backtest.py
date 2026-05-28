"""简单动量轮动策略回测引擎"""

from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from data.etf_list import INDUSTRY_ETFS, RS_BENCHMARK
from data.fetcher import fetch_etf_history


@dataclass
class Trade:
    date: str
    action: str          # "buy" | "sell"
    sectors: list[str]


@dataclass
class BacktestResult:
    nav: list[float]
    dates: list[str]
    benchmark_nav: list[float]
    trades: list[dict]
    metrics: dict


def _calc_period_return(hist: pd.DataFrame, end_idx: int, period: int) -> float:
    """计算 hist 在 end_idx 往前 period 天的涨幅"""
    start_idx = end_idx - period
    if start_idx < 0:
        return np.nan
    start_price = float(hist["收盘"].iloc[start_idx])
    end_price = float(hist["收盘"].iloc[end_idx])
    if start_price == 0:
        return np.nan
    return (end_price / start_price - 1) * 100


def run_backtest(
    period_days: int = 20,
    hold_days: int = 5,
    top_n: int = 5,
) -> BacktestResult:
    """运行动量轮动回测
    - period_days: 信号计算周期（过去N日涨幅排名）
    - hold_days: 每次调仓持有天数
    - top_n: 持有排名前N的板块
    """
    max_days = max(period_days, hold_days) + 250  # 约1年数据

    # 并行拉取历史数据
    all_hist = {}
    bench_hist = pd.DataFrame()

    def _fetch_one(name, code):
        try:
            return name, fetch_etf_history(code, max_days)
        except Exception:
            return name, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_one, name, code): name
                   for name, code in INDUSTRY_ETFS.items()}
        futures[pool.submit(_fetch_one, "__benchmark__", RS_BENCHMARK)] = "__benchmark__"
        for fut in as_completed(futures):
            name, df = fut.result()
            if df is not None:
                if name == "__benchmark__":
                    bench_hist = df
                else:
                    all_hist[name] = df

    if len(all_hist) < 5 or bench_hist.empty:
        return BacktestResult(nav=[], dates=[], benchmark_nav=[], trades=[], metrics={})

    # 对齐日期：取所有 ETF 都有数据的日期
    all_dates = None
    for hist in all_hist.values():
        dates = set(hist["日期"].dt.date)
        all_dates = dates if all_dates is None else all_dates & dates
    all_dates = sorted(all_dates)

    if len(all_dates) < period_days + 10:
        return BacktestResult(nav=[], dates=[], benchmark_nav=[], trades=[], metrics={})

    # 为每个 ETF 建立日期->index 的映射
    hist_idx = {}
    for name, hist in all_hist.items():
        hist_idx[name] = {d: i for i, d in enumerate(hist["日期"].dt.date)}

    bench_idx = {d: i for i, d in enumerate(bench_hist["日期"].dt.date)}

    # 回测
    nav = 1.0
    bench_nav = 1.0
    nav_curve = [1.0]
    bench_curve = [1.0]
    dates_out = [str(all_dates[0])]
    trades = []
    holding = []

    i = 0
    while i < len(all_dates):
        today = all_dates[i]

        # 调仓日：计算排名，选 Top-N
        if i % hold_days == 0 and i >= period_days:
            scores = {}
            for name in all_hist:
                idx = hist_idx[name].get(today)
                if idx is None or idx < period_days:
                    continue
                ret = _calc_period_return(all_hist[name], idx, period_days)
                if not np.isnan(ret):
                    scores[name] = ret

            sorted_sectors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            new_holding = [s[0] for s in sorted_sectors[:top_n]]

            # 记录换仓
            sold = [s for s in holding if s not in new_holding]
            bought = [s for s in new_holding if s not in holding]
            if sold or bought:
                trades.append({
                    "date": str(today),
                    "sold": sold,
                    "bought": bought,
                    "holding": new_holding,
                })
            holding = new_holding

        # 计算当日组合收益
        if holding and i > 0:
            prev_date = all_dates[i - 1]
            daily_returns = []
            for name in holding:
                if name not in hist_idx:
                    continue
                curr_idx = hist_idx[name].get(today)
                prev_idx = hist_idx[name].get(prev_date)
                if curr_idx is None or prev_idx is None:
                    continue
                curr_p = float(all_hist[name]["收盘"].iloc[curr_idx])
                prev_p = float(all_hist[name]["收盘"].iloc[prev_idx])
                if prev_p > 0:
                    daily_returns.append(curr_p / prev_p - 1)

            if daily_returns:
                avg_ret = np.mean(daily_returns)
                nav *= (1 + avg_ret)

        # 基准收益
        if i > 0:
            prev_date = all_dates[i - 1]
            b_curr = bench_idx.get(today)
            b_prev = bench_idx.get(prev_date)
            if b_curr is not None and b_prev is not None:
                bc = float(bench_hist["收盘"].iloc[b_curr])
                bp = float(bench_hist["收盘"].iloc[b_prev])
                if bp > 0:
                    bench_nav *= (bc / bp)

        nav_curve.append(nav)
        bench_curve.append(bench_nav)
        dates_out.append(str(today))
        i += 1

    # 绩效指标
    nav_arr = np.array(nav_curve)
    returns = np.diff(nav_arr) / nav_arr[:-1]
    total_return = (nav_arr[-1] / nav_arr[0] - 1) * 100 if len(nav_arr) > 1 else 0

    # 最大回撤
    peak = np.maximum.accumulate(nav_arr)
    drawdown = (nav_arr - peak) / peak
    max_drawdown = float(drawdown.min()) * 100

    # 年化收益（按交易日252天）
    trading_days = len(nav_curve) - 1
    annual_return = ((nav_arr[-1] / nav_arr[0]) ** (252 / max(trading_days, 1)) - 1) * 100 if trading_days > 0 else 0

    # Sharpe ratio（无风险利率按2%年化）
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = (np.mean(returns) * 252 - 0.02) / (np.std(returns) * np.sqrt(252))
    else:
        sharpe = 0

    metrics = {
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe": round(float(sharpe), 3),
        "trade_count": len(trades),
        "trading_days": trading_days,
        "benchmark_return": round((bench_curve[-1] / bench_curve[0] - 1) * 100, 2) if len(bench_curve) > 1 else 0,
    }

    return BacktestResult(
        nav=nav_curve,
        dates=dates_out,
        benchmark_nav=bench_curve,
        trades=trades,
        metrics=metrics,
    )
