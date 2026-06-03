"""轮动信号评分系统 — 基于 ETF 级别数据"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def score_fund_flow(flow_value: float) -> float:
    """资金流得分 (0-100)，sigmoid 映射"""
    if pd.isna(flow_value):
        return 50.0
    score = 100 / (1 + np.exp(-flow_value * 0.5))
    return round(score, 1)


def score_rs(rs_value: float | None) -> float:
    """RS 得分 (0-100)"""
    if rs_value is None or pd.isna(rs_value):
        return 50.0
    score = min(100, max(0, (rs_value - 0.5) / 1.5 * 100))
    return round(score, 1)


def compute_composite_score(flow_score: float = 50.0, rs_score: float = 50.0) -> float:
    """综合评分 = 资金流×0.6 + RS×0.4"""
    return round(flow_score * 0.6 + rs_score * 0.4, 1)


def score_accumulation(flow_yi: float, small_yi: float,
                       change_pct: float, shares_change_pct: float) -> float:
    """吸筹指数 (0-100): 资金流入 + 散户离场 + 价格不动 + 份额增长"""
    # 1. 主力净流入 (0-40) — sigmoid 映射
    big_money = 40.0 / (1.0 + math.exp(-flow_yi * 0.5))

    # 2. 小单净流出 = 散户在卖 (0-20)
    retail_sell = min(20.0, max(0.0, abs(min(0.0, small_yi)) * 4))

    # 3. 价格平稳 = 主力在压制吸筹 (0-20)
    price_stable = max(0.0, 20.0 * (1.0 - abs(change_pct) / 3.0))

    # 4. ETF 份额增长 = 机构一级市场申购 (0-20)
    share_growth = min(20.0, max(0.0, shares_change_pct * 4))

    return round(big_money + retail_sell + price_stable + share_growth, 1)


def signal_label(score: float) -> tuple[str, str]:
    """根据评分返回 (信号文字, 图标)"""
    if score >= 75:
        return "强势流入", "🔴"
    elif score >= 60:
        return "温和流入", "🟠"
    elif score >= 40:
        return "中性", "⚪"
    elif score >= 25:
        return "温和流出", "🟢"
    else:
        return "强势流出", "🔵"


def position_recommendation(composite_score: float, direction: str) -> dict:
    """计算卖出建议 + 仓位布局建议"""
    if pd.isna(composite_score):
        composite_score = 50.0
    base = (100 - composite_score) / 10
    adjust = 1.0 if "流出" in direction else (-1.0 if "流入" in direction else 0.0)
    sell_tenths = max(0, min(10, int(round(base + adjust))))
    position_tenths = 10 - sell_tenths

    if sell_tenths == 0:
        sell_label = "持有"
    elif sell_tenths == 10:
        sell_label = "清仓"
    else:
        sell_label = f"卖出{sell_tenths}成"

    if position_tenths == 0:
        pos_label = "空仓"
    elif position_tenths <= 3:
        pos_label = f"轻仓{position_tenths}成"
    elif position_tenths <= 6:
        pos_label = f"半仓{position_tenths}成"
    elif position_tenths <= 9:
        pos_label = f"重仓{position_tenths}成"
    else:
        pos_label = "满仓"

    return {
        "sell_tenths": sell_tenths,
        "sell_recommend": sell_label,
        "position_tenths": position_tenths,
        "position_recommend": pos_label,
    }


def build_signal_table(rs_df: pd.DataFrame, quotes_df: pd.DataFrame) -> pd.DataFrame:
    """生成信号汇总表
    rs_df: 来自 rotation.compute_rs_matrix
    quotes_df: 来自 fetcher.get_industry_etf_quotes
    """
    rows = []

    for sector in rs_df.index:
        row = {"板块": sector}

        # RS 数据
        rs_5d = rs_df.loc[sector].get("RS_5d")
        row["RS_5d"] = rs_5d
        row["方向"] = rs_df.loc[sector].get("direction", "→ 持平")
        rs_score = score_rs(rs_5d)
        row["RS得分"] = rs_score

        # 资金流 — 从 ETF 行情获取
        flow_score = 50.0
        flow_amount = 0.0
        row["主力净流入(亿)"] = 0.0
        row["份额(亿份)"] = 0.0

        if quotes_df is not None and not quotes_df.empty:
            from data.etf_list import INDUSTRY_ETFS
            code = INDUSTRY_ETFS.get(sector)
            if code:
                q = quotes_df[quotes_df["代码"] == code]
                if not q.empty:
                    flow_col = "主力净流入-净额(亿)"
                    if flow_col in q.columns:
                        val = q[flow_col].iloc[0]
                        if pd.notna(val):
                            flow_amount = val
                            row["主力净流入(亿)"] = round(flow_amount, 2)
                            flow_score = score_fund_flow(flow_amount)

                    share_col = "最新份额"
                    if share_col in q.columns:
                        s = q[share_col].iloc[0]
                        if pd.notna(s):
                            row["份额(亿份)"] = round(s / 1e8, 2)

                    change_col = "涨跌幅"
                    if change_col in q.columns:
                        row["涨跌幅(%)"] = q[change_col].iloc[0]

        row["资金流得分"] = flow_score

        # 综合评分
        composite = compute_composite_score(flow_score, rs_score)
        row["综合评分"] = composite
        label, icon = signal_label(composite)
        row["信号"] = f"{icon} {label}"

        # 仓位建议
        direction_val = row.get("方向", "-")
        rec = position_recommendation(composite, direction_val)
        row["卖出成数"] = rec["sell_tenths"]
        row["建议卖出"] = rec["sell_recommend"]
        row["仓位成数"] = rec["position_tenths"]
        row["建议仓位"] = rec["position_recommend"]

        rows.append(row)

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("综合评分", ascending=False).reset_index(drop=True)
    return result
