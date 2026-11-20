import re
import time
import html as html_lib
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# آیدی کانال خودت را بدون @ اینجا بنویس
CHANNEL = "pricepashapay"

# کش ۳۰ ثانیه‌ای برای سرعت بالا
CACHE = {"time": 0, "html": ""}


def clean_text(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2066-\u2069]", "", text)
    # تبدیل اعداد فارسی و عربی به انگلیسی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i in range(10):
        text = text.replace(persian_digits[i], str(i)).replace(arabic_digits[i], str(i))
    text = text.replace("ي", "ی").replace("ك", "ک")
    return text


def extract(text: str, pattern: str, flags=0) -> str:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else "---"


def fetch_channel_text():
    url = f"https://t.me/s/{CHANNEL}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    page_html = resp.text

    matches = re.findall(r'<div class="tgme_widget_message_text[^>]*>([\s\S]*?)</div>', page_html)
    if not matches:
        return None

    for raw_msg in reversed(matches):
        candidate = clean_text(raw_msg)
        if "XAUUSD" in candidate or "BTCUSDT" in candidate or "گرم طلا" in candidate:
            return candidate

    return clean_text(matches[-1])


def render_cards(items, is_dollar=False):
    cards_html = []
    for item in items:
        if is_dollar:
            price_block = f'<span class="currency-prefix">$</span><span class="price">{item["price"]}</span>'
        else:
            price_block = f'<span class="price">{item["price"]}</span><span class="currency-suffix">{item["unit"]}</span>'

        cards_html.append(f'''
        <div class="card">
          <div class="card-top">
            <div class="icon-box" style="color: {item["color"]}; background: {item["color"]}18; border-color: {item["color"]}33;">
              {item["icon"]}
            </div>
            <div class="meta">
              <div class="title">{item["title"]}</div>
              <div class="sub">{item["sub"]}</div>
            </div>
          </div>
          <div class="price-row" dir="ltr">
            {price_block}
          </div>
        </div>
        ''')
    return "".join(cards_html)


@app.route("/")
def index():
    is_debug = request.args.get("debug") == "1"

    try:
        now = time.time()
        if not is_debug and CACHE["html"] and (now - CACHE["time"] < 30):
            return Response(CACHE["html"], mimetype="text/html; charset=utf-8")

        text = fetch_channel_text()
        if not text:
            return Response("پیامی در کانال پیدا نشد. مطمئن شو آیدی درست است و کانال عمومی است.", mimetype="text/plain; charset=utf-8")

        if is_debug:
            return Response("=== RAW EXTRACTED TEXT ===\n\n" + text, mimetype="text/plain; charset=utf-8")

        date_str = extract(text, r"تاریخ[^\d\n]*([\d/]+)")
        time_str = extract(text, r"ساعت[^\d\n]*([\d:]+)")

        iran_items = [
            {
                "title": "تتر", "sub": "USDT / IRT",
                "price": extract(text, r"تتر[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#26A17B",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>'
            },
            {
                "title": "گرم طلا ۱۸ عیار", "sub": "GOLD 18K",
                "price": extract(text, r"گرم طلا\s*18[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#F59E0B",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18h12l-1.5-6h-9L6 18z"/><path d="M8.5 12h7l-1-4h-5l-1 4z"/></svg>'
            },
            {
                "title": "آب شده جهانی", "sub": "MELTED GOLD",
                "price": extract(text, r"آب\s*شده\s*جهانی[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#EAB308",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="13" width="18" height="6" rx="1"/><path d="M6 13l2-6h8l2 6"/></svg>'
            },
            {
                "title": "سکه تمام جدید", "sub": "EMAMI COIN",
                "price": extract(text, r"سکه\s*تمام\s*جدید[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#FBBF24",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/></svg>'
            },
            {
                "title": "سکه تمام قدیم", "sub": "BAHAR AZADI",
                "price": extract(text, r"سکه\s*تمام\s*قدیم[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#D97706",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M9 12h6"/></svg>'
            },
            {
                "title": "نیم سکه", "sub": "HALF COIN",
                "price": extract(text, r"نیم\s*سکه[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#FCD34D",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8"/><path d="M12 4v16"/></svg>'
            },
            {
                "title": "ربع سکه", "sub": "QUARTER COIN",
                "price": extract(text, r"ربع\s*سکه[^\d\n]*([\d,]+)"), "unit": "تومان", "color": "#FDE68A",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><path d="M12 12V5a7 7 0 0 1 7 7h-7z"/></svg>'
            },
        ]

        global_items = [
            {
                "title": "انس جهانی طلا", "sub": "XAUUSD",
                "price": extract(text, r"XAUUSD[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#F59E0B",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7l3-7z"/></svg>'
            },
            {
                "title": "بیت‌کوین", "sub": "BTCUSDT",
                "price": extract(text, r"BTCUSDT[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#F7931A",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 5h6a3.5 3.5 0 0 1 0 7H7V5z"/><path d="M7 12h7a3.5 3.5 0 0 1 0 7H7v-7z"/><path d="M10 3v2M14 3v2M10 19v2M14 19v2"/></svg>'
            },
            {
                "title": "اتریوم", "sub": "ETHUSDT",
                "price": extract(text, r"ETHUSDT[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#627EEA",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L5 12l7 4 7-4-7-10z"/><path d="M5 12l7 10 7-10"/></svg>'
            },
            {
                "title": "شاخص داوجونز", "sub": "US30",
                "price": extract(text, r"US30[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#38BDF8",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>'
            },
            {
                "title": "شاخص نزدک", "sub": "NDX",
                "price": extract(text, r"NDX[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#0EA5E9",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-6"/></svg>'
            },
            {
                "title": "یورو / دلار", "sub": "EURUSD",
                "price": extract(text, r"EURUSD[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#6366F1",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 6.5A6.5 6.5 0 1 0 17 17.5"/><path d="M5 10h9M5 14h9"/></svg>'
            },
            {
                "title": "نفت خام آمریکا", "sub": "USOIL",
                "price": extract(text, r"USOIL[^\d\n]*([\d,\.]+)", re.IGNORECASE), "unit": "$", "color": "#94A3B8",
                "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>'
            },
        ]

        tg_icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.665 3.717l-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.579.192l-8.533 7.701h-.002l.002.001-.314 4.692c.46 0 .663-.211.921-.46l2.211-2.15 4.599 3.397c.848.467 1.457.227 1.668-.785l3.019-14.228c.309-1.239-.473-1.8-1.282-1.434z"/></svg>'

        page = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="60">
  <title>xPrice | نرخ لحظه‌ای بازار</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600;700;800&family=Vazirmatn:wght@400;500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #09090b;
      --card-bg: rgba(24, 24, 27, 0.72);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(255, 255, 255, 0.16);
      --text-main: #fafafa;
      --text-muted: #a1a1aa;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Vazirmatn', system-ui, sans-serif;
      background-color: var(--bg);
      background-image: radial-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px);
      background-size: 24px 24px;
      color: var(--text-main);
      min-height: 100vh;
      padding: 32px 20px 48px;
    }}
    .container {{ max-width: 1040px; margin: 0 auto; }}
    header {{
      display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
      gap: 16px; margin-bottom: 36px; padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
    }}
    .brand h1 {{ font-size: 22px; font-weight: 800; letter-spacing: -0.3px; }}
    .brand p {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
    .center-logo {{
      font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 800;
      letter-spacing: -1px; direction: ltr; user-select: none; color: var(--text-main);
      display: inline-flex; align-items: center; justify-self: center;
      padding: 4px 16px; border-radius: 12px;
      background: rgba(255, 255, 255, 0.03); border: 1px solid var(--card-border);
    }}
    .center-logo .x-accent {{ color: #38bdf8; text-shadow: 0 0 18px rgba(56, 189, 248, 0.65); }}
    .status-pill {{
      justify-self: end; display: inline-flex; align-items: center; gap: 10px;
      background: var(--card-bg); border: 1px solid var(--card-border);
      backdrop-filter: blur(12px); padding: 8px 14px;
      border-radius: 999px; font-size: 13px; color: var(--text-muted);
    }}
    @media (max-width: 768px) {{
      header {{ grid-template-columns: 1fr; text-align: center; }}
      .center-logo {{ order: -1; }}
      .status-pill {{ justify-self: center; }}
    }}
    .dot {{
      width: 8px; height: 8px; border-radius: 50%;
      background: #10b981; box-shadow: 0 0 10px #10b981;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}
    .time-mono {{ font-family: 'JetBrains Mono', monospace; color: var(--text-main); font-weight: 600; direction: ltr; }}
    .section-title {{
      font-size: 15px; font-weight: 700; color: var(--text-muted);
      margin: 28px 0 14px; display: flex; align-items: center; gap: 8px;
    }}
    .section-title::before {{ content: ""; width: 4px; height: 16px; border-radius: 4px; background: #38bdf8; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }}
    .card {{
      background: var(--card-bg); border: 1px solid var(--card-border);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border-radius: 16px; padding: 18px; display: flex;
      flex-direction: column; justify-content: space-between; gap: 18px;
      transition: border-color 0.2s ease, transform 0.2s ease;
    }}
    .card:hover {{ border-color: var(--card-hover); transform: translateY(-2px); }}
    .card-top {{ display: flex; align-items: center; gap: 12px; }}
    .icon-box {{
      width: 40px; height: 40px; border-radius: 12px; border: 1px solid;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }}
    .icon-box svg {{ width: 20px; height: 20px; }}
    .title {{ font-size: 14px; font-weight: 700; color: var(--text-main); }}
    .sub {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); margin-top: 2px; }}
    .price-row {{
      display: flex; align-items: baseline; justify-content: flex-end;
      gap: 6px; padding-top: 12px; border-top: 1px dashed rgba(255, 255, 255, 0.07);
    }}
    .price {{
      font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 700;
      font-variant-numeric: tabular-nums; color: var(--text-main); letter-spacing: -0.5px;
    }}
    .currency-prefix {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #10b981; font-weight: 700; }}
    .currency-suffix {{ font-family: 'Vazirmatn', sans-serif; font-size: 12px; color: var(--text-muted); }}
    footer {{
      margin-top: 52px; padding-top: 24px; border-top: 1px solid var(--card-border);
      display: flex; flex-wrap: wrap; justify-content: center; align-items: center;
      gap: 12px; direction: ltr; font-family: 'JetBrains Mono', monospace;
    }}
    .footer-copy {{ font-size: 12px; color: var(--text-muted); letter-spacing: 0.2px; }}
    .footer-links {{ display: inline-flex; align-items: center; gap: 8px; }}
    .tg-pill {{
      display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
      border-radius: 999px; background: var(--card-bg); border: 1px solid var(--card-border);
      backdrop-filter: blur(10px); color: var(--text-main); text-decoration: none;
      font-size: 12px; font-weight: 500; transition: all 0.2s ease;
    }}
    .tg-pill svg {{ width: 13px; height: 13px; color: #38bdf8; transition: transform 0.2s ease; }}
    .tg-pill:hover {{ border-color: rgba(56, 189, 248, 0.45); background: rgba(56, 189, 248, 0.1); transform: translateY(-1px); }}
    .tg-pill:hover svg {{ transform: scale(1.1); }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>نرخ لحظه‌ای بازار</h1>
        <p>بروزرسانی خودکار هر ۶۰ ثانیه</p>
      </div>
      <div class="center-logo"><span class="x-accent">x</span>Price</div>
      <div class="status-pill">
        <span class="dot"></span>
        <span>آخرین بروزرسانی:</span>
        <span class="time-mono">{date_str} - {time_str}</span>
      </div>
    </header>

    <div class="section-title">بازار ایران (تومان)</div>
    <div class="grid">{render_cards(iran_items, False)}</div>

    <div class="section-title">بازار جهانی و کریپتو (دلار)</div>
    <div class="grid">{render_cards(global_items, True)}</div>

    <footer>
      <span class="footer-copy">c7yas & PashaPay · Copyright © 2026</span>
      <div class="footer-links">
        <a href="https://t.me/c7yas" target="_blank" rel="noopener noreferrer" class="tg-pill">{tg_icon}<span>c7yas</span></a>
        <a href="https://t.me/PashaEpay" target="_blank" rel="noopener noreferrer" class="tg-pill">{tg_icon}<span>PashaPay</span></a>
      </div>
    </footer>
  </div>
</body>
</html>"""

        CACHE["time"] = now
        CACHE["html"] = page
        return Response(page, mimetype="text/html; charset=utf-8")

    except Exception as e:
        return Response(f"خطا در دریافت اطلاعات از تلگرام: {e}", status=500, mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
