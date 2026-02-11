import feedparser
import requests
import json
import os
import tldextract
from bs4 import BeautifulSoup

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=penguin&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=penguin+conservation&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=emperor+penguin&hl=en-US&gl=US&ceid=US:en"
]

KEYWORDS = ["penguin", "antarctica", "emperor", "conservation"]

BLACKLIST = ["youtube.com", "pinterest", "facebook", "tiktok"]

TRUSTED_DOMAINS = {
    "bbc.com": 3,
    "reuters.com": 4,
    "apnews.com": 4,
    "nature.com": 5,
    "nationalgeographic.com": 4
}

# --- load history ---
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return []

posted_urls = load_json("posted.json")
posted_titles = load_json("posted_titles.json")

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def is_relevant(title):
    text = title.lower()
    return any(k in text for k in KEYWORDS)

def is_blacklisted(url):
    return any(b in url for b in BLACKLIST)

def get_domain_score(url):
    ext = tldextract.extract(url)
    domain = f"{ext.domain}.{ext.suffix}"
    return TRUSTED_DOMAINS.get(domain, 1)

def fetch_article_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs[:5])
        return text[:500]
    except:
        return ""

candidates = []

# --- collect feeds ---
for feed_url in RSS_FEEDS:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        if entry.link in posted_urls:
            continue
        if not is_relevant(entry.title):
            continue
        if is_blacklisted(entry.link):
            continue

        score = get_domain_score(entry.link)

        candidates.append({
            "title": entry.title,
            "url": entry.link,
            "score": score
        })

# --- sort by trust score ---
candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

if candidates:
    article = candidates[0]
    text = fetch_article_text(article["url"])

    message = f"""📰 **Penguin News Update**

**{article['title']}**

{text}...

🔗 {article['url']}
"""

    requests.post(DISCORD_WEBHOOK, json={"content": message})

    posted_urls.append(article["url"])
    posted_titles.append(article["title"])

    save_json("posted.json", posted_urls)
    save_json("posted_titles.json", posted_titles)
