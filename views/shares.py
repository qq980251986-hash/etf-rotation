"""ETF 份额变动监控视图"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.fetcher import get_industry_etf_quotes


def render_shares():
    """渲染 ETF 份额排名"""
    with st.spinner("正在获取 ETF 份额数据..."):
        quotes_df = get_industry_etf_quotes()

    if quotes_df.empty:
        st.warning("暂无 ETF 份额数据")
        return

    share_col = "最新份额"
    if share_col not in quotes_df.columns:
        st.warning("数据中未找到份额字段")
        return

    df = quotes_df.dropna(subset=[share_col]).sort_values(share_col, ascending=True)

    if df.empty:
        st.warning("无有效份额数据")
        return

    # 份额转亿份
    df["份额(亿份)"] = df[share_col] / 1e8

    st.subheader("行业 ETF 份额排名")
    st.caption("份额变化反映资金申赎方向，大额申购=看多信号")

    # 柱状图
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["sector"],
        x=df["份额(亿份)"],
        orientation="h",
        marker_color=df["涨跌幅"].apply(
            lambda x: "#d62828" if pd.notna(x) and x > 0
            else "#2d6a4f" if pd.notna(x) else "#adb5bd"
        ),
        text=df["份额(亿份)"].apply(lambda x: f"{x:.1f}"),
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="%{y}: %{x:.1f}亿份<extra></extra>",
    ))

    fig.update_layout(
        height=max(500, len(df) * 28),
        xaxis_title="份额（亿份）",
        yaxis_title="",
        margin=dict(l=100, r=60, t=30, b=30),
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch")

    # 数据明细
    st.subheader("份额 + 资金流明细")
    show_cols = {
        "sector": "板块",
        "份额(亿份)": "份额(亿份)",
        "涨跌幅": "涨跌幅(%)",
        "最新价": "最新价",
        "成交额(亿)": "成交额(亿)",
        "主力净流入-净额(亿)": "主力净流入(亿)",
    }
    available = {k: v for k, v in show_cols.items() if k in df.columns}
    show_df = df[list(available.keys())].rename(columns=available)
    show_df = show_df.sort_values("份额(亿份)", ascending=False)
    st.dataframe(show_df, width="stretch", hide_index=True)
