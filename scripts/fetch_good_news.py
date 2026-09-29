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
SEED = ROOT / "data" / "verified_seed.json"

UA = "DopafountainNewsBot/0.2 (+https://github.com/matthew4yang/Dopafountain)"

QUERIES = [
    ("医学", 'site:fda.gov/news-events/press-announcements ("FDA approves" OR "FDA grants accelerated approval" OR "first treatment" OR "first therapy") when:45d'),
    ("医学", 'site:nih.gov/news-events/news-releases (reverses OR improves OR reduced OR remission OR effective OR recovery) when:45d'),
    ("医学", 'site:nature.com/articles/d41586 (remission OR reverses OR eases OR improves OR "first trial") when:45d'),
    ("科学", 'site:science.org/content/article (breakthrough OR discovery OR discovered OR record OR successful) when:45d'),
    ("航天", 'site:nasa.gov (discovery OR discovered OR successful OR record OR "first ever") when:45d'),
    ("航天", 'site:jpl.nasa.gov (discovery OR discovered OR successful OR record OR "first") when:45d'),
    ("航天", 'site:esa.int (successful OR discovery OR discovered OR record OR "first") when:45d'),
    ("健康", 'site:who.int (eliminated OR certified OR reduction OR reduced OR decline OR recovery) when:60d'),
    ("能源", 'site:iea.org (record OR "fastest growing" OR surpassed OR overtook OR reduced) when:120d'),
    ("生态", 'site:noaa.gov (recovery OR restored OR rebound OR protected OR record) when:60d'),
]

MED_STRONG = [
    r"\bapprov(?:e|es|ed|al)\b",
    r"\bauthoriz(?:e|es|ed|ation)\b",
    r"\bremission\b",
    r"\brevers(?:e|es|ed)\b",
    r"\beas(?:e|es|ed)\b",
    r"\bimprov(?:e|es|ed|ement)\b",
    r"\breduc(?:e|es|ed|tion)\b",
    r"\brecover(?:y|ed|s)?\b",
    r"\brestor(?:e|es|ed|ation)\b",
    r"\beffective(?:ness)?\b",
    r"\bprevent(?:s|ed|ion)?\b",
    r"\bsurvival\b",
    r"\bfirst (?:drug|treatment|therapy|gene therapy)\b",
]

SCIENCE_STRONG = [
    r"\bdiscover(?:y|ed|s)?\b",
    r"\bbreakthrough\b",
    r"\bsuccess(?:ful|fully)?\b",
    r"\brecord\b",
    r"\bfirst ever\b",
    r"\bfirst in the world\b",
    r"\bachiev(?:e|es|ed)\b",
    r"\bdetect(?:s|ed)\b",
    r"\bconfirm(?:s|ed)\b",
]

ENERGY_ECO_STRONG = [
    r"\brecord\b",
    r"\brecover(?:y|ed|s)?\b",
    r"\brestor(?:e|es|ed|ation)\b",
    r"\brebound\b",
    r"\bprotect(?:s|ed|ion)?\b",
    r"\beliminat(?:e|es|ed|ion)\b",
    r"\bcertif(?:y|ies|ied)\b",
    r"\breduc(?:e|es|ed|tion)\b",
    r"\bdeclin(?:e|es|ed)\b",
    r"\bsurpass(?:es|ed)?\b",
    r"\bovert(?:ake|akes|ook)\b",
    r"\bfastest growing\b",
]

REJECT = [
    r"\bcase report\b",
    r"\bprotocol\b",
    r"\bsystematic review\b",
    r"\bmeta-analysis\b",
    r"\bcomparison\b",
    r"\bnational trends\b",
    r"\bassociation between\b",
    r"\bperspective\b",
    r"\beditorial\b",
    r"\byears ago\b",
    r"\banniversary\b",
    r"\bhistory of\b",
    r"\bwarning\b",
    r"\brecall\b",
    r"\bshortage\b",
]

def request_bytes(url, timeout=18):
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

def has_pattern(title, patterns):
    low = title.lower()
    return any(re.search(p, low) for p in patterns)

def qualifies(category, title):
    low = title.lower()
    if "?" in title:
        return False
    if any(re.search(p, low) for p in REJECT):
        return False

    if category in ("医学", "健康"):
        return has_pattern(title, MED_STRONG + ENERGY_ECO_STRONG)
    if category in ("航天", "科学"):
        return has_pattern(title, SCIENCE_STRONG)
    return has_pattern(title, ENERGY_ECO_STRONG)

def score_title(category, title):
    patterns = MED_STRONG if category in ("医学", "健康") else (
        SCIENCE_STRONG if category in ("航天", "科学") else ENERGY_ECO_STRONG
    )
    hits = sum(1 for p in patterns if re.search(p, title.lower()))
    score = 55 + hits * 10
    if re.search(r"\b\d+(?:\.\d+)?\s*%|\b\d{2,}\b", title):
        score += 5
    if re.search(r"\bfirst (?:drug|treatment|therapy|gene therapy)\b", title.lower()):
        score += 12
    return min(score, 99)

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
                time.sleep(0.6)
    return text

def collect():
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    seen_titles = set()

    for category, query in QUERIES:
        try:
            root = ET.fromstring(request_bytes(google_news_url(query)))
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

            if not title or not link or not qualifies(category, title):
                continue
            if (now - published).days > 125:
                continue

            key = re.sub(r"\W+", "", title.lower())
            if not key or key in seen_titles:
                continue
            seen_titles.add(key)

            rows.append({
                "category": category,
                "title_raw": title,
                "source": source or "Web",
                "url": link,
                "published": published,
                "score": score_title(category, title),
            })

    rows.sort(key=lambda x: (x["published"], x["score"]), reverse=True)
    return rows[:50]

def generated_items(rows):
    items = []
    for row in rows:
        title_cn = translate_zh(row["title_raw"])
        ident = hashlib.sha256(
            (row["source"] + "|" + row["title_raw"]).encode("utf-8")
        ).hexdigest()[:16]
        items.append({
            "id": ident,
            "category": row["category"],
            "title": title_cn,
            "text": "",
            "source": row["source"],
            "url": row["url"],
            "published_at": row["published"].isoformat().replace("+00:00", "Z"),
            "score": row["score"],
        })
        time.sleep(0.05)
    return items

def load_seed():
    try:
        return json.loads(SEED.read_text("utf-8")).get("items", [])
    except Exception:
        return []

def merge_items(seed, generated):
    out = []
    seen_ids = set()
    seen_titles = set()

    for item in seed + generated:
        ident = item.get("id", "")
        key = re.sub(r"\W+", "", item.get("title", "").lower())
        if not ident or not key or ident in seen_ids or key in seen_titles:
            continue
        seen_ids.add(ident)
        seen_titles.add(key)
        out.append(item)

    out.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return out[:60]

def same_content(old, new_items):
    old_items = old.get("items", []) if isinstance(old, dict) else []
    fields = ("id", "title", "text", "source", "url", "published_at")
    def canon(items):
        return [tuple(x.get(k, "") for k in fields) for x in items]
    return canon(old_items) == canon(new_items)

def main():
    seed = load_seed()
    rows = collect()
    auto = generated_items(rows)
    items = merge_items(seed, auto)

    if len(items) < 5:
        raise RuntimeError("Quality gate produced too few items; keeping previous feed.")

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
        "auto_count": len(auto),
        "verified_seed_count": len(seed),
        "policy": "core facts only; strong positive result required; no motivational filler",
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Wrote {len(items)} items ({len(auto)} auto + {len(seed)} verified seeds).")

if __name__ == "__main__":
    main()
