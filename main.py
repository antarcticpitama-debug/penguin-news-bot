import feedparser
import requests
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
HISTORY_FILE = "history.json"
MAX_POSTS_PER_RUN = 5

PENGUIN_KEYWORDS = [
    "ペンギン",
    "penguin",
    "emperor penguin",
    "adelie",
    "gentoo",
    "chinstrap"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


# =========================
# 共通処理
# =========================

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
        return text[:5000]
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
    requests.post(DISCORD_WEBHOOK, json={"content": message})


# =========================
# メイン処理
# =========================

def main():
    history = load_history()
    posted_urls = {h["url"] for h in history}

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    candidate_articles = []

    # ① 全RSS巡回
    for source in sources:
        feed = feedparser.parse(source["rss"])

        for entry in feed.entries:
            url = entry.link

            if url in posted_urls:
                continue

            published = None
            if hasattr(entry, "published"):
                try:
                    published = parsedate_to_datetime(entry.published)
                except:
                    published = datetime.utcnow()
            else:
                published = datetime.utcnow()

            candidate_articles.append({
                "source": source["name"],
                "title": entry.title,
                "url": url,
                "published": published
            })

    # ② 古い順に並び替え（取りこぼし防止）
    candidate_articles.sort(key=lambda x: x["published"])

    posts_made = 0

    # ③ 最大5件投稿
    for article in candidate_articles:
        if posts_made >= MAX_POSTS_PER_RUN:
            break

        article_text = fetch_article_text(article["url"])
        if not article_text:
            continue

        if not contains_penguin(article_text):
            continue

        summary = summarize(article_text)

        message = f"""📰【{article['source']}】

■ タイトル
{article['title']}

■ 要約
{summary}

🔗 {article['url']}
"""

        post_to_discord(message)

        history.append({
            "title": article["title"],
            "url": article["url"],
            "date": datetime.utcnow().isoformat()
        })

        posts_made += 1

    save_history(history)


if __name__ == "__main__":
    main()
