import feedparser
import requests
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

HISTORY_FILE = "history.json"

# ====== 共通 ======

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_html(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = r.apparent_encoding
        return r.text
    except:
        return ""

def summarize(text):
    text = text.replace("\n", "")
    sentences = text.split("。")
    return "。".join(sentences[:3]) + "。"

def post_to_discord(message):
    if len(message) > 1900:
        message = message[:1900]
    requests.post(DISCORD_WEBHOOK, json={"content": message})

# ====== RSS処理 ======

def process_rss(site, history):
    feed = feedparser.parse(site["rss"])
    for entry in feed.entries[:5]:
        if any(h["url"] == entry.link for h in history):
            continue

        summary = summarize(entry.title + "。")

        message = f"""📰【{site['name']}】

■ タイトル
{entry.title}

■ 要約
{summary}

🔗 {entry.link}
"""

        post_to_discord(message)

        history.append({
            "title": entry.title,
            "url": entry.link,
            "date": datetime.utcnow().isoformat()
        })

        return history

    return history

# ====== スクレイピング処理 ======

def process_scrape(site, selectors, history):
    structure = site["structure"]
    selector = selectors.get(structure)

    if not selector:
        return history

    html = fetch_html(site["news_page"])
    soup = BeautifulSoup(html, "html.parser")

    links = soup.select(selector["article_link_selector"])

    for link in links[:10]:
        href = link.get("href")
        if not href:
            continue

        full_url = urljoin(site["news_page"], href)

        if any(h["url"] == full_url for h in history):
            continue

        article_html = fetch_html(full_url)
        article_soup = BeautifulSoup(article_html, "html.parser")

        title_tag = article_soup.select_one(selector["title_selector"])
        content_tags = article_soup.select(selector["content_selector"])

        if not title_tag or not content_tags:
            continue

        title = title_tag.get_text(strip=True)
        content = " ".join(p.get_text(strip=True) for p in content_tags[:5])

        if not any(k in content for k in ["ペンギン", "penguin", "Penguin"]):
            continue

        summary = summarize(content)

        message = f"""📰【{site['name']}】

■ タイトル
{title}

■ 要約
{summary}

🔗 {full_url}
"""

        post_to_discord(message)

        history.append({
            "title": title,
            "url": full_url,
            "date": datetime.utcnow().isoformat()
        })

        return history

    return history

# ====== 実行 ======

def main():
    history = load_json(HISTORY_FILE, [])
    sources = load_json("sources.json", [])
    selectors = load_json("selectors.json", {})

    for site in sources:
        if "rss" in site and site["rss"]:
            history = process_rss(site, history)
        else:
            history = process_scrape(site, selectors, history)

    save_json(HISTORY_FILE, history)

if __name__ == "__main__":
    main()
