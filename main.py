import feedparser
import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
KEYWORD = "ペンギン"
HISTORY_FILE = "history.json"

# =========================
# 基本ユーティリティ
# =========================

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def post_to_discord(message):
    requests.post(DISCORD_WEBHOOK, json={"content": message})

# =========================
# 本文取得
# =========================

def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        # 不要タグ削除
        for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
            tag.decompose()

        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)

        text = re.sub(r"\s+", " ", text)

        return text[:4000]

    except:
        return ""

# =========================
# 無料ルールベース要約
# =========================

def summarize_text(text):

    if not text:
        return "本文を取得できませんでした。"

    # 文に分割
    sentences = re.split("。|\.|\n", text)

    # ペンギン関連文を優先
    penguin_sentences = [s for s in sentences if KEYWORD in s]

    if penguin_sentences:
        summary = "。".join(penguin_sentences[:3])
    else:
        summary = "。".join(sentences[:3])

    summary = summary.strip()

    if not summary:
        return "要約を生成できませんでした。"

    return summary + "。"

# =========================
# RSS処理
# =========================

def process_rss(source, history):

    feed = feedparser.parse(source["url"])

    for entry in feed.entries:

        if any(h["url"] == entry.link for h in history):
            continue

        article_text = fetch_article_text(entry.link)

        if KEYWORD not in entry.title and KEYWORD not in article_text:
            continue

        summary = summarize_text(article_text)

        message = f"""📰 【{source['name']}】

■ タイトル
{entry.title}

■ 要約
{summary}

🔗 {entry.link}
"""

        if len(message) > 1900:
            message = message[:1900]

        post_to_discord(message)

        history.append({
            "title": entry.title,
            "url": entry.link,
            "date": datetime.utcnow().isoformat()
        })

        save_json(HISTORY_FILE, history)

        break  # 1回の実行で1件投稿（安定化のため）

# =========================
# メイン
# =========================

def main():

    history = load_json(HISTORY_FILE)

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)["sources"]

    for source in sources:
        if source["type"] == "rss":
            process_rss(source, history)

if __name__ == "__main__":
    main()
