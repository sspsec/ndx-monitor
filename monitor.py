#!/usr/bin/env python3
"""监控 Nasdaq-100 回撤，并按人民币金额发送场内加仓提醒。"""

from __future__ import annotations

import datetime as dt
import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from statistics import mean
from typing import Any

import requests


LOOKBACK = 252
MA_CONFIRM = 60
STAGES = (
    (0.10, "第一档", 3000),
    (0.15, "第二档", 5000),
    (0.20, "第三档", 6000),
)
STAGE4_AMOUNT = 6000


@dataclass(frozen=True)
class DailyMetric:
    date: dt.date
    close: float
    reference_high: float
    drawdown: float
    ma60: float | None
    ma60_reclaim_3d: bool


def fetch_ndx() -> list[tuple[dt.date, float]]:
    """从 Yahoo Finance chart API 获取 ^NDX 日线收盘价。"""
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    params = {
        "period1": now - 5 * 365 * 24 * 60 * 60,
        "period2": now + 24 * 60 * 60,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    payload: dict[str, Any] | None = None
    errors: list[str] = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            response = requests.get(
                f"https://{host}/v8/finance/chart/%5ENDX",
                params=params,
                headers={"User-Agent": "ndx-monitor/1.0"},
                timeout=20,
            )
            response.raise_for_status()
            candidate = response.json()
            if (candidate.get("chart") or {}).get("result"):
                payload = candidate
                break
            errors.append(f"{host}: empty result")
        except Exception as exc:  # noqa: BLE001 - try the secondary endpoint
            errors.append(f"{host}: {exc}")
    if payload is None:
        raise RuntimeError("Yahoo Finance 获取 ^NDX 失败；" + " | ".join(errors))
    result = (payload.get("chart") or {}).get("result")
    item = result[0]
    timestamps = item.get("timestamp") or []
    quotes = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quotes.get("close") or []
    rows = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        day = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date()
        rows.append((day, float(close)))
    if len(rows) < LOOKBACK + 3:
        raise RuntimeError(f"有效日线不足，需要至少 {LOOKBACK + 3} 条，实际 {len(rows)} 条")
    return rows


def build_metrics(rows: list[tuple[dt.date, float]]) -> list[DailyMetric | None]:
    """按 Pine 脚本口径计算 252 日参考高点、回撤和 MA60。"""
    closes = [close for _, close in rows]
    metrics: list[DailyMetric | None] = [None] * len(rows)
    for i in range(LOOKBACK, len(rows)):
        reference_high = max(closes[i - LOOKBACK : i])
        drawdown = 1.0 - closes[i] / reference_high
        ma60 = mean(closes[i - MA_CONFIRM + 1 : i + 1]) if i >= MA_CONFIRM - 1 else None
        reclaim = False
        if i >= MA_CONFIRM + 1:
            reclaim = all(
                closes[j] > mean(closes[j - MA_CONFIRM + 1 : j + 1])
                for j in (i - 2, i - 1, i)
            )
        metrics[i] = DailyMetric(
            date=rows[i][0],
            close=closes[i],
            reference_high=reference_high,
            drawdown=drawdown,
            ma60=ma60,
            ma60_reclaim_3d=reclaim,
        )
    return metrics


def find_signals(metrics: list[DailyMetric | None]) -> list[tuple[str, int]]:
    """只检测最新一根日线的跨越事件，避免每天重复推送。"""
    current = metrics[-1]
    previous = metrics[-2]
    if current is None or previous is None:
        return []

    signals: list[tuple[str, int]] = []
    for threshold, name, amount in STAGES:
        if previous.drawdown < threshold <= current.drawdown:
            signals.append((name, amount))

    stage4_now = current.drawdown >= 0.25 and current.ma60_reclaim_3d
    stage4_before = previous.drawdown >= 0.25 and previous.ma60_reclaim_3d
    if stage4_now and not stage4_before:
        signals.append(("第四档", STAGE4_AMOUNT))
    return signals


def format_message(current: DailyMetric, signals: list[tuple[str, int]]) -> str:
    date_text = current.date.isoformat()
    total_amount = sum(amount for _, amount in signals)
    lines = [
        "📉 NDQ 纳斯达克100加仓提醒",
        "━━━━━━━━━━━━━━",
        f"🗓️ 美股日线：{date_text}",
        f"💵 指数收盘：{current.close:,.2f}",
        f"🏔️ 252日最高收盘：{current.reference_high:,.2f}",
        f"📊 当前回撤：{current.drawdown * 100:.2f}%",
        "",
    ]
    for name, amount in signals:
        suffix = "（需同时满足 MA60 三日确认）" if name == "第四档" else ""
        lines.append(f"🚦 触发{name}：场内加仓 {amount:,} 元{suffix}")
    lines.extend(
        [
            "",
            f"💰 本次建议合计：{total_amount:,} 元",
            "🛒 执行方式：场内 ETF 按金额买入",
            "📌 场外基金定投：按原计划执行",
            "⚠️ 这是策略提醒，请结合资金和风险承受能力判断。",
        ]
    )
    return "\n".join(lines)


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=20,
    )
    response.raise_for_status()


def send_email(message: str) -> None:
    """通过 SMTP 发送邮件；未配置完整 SMTP Secrets 时跳过。"""
    host = os.environ.get("SMTP_HOST", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    recipient = os.environ.get("EMAIL_TO", "").strip()
    if not all((host, username, password, recipient)):
        return

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT 必须是数字") from exc

    sender = os.environ.get("EMAIL_FROM", "").strip() or username
    subject = "NDQ 纳斯达克100加仓提醒"
    email = EmailMessage()
    email["From"] = formataddr(("NDQ 纳斯达克100加仓提醒", sender))
    email["To"] = recipient
    email["Subject"] = subject
    email.set_content(message)

    use_ssl = os.environ.get("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes"}
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as smtp:
            smtp.login(username, password)
            smtp.send_message(email)
        return

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(email)


def main() -> int:
    try:
        if os.environ.get("TEST_NOTIFICATION", "").strip().lower() in {"1", "true", "yes"}:
            message = (
                "📉 NDQ 纳斯达克100加仓提醒\n"
                "━━━━━━━━━━━━━━\n"
                f"🕒 北京时间：{dt.datetime.now(dt.timezone(dt.timedelta(hours=8))):%Y-%m-%d %H:%M:%S}\n"
                "🧪 这是测试通知，不代表当前已触发加仓档位。\n"
                "✅ Telegram 及已配置的邮件通知流程已正常触发。\n"
                "📡 后续只有达到策略信号时才会发送加仓提醒。"
            )
            send_telegram(message)
            send_email(message)
            print("TEST_NOTIFICATION_SENT")
            return 0

        rows = fetch_ndx()
        metrics = build_metrics(rows)
        current = metrics[-1]
        if current is None:
            raise RuntimeError("当前没有可用指标")
        signals = find_signals(metrics)
        print(
            f"NDX {current.date} close={current.close:.2f} "
            f"reference_high={current.reference_high:.2f} "
            f"drawdown={current.drawdown * 100:.2f}%"
        )
        if not signals:
            print("NO_SIGNAL")
            return 0
        message = format_message(current, signals)
        print(message)
        send_telegram(message)
        send_email(message)
        print("NOTIFICATION_SENT")
        return 0
    except Exception as exc:  # noqa: BLE001 - Actions 日志需要给出清晰错误
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
