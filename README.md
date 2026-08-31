# NDQ / 标普500监控与场内加仓提醒

这个项目同时监控 Nasdaq-100（Yahoo Finance 的 `^NDX`）和标普500（`^GSPC`）日线，不依赖 TradingView 警报。触发回撤信号后，按人民币金额提醒你使用场内 ETF 加仓；场外基金的日常定投继续由原平台执行。

同一个 GitHub Actions 工作流会并行运行两个监控任务，消息标题会标明 `NDQ` 或 `SP500`，避免混淆。

## 当前档位

- 回撤 10%：第一档，3,000 元
- 回撤 15%：第二档，5,000 元
- 回撤 20%：第三档，6,000 元
- 回撤 25% 且 MA60 连续三日收复：第四档，6,000 元

回撤口径与 Pine 脚本一致：当前收盘价相对前 252 个交易日最高收盘价的跌幅。程序只提醒“最新日线刚跨过阈值”的事件，因此不会每天重复通知；创新高后自然开启下一轮回撤信号。

## GitHub Actions 设置

1. 将本目录推送到一个 GitHub 仓库。
2. 在仓库 `Settings → Secrets and variables → Actions` 添加通知所需的 Secrets。
3. 工作流使用 UTC：`22:30 UTC` 约等于北京时间次日 `06:30`。GitHub Actions 可能有几分钟调度延迟；两个指数会分别检查。
4. 可以在 Actions 页面手动运行 `workflow_dispatch` 测试。

也支持可选的 Telegram：添加 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 两个 Secret 即可。

也支持可选的 SMTP 邮件。iCloud 配置如下：

```text
SMTP_HOST=smtp.mail.me.com
SMTP_PORT=587
SMTP_USERNAME=你的完整 iCloud 邮箱
SMTP_PASSWORD=Apple 生成的应用专用密码
EMAIL_FROM=你的完整 iCloud 邮箱
EMAIL_TO=接收提醒的邮箱
SMTP_USE_SSL=false
```

将这些值分别保存为 GitHub Actions Secrets；`SMTP_PASSWORD` 必须是 Apple 账户生成的“应用专用密码”，不能使用普通登录密码。其他邮箱只需替换 SMTP 主机、端口和账号参数。

## 本地测试

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 monitor.py
```

不要把 Bot Token、SMTP 密码或 GitHub Token 写进代码；全部放进 GitHub Secrets。
