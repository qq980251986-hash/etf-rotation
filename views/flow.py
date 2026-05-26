"""资金流向排行视图 — 基于 ETF 级别资金流数据"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.fetcher import get_industry_etf_quotes


def render_flow():
    """渲染行业 ETF 资金流向排行"""
    with st.spinner("正在获取资金流向数据..."):
        quotes_df = get_industry_etf_quotes()

    if quotes_df.empty:
        st.warning("暂无资金流向数据")
        return

    flow_col = "主力净流入-净额(亿)"
    if flow_col not in quotes_df.columns:
        st.warning("数据中未找到资金流字段")
        return

    df = quotes_df.dropna(subset=[flow_col]).sort_values(flow_col, ascending=True)

    st.subheader("行业 ETF 主力资金流向")
    st.caption("红色=净流入（看多），绿色=净流出（看空）")

    # 双向柱状图
    colors = df[flow_col].apply(lambda x: "#d62828" if x > 0 else "#2d6a4f")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["sector"],
        x=df[flow_col],
        orientation="h",
        marker_color=colors,
        text=df[flow_col].apply(lambda x: f"{x:.2f}亿"),
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="%{y}: %{x:.2f}亿<extra></extra>",
    ))

    fig.update_layout(
        height=max(500, len(df) * 28),
        xaxis_title="主力净流入（亿元）",
        yaxis_title="",
        margin=dict(l=100, r=60, t=30, b=30),
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch")

    # 分层资金流明细
    st.subheader("分层资金流明细")
    detail_cols_map = {
        "sector": "板块",
        "涨跌幅": "涨跌幅(%)",
        "主力净流入-净额(亿)": "主力净流入(亿)",
        "主力净流入-净占比": "主力净占比(%)",
        "超大单净流入-净额(亿)": "超大单(亿)",
        "大单净流入-净额(亿)": "大单(亿)",
        "中单净流入-净额(亿)": "中单(亿)",
        "小单净流入-净额(亿)": "小单(亿)",
        "成交额(亿)": "成交额(亿)",
    }
    available = {k: v for k, v in detail_cols_map.items() if k in df.columns}
    show_df = df[list(available.keys())].rename(columns=available)
    show_df = show_df.sort_values("主力净流入(亿)", ascending=False)

    def highlight_flow(val):
        if pd.isna(val):
            return ""
        try:
            v = float(val)
            if v > 0:
                return "color: #d62828; font-weight: bold"
            elif v < 0:
                return "color: #2d6a4f; font-weight: bold"
        except (ValueError, TypeError):
            pass
        return ""

    styled = show_df.style.map(highlight_flow, subset=["主力净流入(亿)"])
    st.dataframe(styled, width="stretch", hide_index=True)
