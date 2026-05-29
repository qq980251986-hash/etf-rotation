"""补充数据获取层 — 北向资金/行业排名/龙虎榜/热点题材

数据源来自 a-stock-data skill 的直连 HTTP API，不依赖 akshare。
复用 fetcher.py 的缓存模式（Parquet 磁盘 + LRU 内存）。
"""

import datetime
import json
import logging
import pathlib
import time
from functools import lru_cache

import pandas as pd
import requests

_CACHE_DIR = pathlib.Path(__file__).parent.parent / ".cache"
_CACHE_DIR.mkdir(exist_ok=True)
_logger = logging.getLogger("etf.augmented")

# 东财数据中心共用
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


# ---- 缓存基础设施（复用 fetcher.py 模式）----

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


# ---- 东财数据中心统一查询 ----

def _eastmoney_datacenter(report_name: str, columns: str = "ALL",
                           filter_str: str = "", page_size: int = 50,
                           sort_columns: str = "", sort_types: str = "-1") -> list[dict]:
    params = {
        "reportName": report_name, "columns": columns,
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    r = requests.get(DATACENTER_URL, params=params,
                     headers={"User-Agent": UA}, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []


# ---- 1. 北向资金（TTL 5min）----

HSGT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36",
    "Host": "data.hexin.cn",
    "Referer": "https://data.hexin.cn/",
}

_NORTHBOUND_CSV = _CACHE_DIR / "northbound_daily.csv"


@lru_cache(maxsize=1)
def fetch_northbound_realtime() -> pd.DataFrame:
    """沪深股通当日分钟流向（262 个时间点，单位亿元）"""
    def _fetch():
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
        r = requests.get(url, headers=HSGT_HEADERS, timeout=10)
        d = r.json()
        times = d.get("time", [])
        hgt = d.get("hgt", [])
        sgt = d.get("sgt", [])
        n = len(times)
        df = pd.DataFrame({
            "time": times,
            "hgt_yi": hgt[:n] + [None] * max(0, n - len(hgt)),
            "sgt_yi": sgt[:n] + [None] * max(0, n - len(sgt)),
        })
        # 自动缓存今日收盘数据到 CSV
        if not df.empty:
            last = df.dropna(subset=["hgt_yi", "sgt_yi"])
            if not last.empty:
                row = last.iloc[-1]
                _save_northbound_snapshot(
                    datetime.date.today().strftime("%Y-%m-%d"),
                    float(row["hgt_yi"]), float(row["sgt_yi"]),
                )
        return df

    return _cached_fetch("northbound_realtime", 300, _fetch)


def _save_northbound_snapshot(date: str, hgt: float, sgt: float):
    """写入/更新当天北向收盘数据到 CSV"""
    rows = {}
    if _NORTHBOUND_CSV.exists():
        for line in _NORTHBOUND_CSV.read_text().strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) == 3:
                rows[parts[0]] = line
    rows[date] = f"{date},{hgt:.2f},{sgt:.2f}"
    with open(_NORTHBOUND_CSV, "w") as f:
        f.write("date,hgt_yi,sgt_yi\n")
        for d in sorted(rows.keys()):
            f.write(rows[d] + "\n")


def fetch_northbound_history(n: int = 20) -> pd.DataFrame:
    """读取最近 N 天北向历史"""
    if not _NORTHBOUND_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(_NORTHBOUND_CSV)
    return df.tail(n)


# ---- 2. 行业板块排名（TTL 30min）----

@lru_cache(maxsize=1)
def fetch_industry_ranking(top_n: int = 30) -> pd.DataFrame:
    """东财行业板块涨跌幅排名（~100 个行业）"""
    def _fetch():
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1", "pz": "100", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:90+t:2",
            "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
        }
        r = requests.get(url, params=params,
                         headers={"User-Agent": UA}, timeout=15)
        d = r.json()
        items = d.get("data", {}).get("diff", [])
        if not items:
            return pd.DataFrame()

        rows = []
        for i, item in enumerate(items):
            rows.append({
                "rank": i + 1,
                "name": item.get("f14", ""),
                "change_pct": item.get("f3", 0),
                "code": item.get("f12", ""),
                "up_count": item.get("f104", 0),
                "down_count": item.get("f105", 0),
                "leader": item.get("f140", ""),
                "leader_change": item.get("f136", 0),
            })
        return pd.DataFrame(rows)

    return _cached_fetch("industry_ranking", 1800, lambda: _fetch())


# ---- 3. 全市场龙虎榜（TTL 4h）----

@lru_cache(maxsize=4)
def fetch_dragon_tiger_daily(trade_date: str = None) -> pd.DataFrame:
    """每日全市场龙虎榜"""
    if trade_date is None:
        trade_date = datetime.date.today().strftime("%Y-%m-%d")

    def _fetch():
        data = _eastmoney_datacenter(
            "RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_str=f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
            page_size=500,
            sort_columns="BILLBOARD_NET_AMT", sort_types="-1",
        )
        if not data:
            return pd.DataFrame()

        rows = []
        for row in data:
            rows.append({
                "code": row.get("SECURITY_CODE", ""),
                "name": row.get("SECURITY_NAME_ABBR", ""),
                "reason": row.get("EXPLANATION", ""),
                "close": row.get("CLOSE_PRICE") or 0,
                "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
                "net_buy_wan": round((row.get("BILLBOARD_NET_AMT") or 0) / 10000, 1),
                "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
                "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
                "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
            })
        return pd.DataFrame(rows)

    return _cached_fetch(f"dragon_tiger_{trade_date}", 14400, _fetch)


# ---- 4. 同花顺热点题材归因（TTL 30min）----

def _enrich_quotes_from_eastmoney(df: pd.DataFrame):
    """用东财行情 API 批量补充涨幅%、换手率%、收盘价"""
    codes = df["代码"].tolist()
    # 构造 secid: 6 开头=沪市(1.), 其余=深市(0.)
    secids = [
        f"1.{c}" if c.startswith("6") else f"0.{c}" for c in codes
    ]
    # 东财字段: f2=最新价, f3=涨跌幅, f8=换手率, f12=代码
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fields": "f2,f3,f8,f12",
        "secids": ",".join(secids),
    }
    try:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=10)
        diff = (r.json().get("data") or {}).get("diff") or []
    except Exception as e:
        _logger.warning(f"东财单股行情补充失败: {e}")
        diff = []

    quote_map = {}
    for item in diff:
        code = item.get("f12", "")
        price = item.get("f2", "-")
        change = item.get("f3", "-")
        turnover = item.get("f8", "-")
        quote_map[code] = {
            "收盘价": price / 100 if isinstance(price, (int, float)) else price,
            "涨幅%": change / 100 if isinstance(change, (int, float)) else change,
            "换手率%": turnover / 100 if isinstance(turnover, (int, float)) else turnover,
        }

    for col in ("收盘价", "涨幅%", "换手率%"):
        if col not in df.columns:
            df[col] = None

    for idx, row in df.iterrows():
        q = quote_map.get(row["代码"], {})
        for col in ("收盘价", "涨幅%", "换手率%"):
            if q.get(col) is not None:
                df.at[idx, col] = q[col]


@lru_cache(maxsize=1)
def fetch_hot_themes(date: str = None) -> pd.DataFrame:
    """当日强势股 + 人工标注题材归因"""
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")

    def _fetch():
        url = (
            f"http://zx.10jqka.com.cn/event/api/getharden/"
            f"date/{date}/orderby/date/orderway/desc/charset/GBK/"
        )
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "Chrome/117.0.0.0 Safari/537.36"
            ),
        }
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if data.get("errocode", 0) != 0:
            _logger.warning(f"同花顺热点错误: {data.get('errormsg', '')}")
            return pd.DataFrame()

        rows = data.get("data") or []
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        rename_map = {
            "name": "名称", "code": "代码", "reason": "题材归因",
            "market": "市场",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # 同花顺 API 已不再返回行情字段，从东财批量补充涨幅、换手率、收盘价
        if "代码" in df.columns:
            _enrich_quotes_from_eastmoney(df)

        return df

    return _cached_fetch(f"hot_themes_{date}", 1800, _fetch)
