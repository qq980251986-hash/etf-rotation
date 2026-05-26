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

logger = logging.getLogger("etf")

app = FastAPI(title="ETF 轮动监测 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/quotes")
def get_quotes():
    """行业 ETF 实时行情（份额 + 资金流）"""
    df = get_industry_etf_quotes()
    cols = [
        "sector", "代码", "名称", "最新价", "涨跌幅", "成交额", "换手率",
        "最新份额", "流通市值",
        "主力净流入-净额", "主力净流入-净占比",
        "超大单净流入-净额", "大单净流入-净额",
        "中单净流入-净额", "小单净流入-净额",
        "主力净流入-净额(亿)", "超大单净流入-净额(亿)",
        "大单净流入-净额(亿)", "中单净流入-净额(亿)",
        "小单净流入-净额(亿)", "成交额(亿)",
    ]
    available = [c for c in cols if c in df.columns]
    return df[available].fillna("").to_dict(orient="records")


@app.get("/api/rs-matrix")
def get_rs_matrix():
    """RS 矩阵 + 轮动方向"""
    try:
        rs_df = compute_rs_matrix()
        rs_df = compute_rotation_signal(rs_df)
        return rs_df.fillna("").to_dict(orient="index")
    except Exception as e:
        logger.warning(f"RS matrix failed: {e}")
        return {}


@app.get("/api/signals")
def get_signals():
    """综合信号表（RS 失败时降级为纯资金流信号）"""
    from data.etf_list import INDUSTRY_ETFS

    quotes_df = get_industry_etf_quotes()

    try:
        rs_df = compute_rs_matrix()
        rs_df = compute_rotation_signal(rs_df)
        signal_table = build_signal_table(rs_df, quotes_df)
        return signal_table.fillna("").to_dict(orient="records")
    except Exception as e:
        logger.warning(f"RS calculation failed, fallback to flow-only: {e}")
        rows = []
        for _, row in quotes_df.iterrows():
            flow_col = "主力净流入-净额(亿)"
            flow = row.get(flow_col, 0)
            if pd.isna(flow):
                flow = 0
            fs = score_fund_flow(flow)
            comp = compute_composite_score(fs, 50.0)
            label, icon = signal_label(comp)
            share = row.get("最新份额", 0)
            rows.append({
                "板块": row.get("sector", ""),
                "RS_5d": None,
                "RS_10d": None,
                "RS_20d": None,
                "方向": "-",
                "RS得分": 50.0,
                "主力净流入(亿)": round(flow, 2),
                "份额(亿份)": round(share / 1e8, 2) if pd.notna(share) and share else 0,
                "涨跌幅(%)": row.get("涨跌幅", ""),
                "资金流得分": fs,
                "综合评分": comp,
                "信号": f"{icon} {label}",
            })
        result = pd.DataFrame(rows).sort_values("综合评分", ascending=False).reset_index(drop=True)
        return result.fillna("").to_dict(orient="records")


@app.get("/api/history/{code}")
def get_history(code: str, days: int = 30):
    """单只 ETF 历史 K 线"""
    df = fetch_etf_history(code, days)
    return df.fillna("").to_dict(orient="records")


STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
