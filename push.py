"""推送模块 — 钉钉机器人推送分析报告"""

import json
import hmac
import hashlib
import base64
import time
import urllib.parse
from datetime import datetime

import requests


def build_report(results):
    """构建分析报告文本"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"**红杉选股 — {today}**\n"]
    lines.append("筛选条件: 竞价涨幅1-5% | 金额>1000万 | 换手>2% | 市值50-200亿 | 均线多头\n")

    if not results:
        lines.append("今日无符合条件的股票。")
        return "\n".join(lines)

    lines.append("| 股票 | 代码 | 现价 | 涨幅 | 金额(万) | 换手率 | 市值(亿) | 均线状态 | 趋势强度 |")
    lines.append("|------|------|------|------|----------|--------|----------|----------|----------|")

    for r in results:
        amount_wan = round(r["amount"] / 10000, 0)
        cap_yi = round(r["float_market_cap"] / 1e8, 1)
        mas = r["mas"]
        periods = sorted([int(k.replace("MA", "")) for k in mas.keys()])
        ma_str = " > ".join([f"MA{p}({mas[f'MA{p}']:.2f})" for p in periods])
        change_str = f"+{r['change_pct']:.1f}%" if r["change_pct"] >= 0 else f"{r['change_pct']:.1f}%"
        lines.append(
            f"| {r['name']} | {r['code']} | {r['price']:.2f} | {change_str} | "
            f"{amount_wan:.0f} | {r['turnover']:.1f}% | {cap_yi} | {ma_str} | {r['ma_divergence']}% |"
        )

    lines.append(f"\n共 **{len(results)}** 只符合条件")
    return "\n".join(lines)


def push_dingtalk(text, webhook, secret=""):
    """发送钉钉机器人消息"""
    if "YOUR_TOKEN_HERE" in webhook:
        print("钉钉webhook未配置，跳过推送。报告内容：")
        print(text)
        return False

    url = webhook

    # 加签
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{webhook}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "红杉选股",
            "text": text,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            print("钉钉推送成功")
            return True
        else:
            print(f"钉钉推送失败: {result}")
            return False
    except Exception as e:
        print(f"钉钉推送异常: {e}")
        return False


def push_wecom(text, webhook):
    """发送企微机器人消息"""
    if not webhook:
        print("企微webhook未配置，跳过推送。")
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": text,
        },
    }

    try:
        resp = requests.post(webhook, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            print("企微推送成功")
            return True
        else:
            print(f"企微推送失败: {result}")
            return False
    except Exception as e:
        print(f"企微推送异常: {e}")
        return False
