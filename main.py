import feedparser
import requests
import json
import os
import google.generativeai as genai
from bs4 import BeautifulSoup
from readability import Document
from datetime import datetime
from langdetect import detect
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
DISCORD_GOOGLENEWS_WEBHOOK = os.getenv("DISCORD_GOOGLENEWS_WEBHOOK")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MAX_POSTS_GOOGLE = 5
MAX_POSTS_NORMAL = 5
HISTORY_FILE = "history.json"

KEYWORDS = ["penguin", "ペンギン","南極","Antarctica"]

# ----------------------------
# Utility
# ----------------------------
def judge_penguin_news(title):
    """
    戻り値:
    "S" = 超重要
    "A" = 普通のペンギンニュース
    "N" = 関係なし
    """

    if not GEMINI_API_KEY:
        return "A"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
次のニュースタイトルを判定してください。

S：世界的に重要なペンギンニュース
（南極研究・大量死・新発見・保護・気候変動など）

A：普通のペンギンニュース
（水族館・動物園・赤ちゃん誕生など）

N：ペンギン無関係

タイトル:
{title}

S / A / N のどれか1文字だけ答えて
"""

        res = model.generate_content(prompt)
        ans = res.text.strip().upper()

        print("AI判定:", ans)

        if "S" in ans:
            return "S"
        if "A" in ans:
            return "A"
        return "N"

    except Exception as e:
        print("Gemini error:", e)
        return "A"

def summarize_title(title):
    if not title:
        return ""

    jp = translate_to_japanese(title)

    # 不要な媒体名を削除
    # 例: ～ - BBC News
    if " - " in jp:
        jp = jp.split(" - ")[0]

    # 日本語1行ニュース化
    # 長いときだけ短縮
    if len(jp) > 80:
        jp = jp[:80] + "..."

    # ニュースっぽく整形
    return jp


def extract_real_url(google_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(google_url, timeout=10, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        # GoogleNewsの実URLはここにある
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.startswith("http") and "google.com" not in href:
                return href
    except Exception as e:
        print("extract error:", e)

    return google_url


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

def post_to_discord(title, summary, url, webhook):
    message = f"""📰 **ペンギンニュース**

**タイトル**
{title}

**要約**
{summary}

🔗 {url}
"""
    if len(message) > 1900:
        message = message[:1900]

    requests.post(webhook, json={"content": message})

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

    google_count = 0
    normal_count = 0


    for source in sources:
        print("Checking:", source["name"])
        feed = feedparser.parse(source["url"])
        print("entries:", len(feed.entries))

        for entry in feed.entries:
            link = entry.get("link")
            title = entry.get("title", "")

            if not link or link in posted_urls:
                continue

            # --------------------------
            # ★ Googleニュース専用
            # --------------------------
            if "news.google.com" in link:
                print("GoogleNews detected")
            
                result = judge_penguin_news(title)
            
                if result == "N":
                    continue
            
                # タイトル日本語化
                jp_title = translate_to_japanese(title)
            
                # 要約文
                if result == "S":
                    summary = "🌍重要なペンギンニュース"
                else:
                    summary = "Googleニュースのため要約はありません"
            
                post_to_discord(jp_title, summary, link, DISCORD_GOOGLENEWS_WEBHOOK)
            
                history.append({
                    "title": title,
                    "url": link,
                    "date": datetime.utcnow().isoformat()
                })
                save_history(history)
            
                google_count += 1
                if google_count >= MAX_POSTS_GOOGLE:
                    break
            
                continue
            # --------------------------
            # 通常記事
            # --------------------------
            article_text = fetch_article_text(link)

            print("TEXT LENGTH:", len(article_text))
            print("------")

            if not article_text:
                continue

            if not contains_penguin(title + article_text):
                continue

            translated = translate_to_japanese(article_text)
            summary = summarize_text(translated)

            post_to_discord(title, summary, link, DISCORD_WEBHOOK)

            history.append({
                "title": title,
                "url": link,
                "date": datetime.utcnow().isoformat()
            })
            save_history(history)

            normal_count += 1
            if normal_count >= MAX_POSTS_NORMAL:
                print("Normal max reached")
                break


if __name__ == "__main__":
    main()
