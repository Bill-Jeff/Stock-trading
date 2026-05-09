"""数据获取模块 — 通过AKShare获取实时行情和历史K线"""

# 绕过系统代理（Windows注册表中的代理会导致连接失败）
import requests
_orig_merge = requests.Session.merge_environment_settings
def _no_proxy_merge(self, *a, **kw):
    settings = _orig_merge(self, *a, **kw)
    settings["proxies"] = {}
    return settings
requests.Session.merge_environment_settings = _no_proxy_merge

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta


def fetch_realtime_quotes():
    """获取全A股实时行情，返回DataFrame"""
    print("正在获取实时行情数据...")
    df = ak.stock_zh_a_spot_em()
    # 统一列名
    df = df.rename(columns={
        "代码": "code",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "change_pct",
        "成交额": "amount",
        "换手率": "turnover",
        "总市值": "total_market_cap",
        "流通市值": "float_market_cap",
        "60日涨跌幅": "change_60d",
        "量比": "volume_ratio",
        "今开": "open",
        "昨收": "pre_close",
    })
    # 转换数值列
    for col in ["price", "change_pct", "amount", "turnover", "float_market_cap",
                "total_market_cap", "change_60d", "volume_ratio", "open", "pre_close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # 计算竞价涨幅: (开盘价 - 昨收) / 昨收 * 100
    df["auction_pct"] = ((df["open"] - df["pre_close"]) / df["pre_close"] * 100).round(2)
    return df


def fetch_history(code, days=120):
    """获取单只股票历史日K线，返回DataFrame"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
        })
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def fetch_list_date(code):
    """获取股票上市日期"""
    try:
        df = ak.stock_individual_info_em(symbol=code)
        row = df[df["item"] == "上市时间"]
        if not row.empty:
            return row.iloc[0]["value"]
    except Exception:
        pass
    return None
