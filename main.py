import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document
from langdetect import detect
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_URL = "あなたのWebhookURL"

KEYWORDS = ["ペンギン", "penguin"]

# -----------------------------
# 本文取得
# -----------------------------
def fetch_article_text(url):
    try:
        res = requests.get(url, timeout=10)
        doc = Document(res.text)
        soup = BeautifulSoup(doc.summary(), "html.parser")
        text = soup.get_text(separator="\n")
        return text.strip()
    except:
        return ""

# -----------------------------
# 翻訳（英語→日本語）
# -----------------------------
def translate_to_japanese(text):
    try:
        return GoogleTranslator(source="auto", target="ja").translate(text)
    except:
        return text

# -----------------------------
# 簡易要約（前400文字）
# -----------------------------
def summarize_text(text, max_length=400):
    text = text.replace("\n", " ")
    return text[:max_length] + "..." if len(text) > max_length else text

# -----------------------------
# 記事処理
# -----------------------------
def process_article(title, url):
    if not any(k.lower() in title.lower() for k in KEYWORDS):
        return None

    text = fetch_article_text(url)
    if not text:
        return None

    try:
        lang = detect(text)
    except:
        lang = "unknown"

    if lang == "en":
        text = translate_to_japanese(text)

    summary = summarize_text(text)

    return {
        "title": title,
        "url": url,
        "summary": summary
    }

# -----------------------------
# Discord投稿
# -----------------------------
def post_to_discord(article):
    message = f"""🐧 ペンギンニュース

📰 {article['title']}

📝 要約：
{article['summary']}

🔗 {article['url']}
"""
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

# -----------------------------
# RSS取得
# -----------------------------
def run():
    feeds = [
        "https://www3.nhk.or.jp/rss/news/cat0.xml",
        "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
    ]

    posted = 0
    max_posts = 5

    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if posted >= max_posts:
                return

            article = process_article(entry.title, entry.link)
            if article:
                post_to_discord(article)
                posted += 1


if __name__ == "__main__":
    run()
