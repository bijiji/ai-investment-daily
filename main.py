"""AI 投资日报机器人"""

import os
import smtplib
import ssl
from datetime import datetime
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI

TICKERS = ["NVDA", "TSLA", "MSFT", "GOOGL", "ASML", "TSM"]
NEWS_PER_TICKER = 3
REPORT_TZ = ZoneInfo("Australia/Melbourne")


def report_now() -> datetime:
    """返回墨尔本时区的当前时间，用于日报日期与标题。"""
    return datetime.now(REPORT_TZ)


def parse_news_item(item: dict) -> dict:
    """兼容 yfinance 不同版本的新闻字段结构。"""
    if "content" in item and isinstance(item["content"], dict):
        content = item["content"]
        provider = content.get("provider", {})
        click_through = content.get("clickThroughUrl", {})
        return {
            "title": content.get("title", ""),
            "publisher": provider.get("displayName", "") if isinstance(provider, dict) else "",
            "link": click_through.get("url", "") if isinstance(click_through, dict) else "",
        }

    return {
        "title": item.get("title", ""),
        "publisher": item.get("publisher", ""),
        "link": item.get("link", ""),
    }


def fetch_stock_data() -> list[dict]:
    """获取股价与近期新闻。"""
    results = []

    for symbol in TICKERS:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        history = ticker.history(period="5d")

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        change_pct = None
        if price is not None and prev_close:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        news_items = [parse_news_item(item) for item in (ticker.news or [])[:NEWS_PER_TICKER]]

        results.append(
            {
                "symbol": symbol,
                "name": info.get("shortName") or info.get("longName") or symbol,
                "price": price,
                "currency": info.get("currency", "USD"),
                "change_pct": change_pct,
                "prev_close": prev_close,
                "volume": info.get("volume") or info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "recent_5d_close": history["Close"].tolist() if not history.empty else [],
                "news": news_items,
            }
        )

    return results


def format_data_for_prompt(stock_data: list[dict]) -> str:
    """将原始数据格式化为供 LLM 阅读的文本。"""
    lines = [f"报告日期：{report_now().strftime('%Y年%m月%d日')}", ""]

    for stock in stock_data:
        lines.append(f"## {stock['symbol']} - {stock['name']}")
        if stock["price"] is not None:
            change = f"（{stock['change_pct']:+.2f}%）" if stock["change_pct"] is not None else ""
            lines.append(f"现价：{stock['price']} {stock['currency']}{change}")
        if stock["prev_close"]:
            lines.append(f"昨收：{stock['prev_close']} {stock['currency']}")
        if stock["volume"]:
            lines.append(f"成交量：{stock['volume']:,}")
        if stock["market_cap"]:
            lines.append(f"市值：{stock['market_cap']:,} {stock['currency']}")
        if stock["fifty_two_week_high"] and stock["fifty_two_week_low"]:
            lines.append(
                f"52周区间：{stock['fifty_two_week_low']} - {stock['fifty_two_week_high']} {stock['currency']}"
            )
        if stock["recent_5d_close"]:
            closes = ", ".join(f"{c:.2f}" for c in stock["recent_5d_close"])
            lines.append(f"近5日收盘价：{closes}")

        if stock["news"]:
            lines.append("相关新闻：")
            for i, n in enumerate(stock["news"], 1):
                lines.append(f"  {i}. [{n['publisher']}] {n['title']}")
                if n["link"]:
                    lines.append(f"     {n['link']}")
        else:
            lines.append("相关新闻：暂无")

        lines.append("")

    return "\n".join(lines)


def generate_report(raw_text: str, client: OpenAI, model: str) -> str:
    """调用 OpenAI 生成中文投资日报。"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一位专业的投资分析师。请根据提供的股票数据和新闻，"
                    "撰写一份简洁的中文投资日报。要求：\n"
                    "1. 开头写今日市场概览（1-2段）\n"
                    "2. 逐只股票分析：价格变动、关键新闻、简要观点\n"
                    "3. 结尾写风险提示（投资有风险，仅供参考）\n"
                    "4. 使用 Markdown 格式，语言专业但易懂\n"
                    "5. 不要编造数据中不存在的信息"
                ),
            },
            {
                "role": "user",
                "content": f"请根据以下数据生成今日投资日报：\n\n{raw_text}",
            },
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


def send_email(subject: str, body: str) -> None:
    """通过 Gmail SMTP 发送邮件。"""
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL") or gmail_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient

    # 纯文本备用
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 简单 Markdown 转 HTML（保留换行）
    html_body = (
        "<html><body style='font-family: sans-serif; line-height: 1.6;'>"
        + body.replace("\n", "<br>")
        + "</body></html>"
    )
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipient, msg.as_string())


def main() -> None:
    load_dotenv()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("错误：请设置 OPENAI_API_KEY（本地 .env 或 GitHub Secrets）")

    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)

    print("正在获取股票数据与新闻...")
    stock_data = fetch_stock_data()
    raw_text = format_data_for_prompt(stock_data)

    print(f"正在调用 OpenAI ({model}) 生成日报...")
    report = generate_report(raw_text, client, model)

    today = report_now().strftime("%Y-%m-%d")
    subject = f"AI 投资日报 - {today}"

    print("正在发送邮件...")
    send_email(subject, report)

    print(f"完成！日报已发送至 {os.environ.get('RECIPIENT_EMAIL', os.environ['GMAIL_USER'])}")


if __name__ == "__main__":
    main()
