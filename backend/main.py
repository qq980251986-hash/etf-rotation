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


PERIOD_MAP = {"7d": 7, "1m": 30, "3m": 90}


@app.get("/api/accumulation")
def get_accumulation(period: str = "7d"):
    """主力建仓概率 — 多因子评分"""
    days = PERIOD_MAP.get(period, 7)
    quotes_df = get_industry_etf_quotes()

    results = []
    for sector, code in INDUSTRY_ETFS.items():
        # 当日资金流数据
        q = quotes_df[quotes_df["代码"] == code] if "代码" in quotes_df.columns else pd.DataFrame()
        huge_yi = big_yi = small_yi = turnover_yi = change_pct = 0.0
        if not q.empty:
            r = q.iloc[0]
            huge_yi = float(r.get("超大单净流入-净额(亿)", 0) or 0)
            big_yi = float(r.get("大单净流入-净额(亿)", 0) or 0)
            small_yi = float(r.get("小单净流入-净额(亿)", 0) or 0)
            turnover_yi = float(r.get("成交额(亿)", 0) or 0)
            change_pct = float(r.get("涨跌幅", 0) or 0)

        # 因子1: 大买小卖（权重35）
        big_total = huge_yi + big_yi
        if big_total > 0 and small_yi < 0:
            big_vs_small_score = 35
            big_vs_small_label = "大买小卖"
        elif big_total > 0 and small_yi > 0:
            ratio = max(0, 1 - small_yi / (big_total + 0.01))
            big_vs_small_score = round(35 * ratio * 0.6, 1)
            big_vs_small_label = "大单主导"
        elif big_total > 0:
            big_vs_small_score = 20
            big_vs_small_label = "大单流入"
        else:
            big_vs_small_score = 0
            big_vs_small_label = "无明显信号"

        # 因子2: 大单集中度（权重20）
        concentration = 0
        concentration_label = "低"
        if turnover_yi > 0:
            concentration = min(20, abs(big_total) / turnover_yi * 100 * 2)
            if concentration > 12:
                concentration_label = "高"
            elif concentration > 6:
                concentration_label = "中"

        # 因子3 & 4: 需要历史数据
        volume_price_score = 0
        volume_price_label = "无数据"
        bottoming_score = 0
        bottoming_label = "无数据"

        try:
            hist = fetch_etf_history(code, days)
            if len(hist) >= days // 2 + 1:
                import numpy as np
                volumes = hist["成交额"] if "成交额" in hist.columns else pd.Series(dtype=float)
                changes = hist["涨跌幅"]

                # 因子3: 量价背离 — 当日放量但价未涨（权重25）
                if len(volumes) >= 3 and len(changes) >= 1:
                    vol_today = float(volumes.iloc[-1]) if pd.notna(volumes.iloc[-1]) else 0
                    vol_avg = float(volumes.iloc[:-1].mean()) if len(volumes) > 1 else 0
                    if vol_avg > 0 and vol_today > vol_avg * 1.5 and abs(change_pct) < 1.5:
                        volume_price_score = 25
                        volume_price_label = "放量滞涨"
                    elif vol_avg > 0 and vol_today > vol_avg * 1.2 and change_pct < 0:
                        volume_price_score = 18
                        volume_price_label = "放量不跌"
                    elif vol_avg > 0 and vol_today < vol_avg * 0.7:
                        volume_price_score = 5
                        volume_price_label = "缩量"
                    else:
                        volume_price_score = 8
                        volume_price_label = "正常"

                # 因子4: 底部企稳 — 前半段跌幅 > 后半段，后半段放量（权重20）
                mid = len(changes) // 2
                if mid >= 2:
                    first_half_change = float(changes.iloc[:mid].sum())
                    second_half_change = float(changes.iloc[mid:].sum())
                    first_half_vol = float(volumes.iloc[:mid].mean()) if len(volumes) >= mid else 0
                    second_half_vol = float(volumes.iloc[mid:].mean()) if len(volumes) >= mid else 0

                    if first_half_change < second_half_change and second_half_vol > first_half_vol * 1.1:
                        # 前跌后企稳 + 后半段放量
                        strength = min(1.0, abs(first_half_change - second_half_change) / max(abs(first_half_change), 1))
                        bottoming_score = round(20 * strength, 1)
                        bottoming_label = "止跌放量"
                    elif second_half_change > 0 and first_half_vol > 0 and second_half_vol > first_half_vol:
                        bottoming_score = 10
                        bottoming_label = "温和反弹"
                    else:
                        bottoming_score = 3
                        bottoming_label = "无明显信号"
        except Exception as e:
            logger.debug(f"accumulation history failed for {sector}: {e}")

        accum_score = round(big_vs_small_score + concentration + volume_price_score + bottoming_score, 1)

        if accum_score >= 70:
            accum_label = "高概率建仓"
        elif accum_score >= 50:
            accum_label = "可能建仓"
        elif accum_score >= 30:
            accum_label = "轻微迹象"
        else:
            accum_label = "无明显迹象"

        results.append({
            "sector": sector,
            "accum_score": accum_score,
            "accum_label": accum_label,
            "big_vs_small": big_vs_small_label,
            "big_vs_small_score": big_vs_small_score,
            "concentration": round(concentration, 1),
            "concentration_label": concentration_label,
            "volume_price": volume_price_label,
            "volume_price_score": volume_price_score,
            "bottoming": bottoming_label,
            "bottoming_score": bottoming_score,
            "huge_yi": round(huge_yi, 2),
            "big_yi": round(big_yi, 2),
            "small_yi": round(small_yi, 2),
            "change_pct": round(change_pct, 2),
            "period": period,
        })

    results.sort(key=lambda x: x["accum_score"], reverse=True)
    return results


STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
