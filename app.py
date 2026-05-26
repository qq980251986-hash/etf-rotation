"""ETF 主力轮动监测看板 — 主入口"""

import datetime

import streamlit as st

from data.fetcher import get_industry_etf_quotes
from analytics.rotation import compute_rs_matrix, compute_rotation_signal
from analytics.signals import build_signal_table, signal_label
from views.heatmap import render_heatmap
from views.shares import render_shares
from views.flow import render_flow

st.set_page_config(
    page_title="ETF 轮动监测",
    page_icon="📊",
    layout="wide",
)

st.title("📊 ETF 主力轮动监测看板")

# ---- 信号汇总 Dashboard ----
signal_table = None

with st.expander("🎯 今日轮动信号速览", expanded=True):
    # 先获取 ETF 行情（快速）
    with st.spinner("正在获取 ETF 行情数据..."):
        try:
            quotes_df = get_industry_etf_quotes()
        except Exception as e:
            st.error(f"ETF 行情加载失败: {e}")
            quotes_df = None

    # RS 计算（较慢，逐只拉历史）
    with st.spinner("正在计算板块相对强度（约30秒）..."):
        try:
            rs_df = compute_rs_matrix()
            rs_df = compute_rotation_signal(rs_df)
        except Exception as e:
            st.warning(f"RS 计算失败: {e}，将仅展示资金流信号")
            rs_df = None

    if quotes_df is not None and not quotes_df.empty:
        if rs_df is not None and not rs_df.empty:
            signal_table = build_signal_table(rs_df, quotes_df)
        else:
            # 无 RS 数据时，只用资金流构建简单信号
            from analytics.signals import score_fund_flow, compute_composite_score, signal_label as _sl
            rows = []
            for _, row in quotes_df.iterrows():
                flow_col = "主力净流入-净额(亿)"
                flow = row.get(flow_col, 0)
                if pd.isna(flow):
                    flow = 0
                fs = score_fund_flow(flow)
                comp = compute_composite_score(fs, 50.0)
                label, icon = _sl(comp)
                rows.append({
                    "板块": row.get("sector", ""),
                    "涨跌幅(%)": row.get("涨跌幅", ""),
                    "主力净流入(亿)": round(flow, 2) if flow else 0,
                    "综合评分": comp,
                    "信号": f"{icon} {label}",
                })
            import pandas as pd
            signal_table = pd.DataFrame(rows).sort_values("综合评分", ascending=False).reset_index(drop=True)

    if signal_table is not None and not signal_table.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🔴 强势板块 Top 5**")
            for _, row in signal_table.head(5).iterrows():
                score = row["综合评分"]
                label, icon = signal_label(score)
                st.markdown(
                    f"- **{row['板块']}** — {icon} {label} "
                    f"(评分:{score}, "
                    f"资金流:{row.get('主力净流入(亿)', 'N/A')}亿)"
                )

        with col2:
            st.markdown("**🔵 弱势板块 Top 5**")
            for _, row in signal_table.tail(5).iloc[::-1].iterrows():
                score = row["综合评分"]
                label, icon = signal_label(score)
                st.markdown(
                    f"- **{row['板块']}** — {icon} {label} "
                    f"(评分:{score}, "
                    f"资金流:{row.get('主力净流入(亿)', 'N/A')}亿)"
                )

        with st.expander("查看完整信号表"):
            st.dataframe(signal_table, width="stretch", hide_index=True)
    else:
        st.info("信号计算中，请稍候...")

# ---- Tab 页切换 ----
tab1, tab2, tab3 = st.tabs(["🔥 轮动热力图", "📦 份额变动", "💰 资金流向"])

with tab1:
    render_heatmap()

with tab2:
    render_shares()

with tab3:
    render_flow()

# ---- 底部信息 ----
st.divider()
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"数据更新时间: {now} | 数据源: 东方财富(AKShare) | 缓存: 实时5min / 历史1h")
