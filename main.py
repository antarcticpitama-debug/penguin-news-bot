import feedparser
import requests
import json
import os
from bs4 import BeautifulSoup
from readability import Document
from langdetect import detect
from deep_translator import GoogleTranslator
from datetime import datetime

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

MAX_POSTS = 5
HISTORY_FILE = "history.json"

KEYWORDS = ["penguin", "ペンギン"]

# -------------------------
# 共通処理
# -------------------------

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def contains_penguin(text):
    text = text.lower()
    return any(k.lower() in text for k in KEYWORDS)

# -------------------------
# 本文取得
# -------------------------

def fetch_article_text(url):
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0"
        })
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")
        return text.strip()[:2000]
    except:
        return ""

# -------------------------
# 翻訳
# -------------------------

def translate_to_japanese(text):
    try:
        lang = detect(text)
        if lang != "ja":
            return GoogleTranslator(source="auto", target="ja").translate(text)
        return text
    except:
        return text

# -------------------------
# 要約（無料簡易）
# -------------------------

def summarize_text(text):
    sentences = text.split("。")
    summary = "。".join(sentences[:3])
    return summary.strip() + "。"

# -------------------------
# Discord投稿
# -------------------------

def post_to_discord(title, summary, url):
    message = f"""📰 **ペンギンニュース**

**タイトル**
{title}

**要約**
{summary}

🔗 {url}
"""

    if len(message) > 1900:
        message = message[:1900]

    requests.post(DISCORD_WEBHOOK, json={"content": message})

# -------------------------
# メイン処理
# -------------------------

def main():
    history = load_json(HISTORY_FILE)
    posted_urls = [h["url"] for h in history]

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    post_count = 0

    for source in sources:
        feed = feedparser.parse(source["url"])

        for entry in feed.entries:
            if entry.link in posted_urls:
                continue

            title = entry.title
            if not contains_penguin(title):
                continue

            text = fetch_article_text(entry.link)
            if not text:
                continue

            text = translate_to_japanese(text)
            summary = summarize_text(text)

            post_to_discord(title, summary, entry.link)

            history.append({
                "title": title,
                "url": entry.link,
                "date": datetime.utcnow().isoformat()
            })

            save_json(HISTORY_FILE, history)

            post_count += 1
            if post_count >= MAX_POSTS:
                return

if __name__ == "__main__":
    main()
