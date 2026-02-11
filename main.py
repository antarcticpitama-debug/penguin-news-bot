import feedparser
import requests
import json
import os
import tldextract
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=penguin&hl=en-US&gl=US&ceid=US:en"
]

HISTORY_FILE = "history.json"

# ===== ユーティリティ =====
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def get_domain_name(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

# ★ GoogleニュースURLを実URLへ変換
def resolve_url(google_url):
    try:
        response = requests.get(google_url, allow_redirects=True, timeout=10)
        return response.url
    except:
        return google_url

# ★ 本文取得（改良版）
def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)

        return text[:3000]
    except:
        return ""

# ★ 翻訳
def translate_to_japanese(text):
    if len(text) < 200:
        return ""
    try:
        return GoogleTranslator(source="auto", target="ja").translate(text)
    except:
        return text

# ★ 要約（少し改良）
def summarize_text(text):
    if not text:
        return "本文を取得できませんでした。"

    sentences = text.split("。")
    summary = "。".join(sentences[:3])

    return summary + "。"

# ===== 週まとめ判定 =====
def is_weekly_mode():
    return datetime.utcnow().weekday() == 6  # 日曜

# ===== 通常投稿処理 =====
def normal_mode():
    history = load_json(HISTORY_FILE)
    feed = feedparser.parse(RSS_FEEDS[0])

    for entry in feed.entries:

        # 重複防止
        if any(h["url"] == entry.link for h in history):
            continue

        # ★ 実URLへ変換
        real_url = resolve_url(entry.link)

        print("実URL:", real_url)

        text = fetch_article_text(real_url)

        if len(text) < 300:
            print("本文が短すぎるためスキップ")
            continue

        translated = translate_to_japanese(text)
        summary = summarize_text(translated)

        domain = get_domain_name(real_url)

        message = f"""📰 【ペンギンニュース】

■ タイトル
{entry.title}

■ ソース
{domain}

■ 要約
{summary}

🔗 {real_url}
"""

        if len(message) > 1900:
            message = message[:1900]

        requests.post(DISCORD_WEBHOOK, json={"content": message})

        history.append({
            "title": entry.title,
            "url": entry.link,
            "summary": summary,
            "date": datetime.utcnow().isoformat()
        })

        save_json(HISTORY_FILE, history)
        break

# ===== 週まとめ投稿 =====
def weekly_mode():
    history = load_json(HISTORY_FILE)
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    weekly_items = [
        h for h in history
        if datetime.fromisoformat(h["date"]) > one_week_ago
    ]

    if not weekly_items:
        return

    message = "🗓 【ペンギンニュース週間まとめ】\n\n"

    for i, item in enumerate(weekly_items[:5], 1):
        message += f"{i}. {item['title']}\n"
        message += f"{item['summary']}\n\n"

    if len(message) > 1900:
        message = message[:1900]

    requests.post(DISCORD_WEBHOOK, json={"content": message})

# ===== 実行 =====
if is_weekly_mode():
    weekly_mode()
else:
    normal_mode()
