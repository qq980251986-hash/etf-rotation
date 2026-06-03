"""AKShare 数据获取层 — 磁盘缓存 + 启动预热 + 后台定时刷新"""

import datetime
import json
import logging
import os
import pathlib
import threading
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
_logger = logging.getLogger("etf.fetcher")


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


def _read_disk_cache_ts(key: str) -> float | None:
    """返回磁盘缓存的时间戳，无缓存或已损坏返回 None（不判断 TTL）"""
    meta_fp = _CACHE_DIR / f"{key}.meta.json"
    if not meta_fp.exists():
        return None
    try:
        return json.loads(meta_fp.read_text()).get("ts")
    except Exception:
        return None


class _RateLimiter:
    """简单令牌桶限速器 — 确保两次调用间隔 >= min_interval 秒"""
    def __init__(self, min_interval: float = 1.0):
        self._min_interval = min_interval
        self._last_time = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.time()
            elapsed = now - self._last_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_time = time.time()


# 东财域名请求限速：至少间隔 1 秒
_eastmoney_limiter = _RateLimiter(min_interval=1.0)


def _retry(fn, retries=2, delay=3):
    for i in range(retries):
        try:
            return fn()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(delay)


# ---- 实时行情（磁盘 TTL 60min，LRU + API 缓存保鲜）----

@lru_cache(maxsize=1)
def fetch_etf_quotes() -> pd.DataFrame:
    def _fetch():
        _eastmoney_limiter.wait()
        return ak.fund_etf_spot_em()
    return _cached_fetch("etf_quotes_all", 3600, _fetch)


# ---- 历史K线（磁盘 TTL 8h，可覆盖过夜）----

def _fetch_etf_history_mootdx(symbol: str, days: int) -> pd.DataFrame:
    """mootdx 降级：从通达信服务器获取 ETF 日线 K 线"""
    from mootdx.quotes import Quotes

    client = Quotes.factory(market="std")
    raw = client.bars(symbol=symbol, category=9, offset=max(days * 2, 60))

    if raw is None or raw.empty:
        raise ValueError(f"mootdx 返回空数据: {symbol}")

    # mootdx 返回列: open, close, high, low, vol, amount, datetime, ...
    # index 为 DatetimeIndex
    df = pd.DataFrame({
        "日期": pd.to_datetime(raw.index),
        "收盘": pd.to_numeric(raw["close"], errors="coerce"),
    })
    df["涨跌幅"] = df["收盘"].pct_change() * 100
    df = df.sort_values("日期").tail(days).reset_index(drop=True)
    return df


@lru_cache(maxsize=128)
def fetch_etf_history(symbol: str, days: int = 30) -> pd.DataFrame:
    key = f"hist_{symbol}_{days}"

    def _fetch():
        # 主数据源：AKShare（东方财富）— 限速保护
        _eastmoney_limiter.wait()
        try:
            end_date = datetime.date.today().strftime("%Y%m%d")
            start_date = (datetime.date.today() - datetime.timedelta(days=days * 2)).strftime("%Y%m%d")
            df = _retry(lambda: ak.fund_etf_hist_em(
                symbol=symbol, period="daily",
                start_date=start_date, end_date=end_date, adjust="qfq",
            ), retries=2, delay=3)
            df["日期"] = pd.to_datetime(df["日期"])
            df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
            df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
            return df.sort_values("日期").tail(days)
        except Exception as e:
            _logger.warning(f"AKShare K线获取失败 {symbol}: {e}，尝试 mootdx 降级...")

        # 降级数据源：mootdx（通达信）
        return _fetch_etf_history_mootdx(symbol, days)

    return _cached_fetch(key, 28800, _fetch)


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


# ---- 预热 + 后台定时刷新 ----

def warm_up():
    """启动时串行预热所有缓存（1.5s 间隔，跳过已缓存的长周期 K 线）"""
    _logger.info("开始预热缓存...")

    try:
        fetch_etf_quotes()
        _logger.info("行情缓存就绪")
    except Exception as e:
        _logger.warning(f"行情预热失败: {e}")

    from data.etf_list import RS_BENCHMARK
    all_codes = list(INDUSTRY_ETFS.values()) + [RS_BENCHMARK]
    success = 0
    for code in all_codes:
        try:
            fetch_etf_history(code, 30)
            fetch_etf_history(code, 90)
            # 300 天 K 线仅回测使用，磁盘已有则跳过
            if _read_disk_cache_ts(f"hist_{code}_300") is None:
                fetch_etf_history(code, 300)
            success += 1
        except Exception:
            pass
        time.sleep(1.5)  # 1.5s 间隔 ≈ 0.67 req/s，避免触发限流

    _logger.info(f"历史缓存就绪: {success}/{len(all_codes)}")


