"""建仓预测追踪 — 每日保存预测，用后续涨跌幅验证准确率"""

import datetime
import pathlib

import pandas as pd

from data.etf_list import INDUSTRY_ETFS
from data.fetcher import fetch_etf_history

_PRED_FILE = pathlib.Path(__file__).parent.parent / ".cache" / "prediction_snapshots.parquet"


def save_prediction_snapshot(predictions: list[dict]) -> None:
    """保存当日建仓预测快照（同一天不重复写入）"""
    today = datetime.date.today().isoformat()

    rows = []
    for p in predictions:
        sector = p.get("sector", "")
        code = INDUSTRY_ETFS.get(sector, "")
        if not code:
            continue
        rows.append({
            "date": today,
            "sector": sector,
            "code": code,
            "accum_score": p.get("accum_score", 0),
            "accum_label": p.get("accum_label", ""),
        })

    if not rows:
        return

    new_df = pd.DataFrame(rows)

    if _PRED_FILE.exists():
        existing = pd.read_parquet(_PRED_FILE)
        existing = existing[existing["date"] != today]
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    _PRED_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(_PRED_FILE, index=False)


def get_prediction_accuracy(forward_days: int = 5) -> dict:
    """计算建仓预测准确率"""
    if not _PRED_FILE.exists():
        return {"total": 0, "correct": 0, "accuracy": 0, "by_label": {}}

    df = pd.read_parquet(_PRED_FILE)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    today = datetime.date.today()

    # 只验证距今 >= forward_days 的预测（确保有足够后续数据）
    cutoff = today - datetime.timedelta(days=forward_days + 5)
    df = df[df["date"] <= cutoff]

    if df.empty:
        return {"total": 0, "correct": 0, "accuracy": 0, "by_label": {}}

    # 对每条预测，获取后续 forward_days 的涨跌幅
    results = []
    for _, row in df.iterrows():
        code = row["code"]
        pred_date = row["date"]
        score = row["accum_score"]
        label = row["accum_label"]

        try:
            hist = fetch_etf_history(code, forward_days + 60)
            hist["日期"] = pd.to_datetime(hist["日期"]).dt.date
            # 找到预测日期之后 forward_days 天的收盘价
            future = hist[hist["日期"] > pred_date].head(forward_days + 1)
            if len(future) < 2:
                continue
            start_price = float(future["收盘"].iloc[0])
            end_price = float(future["收盘"].iloc[-1])
            if start_price <= 0:
                continue
            actual_return = (end_price / start_price - 1) * 100

            # 判断预测是否正确
            if score >= 70:
                correct = actual_return > 1.0
            elif score >= 50:
                correct = actual_return > 0
            elif score < 30:
                correct = actual_return <= 0
            else:
                correct = False

            results.append({
                "label": label,
                "correct": correct,
                "actual_return": actual_return,
            })
        except Exception:
            continue

    if not results:
        return {"total": 0, "correct": 0, "accuracy": 0, "by_label": {}}

    total = len(results)
    correct = sum(1 for r in results if r["correct"])

    # 分档统计
    by_label = {}
    for r in results:
        lbl = r["label"]
        if lbl not in by_label:
            by_label[lbl] = {"total": 0, "correct": 0}
        by_label[lbl]["total"] += 1
        if r["correct"]:
            by_label[lbl]["correct"] += 1

    for lbl in by_label:
        t, c = by_label[lbl]["total"], by_label[lbl]["correct"]
        by_label[lbl]["accuracy"] = round(c / t * 100, 1) if t > 0 else 0

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
        "by_label": by_label,
    }
