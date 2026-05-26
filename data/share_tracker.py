"""ETF 份额快照追踪 — 每日保存份额，计算申赎变化趋势"""

import datetime
import pathlib

import pandas as pd

from data.etf_list import INDUSTRY_ETFS

_SNAP_FILE = pathlib.Path(__file__).parent.parent / ".cache" / "shares_snapshots.parquet"


def save_share_snapshot(quotes_df: pd.DataFrame) -> None:
    """从实时行情提取最新份额，追加到快照文件（同一天不重复写入）"""
    today = datetime.date.today().isoformat()
    codes = set(INDUSTRY_ETFS.values())

    rows = []
    for _, row in quotes_df.iterrows():
        code = row.get("代码", "")
        if code not in codes:
            continue
        shares = row.get("最新份额", None)
        if shares is None or pd.isna(shares):
            continue
        sector = row.get("sector", "")
        if not sector:
            sector = INDUSTRY_ETFS.get(code, code)
        rows.append({
            "date": today,
            "sector": sector,
            "code": code,
            "shares": float(shares),
        })

    if not rows:
        return

    new_df = pd.DataFrame(rows)

    if _SNAP_FILE.exists():
        existing = pd.read_parquet(_SNAP_FILE)
        # 去掉今天已有的快照（防止重复）
        existing = existing[existing["date"] != today]
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    _SNAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(_SNAP_FILE, index=False)


def get_share_changes(days: int = 5) -> pd.DataFrame:
    """计算各板块的份额变化
    返回 DataFrame: sector, code, shares_now, shares_prev, change, change_pct
    """
    if not _SNAP_FILE.exists():
        return pd.DataFrame(columns=["sector", "code", "shares_now", "shares_prev", "change", "change_pct"])

    df = pd.read_parquet(_SNAP_FILE)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    today = df["date"].max()
    # 找到 days 天前最近的快照日期
    target_date = today - datetime.timedelta(days=days)
    prev_dates = df[df["date"] <= target_date]["date"]
    prev_date = prev_dates.max() if not prev_dates.empty else None

    now_df = df[df["date"] == today][["sector", "code", "shares"]].rename(columns={"shares": "shares_now"})

    if prev_date is None:
        result = now_df.copy()
        result["shares_prev"] = 0.0
        result["change"] = 0.0
        result["change_pct"] = 0.0
        return result

    prev_df = df[df["date"] == prev_date][["code", "shares"]].rename(columns={"shares": "shares_prev"})

    result = now_df.merge(prev_df, on="code", how="left")
    result["shares_prev"] = result["shares_prev"].fillna(0)
    result["change"] = result["shares_now"] - result["shares_prev"]
    result["change_pct"] = result.apply(
        lambda r: round((r["change"] / r["shares_prev"]) * 100, 2) if r["shares_prev"] > 0 else 0, axis=1
    )

    return result[["sector", "code", "shares_now", "shares_prev", "change", "change_pct"]]


def get_snapshot_dates() -> list[str]:
    """返回所有已保存的快照日期"""
    if not _SNAP_FILE.exists():
        return []
    df = pd.read_parquet(_SNAP_FILE)
    return sorted(df["date"].unique())
