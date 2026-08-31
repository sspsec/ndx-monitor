# NDQ / 标普500监控与场内加仓提醒

这是一个基于 GitHub Actions 的指数监控工具。它每天获取 Yahoo Finance 的美股日线数据，计算回撤和 MA60 条件，并在达到分档信号时通过 Telegram 和/或邮件提醒。

它不依赖 TradingView 警报，也不会自动下单：场内 ETF 需要你自行按金额买入，场外基金定投继续按原平台计划执行。

## 监控标的

| 名称 | Yahoo Finance 代码 | 用途 |
| --- | --- | --- |
| NDQ 纳斯达克100 | `^NDX` | 纳斯达克100方向参考 |
| SP500 标普500 | `^GSPC` | 标普500方向参考 |

两个标的在同一个工作流中并行检查，通知标题会明确标注 `NDQ` 或 `SP500`。

## 加仓规则

回撤定义为：当前收盘价相对前 **252 个交易日最高收盘价** 的跌幅。

| 触发条件 | 信号 | 建议场内加仓 |
| --- | --- | ---: |
| 回撤达到 10% | 第一档 | 3,000 元 |
| 回撤达到 15% | 第二档 | 5,000 元 |
| 回撤达到 20% | 第三档 | 6,000 元 |
| 回撤达到 25%，且 MA60 连续三日收复 | 第四档 | 6,000 元 |

程序只提醒“最新日线刚跨过阈值”的事件，避免每天重复发送。同一轮回撤创新高后会重新开始计算下一轮信号。

## 自动执行时间

GitHub Actions 使用 UTC，工作流配置为：

```text
周日到周四 22:30 UTC
= 北京时间周一到周五 06:30
```

该时间用于检查上一交易日的美股收盘数据。GitHub Actions 的实际启动可能延迟几分钟；美股周末或节假日没有新行情时，会使用最近一条可用日线。

工作流文件：`.github/workflows/monitor.yml`

## GitHub Secrets 配置

在仓库的 `Settings → Secrets and variables → Actions` 中添加以下变量。

### Telegram（可选）

```text
TELEGRAM_BOT_TOKEN=机器人 Token
TELEGRAM_CHAT_ID=接收消息的 Chat ID
```

### SMTP 邮件（可选）

iCloud 示例：

```text
SMTP_HOST=smtp.mail.me.com
SMTP_PORT=587
SMTP_USERNAME=你的完整 iCloud 邮箱
SMTP_PASSWORD=Apple 生成的应用专用密码
EMAIL_FROM=你的完整 iCloud 邮箱
EMAIL_TO=接收提醒的邮箱
SMTP_USE_SSL=false
```

`SMTP_PASSWORD` 必须是 Apple 账户生成的“应用专用密码”，不能填写 iCloud 普通登录密码。未配置完整的一种通知方式时，另一种仍可独立工作。

## 手动测试通知

进入仓库的 **Actions → Index ETF monitor → Run workflow**，将 `test_notification` 设为 `true` 后运行。由于工作流包含两个矩阵任务，会分别发送一条 NDQ 和一条 SP500 测试消息。

也可以在命令行触发：

```bash
gh workflow run monitor.yml -R sspsec/ndx-monitor -f test_notification=true
```

## 本地运行与测试

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v

# 默认检查 NDQ
python3 monitor.py

# 检查标普500
MARKET=sp500 python3 monitor.py
```

正常没有触发信号时会输出 `NO_SIGNAL`；触发信号时会打印完整提醒内容并发送已配置的通知。

## 注意事项

- Yahoo Finance 指数数据用于判断大方向，不等于国内 ETF 的实时价格。
- 国内 ETF 还会受到汇率、溢价/折价、管理费、交易时差和跟踪误差影响。
- 信号是策略提醒，不构成投资建议；实际买入前请结合 ETF 溢价、流动性和个人风险承受能力判断。
- 不要把 Bot Token、SMTP 密码、Apple 应用专用密码或 GitHub Token 写入代码；统一放进 GitHub Secrets。
