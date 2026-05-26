"""AKShare 数据获取层 — 双层缓存（磁盘 + Streamlit 内存）"""

import contextlib
import datetime
import json
import os
import pathlib
import time

import akshare as ak
import pandas as pd
import requests
import streamlit as st

from data.etf_list import INDUSTRY_ETFS, CODE_TO_NAME, BENCHMARK_ETFS

# AKShare 访问国内站点，全局绕过代理
os.environ["NO_PROXY"] = "*"
for _k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(_k, None)

requests.utils.getproxies = lambda *_, **__: {}

# 磁盘缓存目录
_CACHE_DIR = pathlib.Path(__file__).parent.parent / ".cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _read_disk_cache(key: str, ttl_seconds: int):
    """读磁盘缓存，过期返回 None"""
    fp = _CACHE_DIR / f"{key}.parquet"
    meta_fp = _CACHE_DIR / f"{key}.meta.json"
    if not fp.exists() or not meta_fp.exists():
        return None
    try:
        meta = json.loads(meta_fp.read_text())
        if time.time() - meta["ts"] > ttl_seconds:
            return None
        return pd.read_parquet(fp)
    except Exception:
        return None


def _write_disk_cache(key: str, df: pd.DataFrame):
    """写磁盘缓存"""
    fp = _CACHE_DIR / f"{key}.parquet"
    meta_fp = _CACHE_DIR / f"{key}.meta.json"
    df.to_parquet(fp, index=False)
    meta_fp.write_text(json.dumps({"ts": time.time()}))


def _cached_fetch(key: str, ttl_seconds: int, fetch_fn):
    """双层缓存：磁盘 → Streamlit 内存 → 远程"""
    # 1. 磁盘缓存
    disk_df = _read_disk_cache(key, ttl_seconds)
    if disk_df is not None:
        return disk_df

    # 2. 远程获取
    df = fetch_fn()

    # 3. 写入磁盘
    _write_disk_cache(key, df)
    return df


# ---- 实时行情（TTL 5min）----

@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_quotes() -> pd.DataFrame:
    """获取全市场 ETF 实时行情"""
    return _cached_fetch("etf_quotes_all", 300, ak.fund_etf_spot_em)


# ---- 历史K线（TTL 1h）----

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_etf_history(symbol: str, days: int = 30) -> pd.DataFrame:
    """获取 ETF 历史 K 线"""
    key = f"hist_{symbol}_{days}"

    def _fetch():
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=days * 2)).strftime("%Y%m%d")
        df = ak.fund_etf_hist_em(
            symbol=symbol, period="daily",
            start_date=start_date, end_date=end_date, adjust="qfq",
        )
        df["日期"] = pd.to_datetime(df["日期"])
        df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
        df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
        return df.sort_values("日期").tail(days)

    return _cached_fetch(key, 3600, _fetch)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_benchmark_history(days: int = 30) -> pd.DataFrame:
    """获取基准 ETF（沪深300）历史数据"""
    from data.etf_list import RS_BENCHMARK
    return fetch_etf_history(RS_BENCHMARK, days)


# ---- 衍生查询 ----

def get_industry_etf_quotes() -> pd.DataFrame:
    """筛选行业 ETF 行情，附带板块名称"""
    all_quotes = fetch_etf_quotes()
    codes = set(INDUSTRY_ETFS.values())
    df = all_quotes[all_quotes["代码"].isin(codes)].copy()
    df["sector"] = df["代码"].map(CODE_TO_NAME)

    numeric_cols = [
        "最新价", "涨跌幅", "成交额", "换手率", "最新份额", "流通市值",
        "主力净流入-净额", "主力净流入-净占比",
        "超大单净流入-净额", "大单净流入-净额",
        "中单净流入-净额", "小单净流入-净额",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["成交额", "主力净流入-净额", "超大单净流入-净额", "大单净流入-净额", "中单净流入-净额", "小单净流入-净额"]:
        if col in df.columns:
            df[f"{col}(亿)"] = df[col] / 1e8

    return df


def get_benchmark_quotes() -> pd.DataFrame:
    """获取宽基 ETF 行情"""
    all_quotes = fetch_etf_quotes()
    codes = set(BENCHMARK_ETFS.values())
    df = all_quotes[all_quotes["代码"].isin(codes)].copy()
    df["sector"] = df["代码"].map({v: k for k, v in BENCHMARK_ETFS.items()})
    for col in ["最新价", "涨跌幅"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
