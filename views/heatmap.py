"""板块轮动热力图视图"""

import plotly.graph_objects as go
import streamlit as st

from analytics.rotation import compute_rs_matrix, compute_rotation_signal


def render_heatmap():
    """渲染板块 RS 热力图"""
    with st.spinner("正在计算板块相对强度（需获取 25+ 只 ETF 历史数据，约30秒）..."):
        rs_df = compute_rs_matrix()
        rs_df = compute_rotation_signal(rs_df)

    if rs_df.empty:
        st.warning("暂无数据")
        return

    st.subheader("板块 RS 热力图")
    st.caption("RS > 1 表示跑赢沪深300，颜色越红越强 | 箭头表示5日排名 vs 20日排名的变化方向")

    rs_cols = [c for c in rs_df.columns if c.startswith("RS_")]
    if not rs_cols:
        st.warning("RS 数据不足，可能历史数据获取失败")
        return

    labels = [c.replace("RS_", "").replace("d", "日") for c in rs_cols]
    sectors = rs_df.index.tolist()
    z_data = rs_df[rs_cols].values

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=labels,
        y=sectors,
        colorscale=[
            [0.0, "#2d6a4f"],
            [0.3, "#52b788"],
            [0.5, "#f4f4f4"],
            [0.7, "#e76f51"],
            [1.0, "#d62828"],
        ],
        zmid=1.0,
        text=[[f"{v:.2f}" if v is not None and v == v else "" for v in row] for row in z_data],
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="%{y} %{x}: RS=%{z:.3f}<extra></extra>",
    ))

    fig.update_layout(
        height=max(500, len(sectors) * 28),
        xaxis_title="周期",
        yaxis_title="",
        margin=dict(l=100, r=40, t=30, b=30),
        font=dict(size=12),
    )

    st.plotly_chart(fig, width="stretch")

    # 排名变化表
    st.subheader("轮动方向")
    display_cols = [c for c in rs_df.columns if c.startswith(("RS_", "rank_", "direction"))]
    if display_cols:
        show_df = rs_df[display_cols].copy()
        rename_map = {}
        for c in show_df.columns:
            if "direction" in c:
                rename_map[c] = "方向"
            elif c.startswith("RS_"):
                rename_map[c] = c.replace("RS_", "RS(") + "日)"
            elif c.startswith("rank_"):
                rename_map[c] = c.replace("rank_", "排名(") + "日)"
        show_df = show_df.rename(columns=rename_map)
        st.dataframe(show_df, width="stretch")
