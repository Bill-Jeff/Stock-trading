"""临时脚本：用 akshare+baostock 混合数据跑竞价涨幅筛选"""

import requests
_orig = requests.Session.merge_environment_settings
def _np(self, *a, **kw):
    s = _orig(self, *a, **kw)
    s['proxies'] = {}
    return s
requests.Session.merge_environment_settings = _np

import akshare as ak
import baostock as bs
import pandas as pd

# ===== 第一步：akshare 初步过滤 =====
print("正在获取行情数据...")
df = ak.stock_zh_a_spot()

# 只要A股（去掉bj北交所）
df = df[~df['代码'].str.startswith('bj')]
print(f"A股总数: {len(df)}")

# 数值转换
for col in ['今开', '昨收', '最新价', '成交额']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 排除价格为0
df = df[df['最新价'] > 0]

# 竞价涨幅
df['auction_pct'] = ((df['今开'] - df['昨收']) / df['昨收'] * 100).round(2)

# 竞价涨幅 1%~5%
df = df[(df['auction_pct'] >= 1.0) & (df['auction_pct'] <= 5.0)]
print(f"竞价涨幅1-5%: {len(df)}")

# 成交额 > 1000万
df = df[df['成交额'] >= 1000 * 10000]
print(f"成交额>1000万: {len(df)}")

# 排除ST
df = df[~df['名称'].str.contains('ST', na=False)]

# 排除科创板(688)、创业板(300/301)
code_clean = df['代码'].str.replace(r'^(sh|sz)', '', regex=True)
df = df[~code_clean.str.startswith('688')]
df = df[~code_clean.str.startswith('300')]
df = df[~code_clean.str.startswith('301')]
print(f"排除ST/科创/创业板: {len(df)}")

# 转换代码格式（sh600000 → sh.600000）
df['bs_code'] = df['代码'].str[:2] + '.' + df['代码'].str[2:]

candidates = df[['bs_code', '名称', '今开', '昨收', '最新价', 'auction_pct', '成交额']].copy()
candidates.columns = ['code', 'name', 'open', 'pre_close', 'close', 'auction_pct', 'amount']
print(f"\n初步候选: {len(candidates)} 只")

# ===== 第二步：baostock 查换手率 =====
print("\n正在查询换手率...")
bs.login()

results = []
for i, row in candidates.iterrows():
    code = row['code']
    rs = bs.query_history_k_data_plus(code,
        'date,code,open,close,amount,turn,isST',
        start_date='2026-05-08', end_date='2026-05-08',
        frequency='d', adjustflag='2')
    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    if rows:
        r = dict(zip(rs.fields, rows[0]))
        turn = float(r['turn']) if r['turn'] else 0
        is_st = r['isST']
        results.append({
            'code': code,
            'name': row['name'],
            'open': row['open'],
            'pre_close': row['pre_close'],
            'close': row['close'],
            'auction_pct': row['auction_pct'],
            'amount': row['amount'],
            'turn': turn,
            'isST': is_st,
        })
    print(f"  {len(results)}/{len(candidates)}", end='\r')

print()
bs.logout()

df_result = pd.DataFrame(results)
print(f"获取到 {len(df_result)} 只数据")

# 换手率 > 2%
df_result = df_result[df_result['turn'] > 2.0]
print(f"换手率>2%: {len(df_result)}")

# 排除ST
df_result = df_result[df_result['isST'] != '1']
print(f"排除ST后: {len(df_result)}")

# ===== 第三步：均线多头检查 =====
print("\n正在检查均线...")
# 获取历史K线做均线
bs.login()
final = []
for i, row in df_result.iterrows():
    rs = bs.query_history_k_data_plus(row['code'],
        'date,close',
        start_date='2025-11-01', end_date='2026-05-08',
        frequency='d', adjustflag='2')
    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    if len(rows) < 60:
        continue
    closes = pd.DataFrame(rows, columns=rs.fields)['close'].astype(float)
    ma5 = closes.rolling(5).mean().iloc[-1]
    ma10 = closes.rolling(10).mean().iloc[-1]
    ma20 = closes.rolling(20).mean().iloc[-1]
    ma60 = closes.rolling(60).mean().iloc[-1]
    if ma5 > ma10 > ma20 > ma60:
        divergence = round((ma5 - ma60) / ma60 * 100, 2)
        final.append({
            'code': row['code'],
            'name': row['name'],
            'open': row['open'],
            'pre_close': row['pre_close'],
            'close': row['close'],
            'auction_pct': row['auction_pct'],
            'amount': row['amount'],
            'turn': row['turn'],
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'divergence': divergence,
        })
    print(f"  检查 {len(final)} 入选 / {i}", end='\r')

bs.logout()
print()

df_final = pd.DataFrame(final)
print(f"\n最终入选: {len(df_final)} 只")
if not df_final.empty:
    df_final = df_final.sort_values('auction_pct', ascending=False)
    for _, r in df_final.iterrows():
        amount_w = round(r['amount'] / 10000, 0)
        print(f"  {r['name']:8s} {r['code']}  竞价{r['auction_pct']:+.1f}%  金额{amount_w:.0f}万  换手{r['turn']:.1f}%  MA发散{r['divergence']}%")
