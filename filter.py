"""筛选模块 — 条件过滤 + 均线多头排列判断"""

import pandas as pd
from datetime import datetime, timedelta
from fetcher import fetch_history, fetch_list_date


def apply_hard_filters(df, config):
    """硬条件过滤：涨幅、金额、换手率、市值、ST、科创板"""
    s = config["screen"]

    # 竞价涨幅 1%~5%（开盘价相对昨收的涨幅）
    df = df[(df["auction_pct"] >= s["auction_change_pct_min"]) & (df["auction_pct"] <= s["auction_change_pct_max"])]

    # 成交额 > 1000万（amount单位是元，转万元比较）
    df = df[df["amount"] >= s["auction_amount_min"] * 10000]

    # 换手率 > 2%
    df = df[df["turnover"] >= s["turnover_min"]]

    # 流通市值 50亿~200亿（float_market_cap单位是元）
    min_cap = s["float_market_cap_min"] * 1e8
    max_cap = s["float_market_cap_max"] * 1e8
    df = df[(df["float_market_cap"] >= min_cap) & (df["float_market_cap"] <= max_cap)]

    # 排除ST
    df = df[~df["name"].str.contains("ST", na=False)]

    # 排除科创板（代码688开头）
    df = df[~df["code"].str.startswith("688")]

    # 排除创业板（代码300、301开头）
    df = df[~df["code"].str.startswith("300")]
    df = df[~df["code"].str.startswith("301")]

    # 排除北交所（代码8开头）
    df = df[~df["code"].str.startswith("8")]

    # 排除价格为0或NaN
    df = df[df["price"] > 0]

    return df


def check_ma_bullish(close_series, periods=[5, 10, 20, 60]):
    """检查均线多头排列：MA5 > MA10 > MA20 > MA60"""
    if len(close_series) < max(periods):
        return False, {}
    mas = {}
    for p in periods:
        mas[f"MA{p}"] = close_series.rolling(window=p).mean().iloc[-1]
    # 多头排列
    values = [mas[f"MA{p}"] for p in periods]
    is_bullish = all(values[i] > values[i + 1] for i in range(len(values) - 1))
    return is_bullish, mas


def calc_ma_divergence(mas, periods=[5, 10, 20, 60]):
    """计算均线发散程度（趋势强度）"""
    values = [mas[f"MA{p}"] for p in periods]
    if values[-1] == 0:
        return 0
    return round((values[0] - values[-1]) / values[-1] * 100, 2)


def filter_new_stocks(df, min_days=60):
    """排除上市不足N天的新股（采样检查）"""
    cutoff = datetime.now() - timedelta(days=min_days)
    # 采样前50只检查上市日期，避免全量查询太慢
    sample = df.head(50)
    new_codes = set()
    for _, row in sample.iterrows():
        list_date = fetch_list_date(row["code"])
        if list_date:
            try:
                ld = datetime.strptime(str(list_date), "%Y-%m-%d")
                if ld > cutoff:
                    new_codes.add(row["code"])
            except ValueError:
                pass
    if new_codes:
        df = df[~df["code"].isin(new_codes)]
    return df


def screen_stocks(df, config):
    """完整筛选流程，返回筛选结果列表"""
    print(f"原始股票数: {len(df)}")

    # 硬条件过滤
    df = apply_hard_filters(df, config)
    print(f"硬条件过滤后: {len(df)}")

    # 排除新股（采样检查）
    df = filter_new_stocks(df, config["screen"]["min_listing_days"])
    print(f"排除新股后: {len(df)}")

    if df.empty:
        return []

    # 均线多头排列筛选
    results = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        code = row["code"]
        print(f"  检查均线 [{i+1}/{total}]: {code} {row['name']}", end="")
        hist = fetch_history(code, days=120)
        if hist.empty or len(hist) < 60:
            print(" — 数据不足，跳过")
            continue
        is_bullish, mas = check_ma_bullish(hist["close"])
        if is_bullish:
            divergence = calc_ma_divergence(mas)
            results.append({
                "code": code,
                "name": row["name"],
                "price": row["price"],
                "change_pct": row["change_pct"],
                "amount": row["amount"],
                "turnover": row["turnover"],
                "float_market_cap": row["float_market_cap"],
                "volume_ratio": row.get("volume_ratio", 0),
                "change_60d": row.get("change_60d", 0),
                "mas": mas,
                "ma_divergence": divergence,
            })
            print(f" — 均线多头 [OK] (发散{divergence}%)")
        else:
            print(" — 非多头，跳过")

    print(f"最终入选: {len(results)} 只")
    return results
