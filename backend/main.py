"""ETF 轮动监测 — FastAPI 后端"""

import sys
import os

# 确保 import 路径正确
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd

from data.fetcher import get_industry_etf_quotes, fetch_etf_history
from analytics.rotation import compute_rs_matrix, compute_rotation_signal
from analytics.signals import build_signal_table

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
    rs_df = compute_rs_matrix()
    rs_df = compute_rotation_signal(rs_df)
    return rs_df.fillna("").to_dict(orient="index")


@app.get("/api/signals")
def get_signals():
    """综合信号表"""
    quotes_df = get_industry_etf_quotes()
    rs_df = compute_rs_matrix()
    rs_df = compute_rotation_signal(rs_df)
    signal_table = build_signal_table(rs_df, quotes_df)
    return signal_table.fillna("").to_dict(orient="records")


@app.get("/api/history/{code}")
def get_history(code: str, days: int = 30):
    """单只 ETF 历史 K 线"""
    df = fetch_etf_history(code, days)
    return df.fillna("").to_dict(orient="records")


# 生产环境：托管 React 静态文件
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
