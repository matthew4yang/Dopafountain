#!/usr/bin/env python3
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "goodnews.json"

UA = "DopafountainNewsBot/0.2 (+https://github.com/matthew4yang/Dopafountain)"

QUERIES = [
    ("医学", "site:nih.gov (trial OR treatment OR remission OR vaccine OR successful) when:30d"),
    ("医学", "site:fda.gov (approves OR approval OR authorized OR clearance) when:30d"),
    ("医学", "site:nature.com (trial OR treatment OR remission OR breakthrough) when:30d"),
    ("科学", "site:science.org (breakthrough OR discovery OR discovered OR first) when:30d"),
    ("航天", "site:nasa.gov (successful OR discovery OR discovered OR first OR launched) when:30d"),
    ("航天", "site:esa.int (successful OR discovery OR discovered OR first OR launched) when:30d"),
    ("健康", "site:who.int (eliminated OR reduction OR vaccine OR certified OR approved) when:45d"),
    ("能源", "site:iea.org (renewable OR solar OR battery OR efficiency OR record) when:45d"),
    ("生态", "site:noaa.gov (recovery OR restored OR rebound OR protected OR record) when:45d"),
]

POSITIVE = {
    "approved": 20, "approves": 20, "authorized": 18, "clearance": 15,
    "breakthrough": 18, "successful": 16, "success": 14, "first": 10,
    "remission": 22, "effective": 18, "efficacy": 16, "survival": 14,
    "recovery": 16, "recovered": 16, "restored": 16, "rebound": 14,
    "eliminated": 22, "eradicated": 24, "reduction": 12, "reduced": 12,
    "discovery": 12, "discovered": 12, "record": 12, "improved": 12,
    "improves": 12, "protect": 10, "protected": 10, "renewable": 10,
    "solar": 8, "battery": 8, "efficiency": 10, "vaccine": 10,
    "treatment": 8, "trial": 8, "launched": 8, "landed": 14,
}

HARD = [
    "phase 3", "phase iii", "randomized", "clinical trial", "fda",
    "who", "percent", "%", "patients", "participants", "published",
    "study", "mission", "megawatt", "gigawatt", "efficiency"
]

CLICKBAIT = [
    "shocking", "stunning", "you won't believe", "miracle",
    "game changer", "mind-blowing", "secret"
]

def request_bytes(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def clean_text(s):
    if not s:
        return ""
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip()

def parse_date(s):
    try:
        d = email.utils.parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return dt.datetime.now(dt.timezone.utc)

def google_news_url(query):
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

def score_title(title):
    low = title.lower()
    score = 18
    for word, points in POSITIVE.items():
        if word in low:
            score += points
    for word in HARD:
        if word in low:
            score += 6
    if re.search(r"\b\d+(?:\.\d+)?\s*%|\b\d{2,}\b", low):
        score += 8
    for word in CLICKBAIT:
        if word in low:
            score -= 40
    return score

def translate_zh(text):
    text = clean_text(text)[:900]
    if not text:
        return ""
    params = urllib.parse.urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": "zh-CN",
        "dt": "t",
        "q": text,
    })
    url = "https://translate.googleapis.com/translate_a/single?" + params
    for attempt in range(2):
        try:
            data = json.loads(request_bytes(url, timeout=12).decode("utf-8"))
            result = "".join(part[0] for part in data[0] if part and part[0])
            return clean_text(result)
        except Exception:
            if attempt == 0:
                time.sleep(0.8)
    return text

META_PATTERNS = [
    re.compile(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']', re.I),
]

def page_description(url):
    try:
        raw = request_bytes(url, timeout=12)[:900000]
        page = raw.decode("utf-8", errors="ignore")
        for pattern in META_PATTERNS:
            m = pattern.search(page)
            if not m:
                continue
            text = clean_text(m.group(1))
            low = text.lower()
            if 45 <= len(text) <= 700 and "google news" not in low and "comprehensive up-to-date" not in low:
                return text
    except Exception:
        pass
    return ""

def trim_sentences(text, max_chars=260):
    text = clean_text(text)
    if not text:
        return ""
    chunks = re.split(r"(?<=[.!?。！？])\s+", text)
    out = " ".join(chunks[:2]).strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return out

def collect():
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    seen_titles = set()

    for category, query in QUERIES:
        try:
            root = ET.fromstring(request_bytes(google_news_url(query), timeout=18))
        except Exception as exc:
            print(f"skip query: {query}: {exc}")
            continue

        for item in root.findall(".//item"):
            title = clean_text(item.findtext("title"))
            link = clean_text(item.findtext("link"))
            published = parse_date(item.findtext("pubDate") or "")
            source_node = item.find("source")
            source = clean_text(source_node.text if source_node is not None else "")

            if source and title.endswith(" - " + source):
                title = title[:-(len(source) + 3)].strip()

            if not title or not link:
                continue
            if (now - published).days > 50:
                continue

            key = re.sub(r"\W+", "", title.lower())
            if key in seen_titles:
                continue
            seen_titles.add(key)

            score = score_title(title)
            if score < 34:
                continue

            rows.append({
                "category": category,
                "title_raw": title,
                "source": source or "Web",
                "url": link,
                "published": published,
                "score": score,
            })

    rows.sort(key=lambda x: (x["published"], x["score"]), reverse=True)
    return rows[:60]

def build_items(rows):
    items = []
    for i, row in enumerate(rows):
        title_cn = translate_zh(row["title_raw"])
        desc_raw = page_description(row["url"]) if i < 28 else ""
        text_cn = translate_zh(trim_sentences(desc_raw)) if desc_raw else ""

        if text_cn == title_cn:
            text_cn = ""

        ident = hashlib.sha256(
            (row["source"] + "|" + row["title_raw"]).encode("utf-8")
        ).hexdigest()[:16]

        items.append({
            "id": ident,
            "category": row["category"],
            "title": title_cn,
            "text": text_cn,
            "source": row["source"],
            "url": row["url"],
            "published_at": row["published"].isoformat().replace("+00:00", "Z"),
            "score": row["score"],
        })
        time.sleep(0.08)
    return items

def same_content(old, new_items):
    old_items = old.get("items", []) if isinstance(old, dict) else []
    fields = ("id", "title", "text", "source", "url", "published_at")
    def canon(items):
        return [tuple(x.get(k, "") for k in fields) for x in items]
    return canon(old_items) == canon(new_items)

def main():
    rows = collect()
    if not rows:
        raise RuntimeError("No qualifying hard-good-news items found; keeping previous feed.")

    items = build_items(rows)
    if not items:
        raise RuntimeError("No usable items after processing; keeping previous feed.")

    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text("utf-8"))
        except Exception:
            old = {}

    if same_content(old, items):
        print(f"No feed change; keeping {len(items)} items.")
        return

    payload = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(items),
        "policy": "core facts only; no motivational filler",
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Wrote {len(items)} items to {OUT}")

if __name__ == "__main__":
    main()
