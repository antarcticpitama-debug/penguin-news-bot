import feedparser
import requests
import json
import os
from bs4 import BeautifulSoup
from readability import Document
from datetime import datetime
from langdetect import detect
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
MAX_POSTS = 5
HISTORY_FILE = "history.json"

KEYWORDS = ["penguin", "ペンギン"]

# ----------------------------
# Utility
# ----------------------------

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def contains_penguin(text):
    if not text:
        return False
    text = text.lower()
    return any(k.lower() in text for k in KEYWORDS)

# ----------------------------
# Article fetch
# ----------------------------

def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=10, headers=headers)
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ")
        return text.strip()[:3000]
    except Exception as e:
        print("Fetch error:", e)
        return ""

# ----------------------------
# Translation
# ----------------------------

def translate_to_japanese(text):
    try:
        if not text:
            return ""
        lang = detect(text)
        if lang != "ja":
            return GoogleTranslator(source="auto", target="ja").translate(text)
        return text
    except:
        return text

# ----------------------------
# Simple summary
# ----------------------------

def summarize_text(text):
    if not text:
        return ""
    sentences = text.split("。")
    return "。".join(sentences[:3]).strip() + "。"

# ----------------------------
# Discord post
# ----------------------------

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

# ----------------------------
# Main
# ----------------------------

def main():
    if not DISCORD_WEBHOOK:
        print("Webhook not set")
        return

    history = load_history()
    posted_urls = {item["url"] for item in history}

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    post_count = 0

    for source in sources:
        print("Checking:", source["name"])
        feed = feedparser.parse(source["url"])

        for entry in feed.entries:
            link = entry.get("link")
            title = entry.get("title", "")

            if not link or link in posted_urls:
                continue

            # タイトル or 概要にペンギンが含まれるか
            summary_text = entry.get("summary", "")
            if not contains_penguin(title + summary_text):
                continue

            article_text = fetch_article_text(link)
            if not article_text:
                continue

            translated = translate_to_japanese(article_text)
            summary = summarize_text(translated)

            post_to_discord(title, summary, link)

            history.append({
                "title": title,
                "url": link,
                "date": datetime.utcnow().isoformat()
            })

            save_history(history)

            post_count += 1
            if post_count >= MAX_POSTS:
                print("Max posts reached")
                return

if __name__ == "__main__":
    main()
