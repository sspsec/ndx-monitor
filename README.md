# NDQ 监控与场内加仓提醒

这个项目监控 Nasdaq-100（Yahoo Finance 的 `^NDX`）日线，不依赖 TradingView 警报。触发回撤信号后，按人民币金额提醒你使用场内 ETF 加仓；场外基金的日常定投继续由原平台执行。

## 当前档位

- 回撤 10%：第一档，3,000 元
- 回撤 15%：第二档，5,000 元
- 回撤 20%：第三档，6,000 元
- 回撤 25% 且 MA60 连续三日收复：第四档，6,000 元

回撤口径与 Pine 脚本一致：当前收盘价相对前 252 个交易日最高收盘价的跌幅。程序只提醒“最新日线刚跨过阈值”的事件，因此不会每天重复通知；创新高后自然开启下一轮回撤信号。

## GitHub Actions 设置

1. 将本目录推送到一个 GitHub 仓库。
2. 在 iPhone 安装 ntfy，订阅一个随机、难猜的 topic。
3. 在仓库 `Settings → Secrets and variables → Actions` 添加 `NTFY_TOPIC`。
4. 工作流使用 UTC：`22:30 UTC` 约等于北京时间次日 `06:30`。GitHub Actions 可能有几分钟调度延迟。
5. 可以在 Actions 页面手动运行 `workflow_dispatch` 测试。

也支持可选的 Telegram：添加 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 两个 Secret 即可。

也支持可选的 SMTP 邮件：添加 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USERNAME`、`SMTP_PASSWORD`、`EMAIL_FROM`、`EMAIL_TO` 六个 Secret；如使用 465 端口 SSL，再添加 `SMTP_USE_SSL=true`。iCloud 邮箱可使用 `smtp.mail.me.com`、587 端口和 Apple 生成的应用专用密码，不能使用普通登录密码。

## 本地测试

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 monitor.py
```

不要把 Bot Token、ntfy topic 或 GitHub Token 写进代码；全部放进 GitHub Secrets。
