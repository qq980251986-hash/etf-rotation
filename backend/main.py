"""ETF 轮动监测 — FastAPI 后端"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd

from data.fetcher import get_industry_etf_quotes, fetch_etf_history
from analytics.rotation import compute_rs_matrix, compute_rotation_signal
from analytics.signals import build_signal_table, score_fund_flow, compute_composite_score, signal_label
from data.etf_list import INDUSTRY_ETFS

logger = logging.getLogger("etf")

app = FastAPI(title="ETF 轮动监测 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_signal_row(sector: str, rs_5d=None, rs_10d=None, rs_20d=None,
                      direction="-", rs_score=50.0, flow_yi=0.0,
                      shares_yi=0.0, change_pct=0.0, flow_score=50.0,
                      signal_text=""):
    comp = compute_composite_score(flow_score, rs_score)
    if not signal_text:
        label, icon = signal_label(comp)
        signal_text = f"{icon} {label}"
    return {
        "sector": sector,
        "rs_5d": rs_5d,
        "rs_10d": rs_10d,
        "rs_20d": rs_20d,
        "direction": direction,
        "rs_score": rs_score,
        "flow_yi": round(flow_yi, 2),
        "shares_yi": round(shares_yi, 2),
        "change_pct": round(float(change_pct), 2) if change_pct else 0,
        "flow_score": flow_score,
        "composite_score": comp,
        "signal": signal_text,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/quotes")
def get_quotes():
    """行业 ETF 实时行情"""
    df = get_industry_etf_quotes()
    results = []
    for _, row in df.iterrows():
        results.append({
            "sector": row.get("sector", ""),
            "code": row.get("代码", ""),
            "name": row.get("名称", ""),
            "price": row.get("最新价", 0),
            "change_pct": row.get("涨跌幅", 0),
            "turnover_yi": round(float(row.get("成交额(亿)", 0) or 0), 2),
            "shares_yi": round(float(row.get("最新份额", 0) or 0) / 1e8, 2),
            "flow_yi": round(float(row.get("主力净流入-净额(亿)", 0) or 0), 2),
            "flow_pct": row.get("主力净流入-净占比", 0),
            "huge_yi": round(float(row.get("超大单净流入-净额(亿)", 0) or 0), 2),
            "big_yi": round(float(row.get("大单净流入-净额(亿)", 0) or 0), 2),
            "mid_yi": round(float(row.get("中单净流入-净额(亿)", 0) or 0), 2),
            "small_yi": round(float(row.get("小单净流入-净额(亿)", 0) or 0), 2),
        })
    return results


@app.get("/api/rs-matrix")
def get_rs_matrix():
    """RS 矩阵"""
    try:
        rs_df = compute_rs_matrix()
        rs_df = compute_rotation_signal(rs_df)
        out = {}
        for sector in rs_df.index:
            r = rs_df.loc[sector]
            out[sector] = {
                "rs_5d": r.get("RS_5d"),
                "rs_10d": r.get("RS_10d"),
                "rs_20d": r.get("RS_20d"),
                "ret_5d": r.get("ret_5d"),
                "ret_10d": r.get("ret_10d"),
                "ret_20d": r.get("ret_20d"),
                "rank_5d": r.get("rank_5d"),
                "rank_20d": r.get("rank_20d"),
                "rank_change": r.get("rank_change"),
                "direction": r.get("direction", "→ 持平"),
            }
        return out
    except Exception as e:
        logger.warning(f"RS matrix failed: {e}")
        return {}


@app.get("/api/signals")
def get_signals():
    """综合信号表"""
    quotes_df = get_industry_etf_quotes()

    try:
        rs_df = compute_rs_matrix()
        rs_df = compute_rotation_signal(rs_df)
    except Exception as e:
        logger.warning(f"RS failed, fallback: {e}")
        rs_df = None

    results = []
    for sector, code in INDUSTRY_ETFS.items():
        q = quotes_df[quotes_df["代码"] == code] if "代码" in quotes_df.columns else pd.DataFrame()
        flow_yi = 0.0
        shares_yi = 0.0
        change_pct = 0.0
        if not q.empty:
            r = q.iloc[0]
            flow_yi = float(r.get("主力净流入-净额(亿)", 0) or 0)
            shares_yi = float(r.get("最新份额", 0) or 0) / 1e8
            change_pct = float(r.get("涨跌幅", 0) or 0)

        rs_5d = rs_10d = rs_20d = None
        direction = "-"
        rs_score = 50.0
        if rs_df is not None and sector in rs_df.index:
            row = rs_df.loc[sector]
            rs_5d = row.get("RS_5d")
            rs_10d = row.get("RS_10d")
            rs_20d = row.get("RS_20d")
            direction = row.get("direction", "-")
            if rs_5d is not None and rs_5d == rs_5d:
                from analytics.signals import score_rs
                rs_score = score_rs(rs_5d)

        flow_score = score_fund_flow(flow_yi)
        comp = compute_composite_score(flow_score, rs_score)
        label, icon = signal_label(comp)

        results.append(_build_signal_row(
            sector=sector, rs_5d=rs_5d, rs_10d=rs_10d, rs_20d=rs_20d,
            direction=direction, rs_score=rs_score, flow_yi=flow_yi,
            shares_yi=shares_yi, change_pct=change_pct, flow_score=flow_score,
            signal_text=f"{icon} {label}",
        ))
        results[-1]["composite_score"] = comp

    results.sort(key=lambda x: x["composite_score"], reverse=True)
    return results


@app.get("/api/history/{code}")
def get_history(code: str, days: int = 30):
    """单只 ETF 历史 K 线"""
    df = fetch_etf_history(code, days)
    out = []
    for _, row in df.iterrows():
        out.append({
            "date": str(row["日期"])[:10],
            "close": float(row["收盘"]),
            "change_pct": float(row["涨跌幅"]),
        })
    return out


STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
