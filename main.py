import feedparser
import requests
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
HISTORY_FILE = "history.json"

PENGUIN_KEYWORDS = [
    "ペンギン",
    "penguin",
    "Penguin",
    "emperor penguin",
    "adelie",
    "gentoo",
    "chinstrap"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =======================
# 共通処理
# =======================

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_article_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)

        return text[:4000]
    except:
        return ""

def contains_penguin(text):
    text_lower = text.lower()
    return any(k.lower() in text_lower for k in PENGUIN_KEYWORDS)

def summarize(text):
    text = text.replace("\n", "")
    sentences = text.split("。")
    if len(sentences) > 3:
        return "。".join(sentences[:3]) + "。"
    return text[:300]

def post_to_discord(message):
    if len(message) > 1900:
        message = message[:1900]

    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except:
        pass

# =======================
# RSS処理
# =======================

def process_feed(source, history):
    feed = feedparser.parse(source["rss"])

    for entry in feed.entries[:5]:
        url = entry.link

        if any(h["url"] == url for h in history):
            continue

        article_text = fetch_article_text(url)

        if not article_text:
            continue

        if not contains_penguin(article_text):
            continue

        summary = summarize(article_text)

        message = f"""📰【{source['name']}】

■ タイトル
{entry.title}

■ 要約
{summary}

🔗 {url}
"""

        post_to_discord(message)

        history.append({
            "title": entry.title,
            "url": url,
            "date": datetime.utcnow().isoformat()
        })

        return history

    return history

# =======================
# メイン
# =======================

def main():
    history = load_history()

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    for source in sources:
        history = process_feed(source, history)

    save_history(history)

if __name__ == "__main__":
    main()
