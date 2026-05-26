"""AKShare 数据获取层 — 带缓存

可用接口:
- fund_etf_spot_em(): ETF实时行情 + 份额 + 资金流（一个接口搞定）
- fund_etf_hist_em(): ETF历史K线（RS计算）
"""

import datetime
import os

import akshare as ak
import pandas as pd
import requests
import streamlit as st

from data.etf_list import INDUSTRY_ETFS, CODE_TO_NAME, BENCHMARK_ETFS

# AKShare 访问国内站点，全局绕过代理
os.environ["NO_PROXY"] = "*"
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)

# 同时 patch requests 的 proxy 检测
original_getproxies = requests.utils.getproxies


def _no_proxies(*args, **kwargs):
    return {}


requests.utils.getproxies = _no_proxies


@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_quotes() -> pd.DataFrame:
    """获取全市场 ETF 实时行情（含份额、资金流）"""
    df = ak.fund_etf_spot_em()
    return df


def get_industry_etf_quotes() -> pd.DataFrame:
    """筛选行业 ETF 行情，附带板块名称"""
    all_quotes = fetch_etf_quotes()
    codes = set(INDUSTRY_ETFS.values())
    df = all_quotes[all_quotes["代码"].isin(codes)].copy()
    df["sector"] = df["代码"].map(CODE_TO_NAME)

    # 转换数值列
    numeric_cols = [
        "最新价", "涨跌幅", "成交额", "换手率", "最新份额", "流通市值",
        "主力净流入-净额", "主力净流入-净占比",
        "超大单净流入-净额", "大单净流入-净额",
        "中单净流入-净额", "小单净流入-净额",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 金额转换为亿元
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


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_etf_history(symbol: str, days: int = 30) -> pd.DataFrame:
    """获取 ETF 历史 K 线"""
    end_date = datetime.date.today().strftime("%Y%m%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=days * 2)).strftime("%Y%m%d")
    df = ak.fund_etf_hist_em(
        symbol=symbol, period="daily",
        start_date=start_date, end_date=end_date, adjust="qfq",
    )
    df["日期"] = pd.to_datetime(df["日期"])
    df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
    df["收盘"] = pd.to_numeric(df["收盘"], errors="coerce")
    df = df.sort_values("日期").tail(days)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_benchmark_history(days: int = 30) -> pd.DataFrame:
    """获取基准 ETF（沪深300）历史数据"""
    from data.etf_list import RS_BENCHMARK
    return fetch_etf_history(RS_BENCHMARK, days)
