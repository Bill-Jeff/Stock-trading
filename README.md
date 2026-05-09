# 红杉选股 (Stock-trading)

> A 股选股系统 — 集合竞价阶段筛选 + 自动推送

## 简介

基于 AKShare（东方财富数据源）获取全 A 股实时行情，通过硬条件过滤 + 均线多头排列筛选符合条件的个股，自动推送至企业微信/钉钉。

## 筛选策略

1. **硬条件过滤**

   | 条件 | 默认值 |
   |------|--------|
   | 竞价涨幅 | 1% ~ 5%（开盘价相对昨收） |
   | 成交额 | > 1000 万 |
   | 换手率 | > 2% |
   | 流通市值 | 50 亿 ~ 200 亿 |
   | 排除 | ST、科创板(688)、创业板(300/301)、北交所(8开头)、次新股(不足60天) |

2. **均线多头排列**
   - 检查 MA5 > MA10 > MA20 > MA60 严格递增
   - 计算均线发散度（趋势强度）：`(MA5 - MA60) / MA60 × 100%`

## 快速开始

### 环境要求

- Python >= 3.10
- TA-Lib C 库（Python ta-lib 包的前置依赖）

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml：
#   - wecom.webhook: 企微机器人 webhook 地址
#   - dingtalk: 钉钉机器人配置（可选）
#   - screen.*: 筛选参数
```

### 运行

```bash
# 单次运行
python main.py

# 守护模式（每个交易日 09:25 自动运行）
python main.py --daemon
```

## 推送渠道

- **企业微信**：通过 webhook 推送 markdown 格式报告
- **钉钉**：支持加签验证

## 目录结构

```
├── main.py            # 入口，单次运行 / 守护模式
├── fetcher.py         # 数据获取（akshare，含代理绕过）
├── filter.py          # 筛选逻辑（硬过滤 + 均线多头）
├── push.py            # 推送（企微 + 钉钉）
├── config.yaml        # 配置文件
├── CLAUDE.md          # AI 辅助开发文档
├── result.txt         # 上次筛选结果缓存
└── run_baostock.py    # 临时脚本（周末备用数据源）
```

## License

MIT
