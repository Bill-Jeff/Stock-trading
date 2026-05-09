"""主入口 — 量化选股"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "4"

import yaml
import sys
import time
from datetime import datetime

from fetcher import fetch_realtime_quotes
from filter import screen_stocks
from push import build_report, push_dingtalk, push_wecom


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_trading_day():
    """判断是否为交易日（排除周末+节假日）"""
    today = datetime.now().date()
    if today.weekday() >= 5:
        return False
    try:
        import holidays
        cn_holidays = holidays.CN(years=today.year)
        return today not in cn_holidays
    except ImportError:
        return True


def run_once(config):
    """执行一次完整的选股流程"""
    print(f"\n{'='*50}")
    print(f"红杉选股 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    if not is_trading_day():
        print("今日非交易日，跳过。")
        return

    # 1. 获取实时行情
    df = fetch_realtime_quotes()
    print(f"获取到 {len(df)} 只股票行情")

    # 2. 筛选
    results = screen_stocks(df, config)

    # 3. 构建报告
    report = build_report(results)
    print("\n" + report)

    # 4. 推送
    dingtalk = config.get("dingtalk", {})
    push_dingtalk(report, dingtalk.get("webhook", ""), dingtalk.get("secret", ""))

    wecom = config.get("wecom", {})
    push_wecom(report, wecom.get("webhook", ""))

    return results


def main():
    config = load_config()

    if "--daemon" in sys.argv:
        # 守护模式：每天指定时间运行
        run_time = config.get("schedule", {}).get("time", "09:30")
        print(f"守护模式启动: 每个交易日 {run_time} 运行")
        print("按 Ctrl+C 退出\n")
        while True:
            now = datetime.now().strftime("%H:%M")
            if now == run_time and is_trading_day():
                run_once(config)
                time.sleep(60)  # 避免同一分钟重复执行
            time.sleep(10)
    else:
        # 单次运行
        run_once(config)


if __name__ == "__main__":
    main()
