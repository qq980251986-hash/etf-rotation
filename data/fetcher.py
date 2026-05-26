"""AKShare 数据获取层 — 磁盘缓存（无框架依赖）"""

import datetime
import json
import os
import pathlib
import time
from functools import lru_cache

import akshare as ak
import pandas as pd
import requests

from data.etf_list import INDUSTRY_ETFS, CODE_TO_NAME, BENCHMARK_ETFS

# AKShare 访问国内站点，全局绕过代理
os.environ["NO_PROXY"] = "*"
for _k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(_k, None)

requests.utils.getproxies = lambda *_, **__: {}

_CACHE_DIR = pathlib.Path(__file__).parent.parent / ".cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _read_disk_cache(key: str, ttl_seconds: int):
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
    fp = _CACHE_DIR / f"{key}.parquet"
    meta_fp = _CACHE_DIR / f"{key}.meta.json"
    df.to_parquet(fp, index=False)
    meta_fp.write_text(json.dumps({"ts": time.time()}))


def _cached_fetch(key: str, ttl_seconds: int, fetch_fn):
    disk_df = _read_disk_cache(key, ttl_seconds)
    if disk_df is not None:
        return disk_df
    df = fetch_fn()
    _write_disk_cache(key, df)
    return df


def _retry(fn, retries=3, delay=2):
    """简单重试包装"""
    for i in range(retries):
        try:
            return fn()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(delay)


# ---- 实时行情（TTL 5min）----

@lru_cache(maxsize=1)
def fetch_etf_quotes() -> pd.DataFrame:
    return _cached_fetch("etf_quotes_all", 300, ak.fund_etf_spot_em)


# ---- 历史K线（TTL 1h）----

@lru_cache(maxsize=128)
def fetch_etf_history(symbol: str, days: int = 30) -> pd.DataFrame:
    key = f"hist_{symbol}_{days}"

    def _fetch():
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=days * 2)).strftime("%Y%m%d")
        df = _retry(lambda: ak.fund_etf_hist_em(
            symbol=symbol, period="daily",
            start_date=start_date, end_date=end_date, adjust="qfq",
        ), retries=3, delay=2)
        df["日期"] = pd.to_datetime(df["日期"])
        df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
        df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
        return df.sort_values("日期").tail(days)

    return _cached_fetch(key, 3600, _fetch)


@lru_cache(maxsize=4)
def fetch_benchmark_history(days: int = 30) -> pd.DataFrame:
    from data.etf_list import RS_BENCHMARK
    return fetch_etf_history(RS_BENCHMARK, days)


# ---- 衍生查询 ----

def get_industry_etf_quotes() -> pd.DataFrame:
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
    all_quotes = fetch_etf_quotes()
    codes = set(BENCHMARK_ETFS.values())
    df = all_quotes[all_quotes["代码"].isin(codes)].copy()
    df["sector"] = df["代码"].map({v: k for k, v in BENCHMARK_ETFS.items()})
    for col in ["最新价", "涨跌幅"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
