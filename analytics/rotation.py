"""板块相对强度 (RS) 计算 + 轮动排名"""

from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd

from data.etf_list import INDUSTRY_ETFS
from data.fetcher import fetch_etf_history, fetch_benchmark_history

_logger = logging.getLogger("etf.rotation")


def calc_return(df: pd.DataFrame, days: int) -> float:
    """计算 N 日涨幅（%），数据不足返回 NaN"""
    if len(df) < days + 1:
        return np.nan
    return (df["收盘"].iloc[-1] / df["收盘"].iloc[-1 - days] - 1) * 100


def _fetch_history_with_retry(code: str, max_days: int, retries: int = 2, delay: float = 2.0):
    """带重试的历史数据获取，返回 DataFrame 或 None"""
    for attempt in range(retries + 1):
        try:
            return fetch_etf_history(code, max_days)
        except Exception as e:
            if attempt < retries:
                _logger.warning(f"ETF {code} 历史数据获取失败 (第{attempt + 1}次)，{delay}s 后重试: {e}")
                time.sleep(delay)
            else:
                _logger.error(f"ETF {code} 历史数据获取最终失败 ({retries + 1}次尝试): {e}")
                return None


def compute_rs_matrix(periods: list[int] | None = None) -> tuple[pd.DataFrame, str | None]:
    """计算所有行业 ETF 的 RS 矩阵
    返回 (DataFrame, data_date): index=板块名, columns=[RS_5d, RS_10d, RS_20d, ...]
    data_date 为 K 线数据最后日期 (YYYY-MM-DD)
    """
    if periods is None:
        periods = [5, 10, 20]

    max_days = max(periods) + 10
    benchmark_df = fetch_benchmark_history(max_days)
    data_date = benchmark_df["日期"].iloc[-1].strftime("%Y-%m-%d") if not benchmark_df.empty else None
    benchmark_returns = {p: calc_return(benchmark_df, p) for p in periods}

    rows = []
    for name, code in INDUSTRY_ETFS.items():
        hist = _fetch_history_with_retry(code, max_days)
        if hist is None:
            # 即使获取失败也保留行，RS 值为 None
            row = {"sector": name}
            for p in periods:
                row[f"ret_{p}d"] = None
                row[f"RS_{p}d"] = None
            rows.append(row)
            continue

        row = {"sector": name}
        for p in periods:
            ret = calc_return(hist, p)
            bm_ret = benchmark_returns.get(p, np.nan)
            row[f"ret_{p}d"] = round(ret, 2) if not np.isnan(ret) else None
            if not np.isnan(ret) and not np.isnan(bm_ret) and bm_ret != 0:
                row[f"RS_{p}d"] = round(ret / bm_ret, 3)
            else:
                row[f"RS_{p}d"] = None
        rows.append(row)

    df = pd.DataFrame(rows).set_index("sector")

    # 排名（RS 越高排名越前，rank=1 最强）
    for p in periods:
        col = f"RS_{p}d"
        if col in df.columns:
            df[f"rank_{p}d"] = df[col].rank(ascending=False, method="min")

    return df, data_date


def compute_rotation_signal(rs_df: pd.DataFrame) -> pd.DataFrame:
    """根据排名变化判断轮动方向
    对比 5日排名 vs 20日排名：排名上升=资金流入，下降=流出
    """
    if "rank_5d" not in rs_df.columns or "rank_20d" not in rs_df.columns:
        return rs_df

    rs_df["rank_change"] = rs_df["rank_20d"] - rs_df["rank_5d"]
    rs_df["direction"] = rs_df["rank_change"].apply(
        lambda x: "↑ 流入" if x >= 3 else ("↓ 流出" if x <= -3 else "→ 持平")
    )
    return rs_df
