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

UA = "DopafountainNewsBot/0.3 (+https://github.com/matthew4yang/Dopafountain)"

# Narrow queries.  Discovery is broad enough to stay fresh, but the second-stage
# gate below is deliberately much stricter than the search query itself.
QUERIES = [
    ("医学", 'site:fda.gov/news-events/press-announcements ("FDA approves" OR "FDA grants accelerated approval" OR "first treatment") when:35d'),
    ("医学", 'site:nih.gov/news-events/news-releases ("clinical trial" OR patients) (remission OR reduced OR improved OR effective) when:45d'),
    ("医学", 'site:nature.com/articles/d41586 (trial OR patients) (remission OR reduced OR improved OR effective) when:45d'),
    ("科学", 'site:science.org/content/article ("first ever" OR discovery OR discovered OR breakthrough) when:45d'),
    ("航天", 'site:nasa.gov (spacecraft OR telescope OR probe OR mission OR engine OR thruster) (successfully OR record OR discovered OR "first") when:45d'),
    ("航天", 'site:jpl.nasa.gov (spacecraft OR telescope OR probe OR mission OR engine) (successfully OR record OR discovered OR "first") when:45d'),
    ("航天", 'site:esa.int (spacecraft OR telescope OR probe OR mission OR launcher) (successfully OR record OR discovered OR "first") when:45d'),
    ("健康", 'site:who.int (eliminated OR certified OR "cases declined" OR "cases fell" OR reduction) (malaria OR trachoma OR cholera OR measles OR disease) when:90d'),
    ("能源", 'site:iea.org (record OR surpassed OR overtook OR growth) (renewable OR solar OR wind OR battery OR electricity) when:120d'),
    ("生态", 'site:noaa.gov (recovered OR recovery OR rebound OR restored OR increased) (species OR population OR habitat OR coral OR whale OR turtle OR salmon) when:120d'),
]

ADMIN_REJECT = [
    r"\bdialogue\b", r"\bspeech\b", r"\bremarks\b", r"\bwebinar\b",
    r"\bmeeting\b", r"\bconference\b", r"\bworkshop\b", r"\bforum\b",
    r"\bfunding opportunity\b", r"\bgrant opportunity\b", r"\bcall for\b",
    r"\bguideline(?:s)?\b", r"\bguidance\b", r"\broadmap\b", r"\bstrategy\b",
    r"\bpolicy\b", r"\bplan\b", r"\bprogram(?:me)?\b", r"\bregulation(?:s)?\b",
    r"\bappendix\b", r"\brepository\b", r"\bassessment\b", r"\boverview\b",
    r"\banniversary\b", r"\bhistory of\b", r"\bparticipation\b",
    r"\bcase report\b", r"\bprotocol\b", r"\bsystematic review\b",
    r"\bmeta-analysis\b", r"\bperspective\b", r"\beditorial\b",
    r"\binterview\b", r"\bcontroversy\b", r"\bdebate\b",
    r"\bhow to\b", r"\bexplainer\b", r"\bwhat to know\b",
]

NEGATIVE_REJECT = [
    r"\bwarning\b", r"\brecall\b", r"\bshortage\b", r"\boutbreak worsens\b",
    r"\bdeaths? rise\b", r"\bcases? rise\b", r"\bdeclared emergency\b",
]

MED_ACTION = [
    r"\bfda approv", r"\bapproved\b", r"\baccelerated approval\b",
    r"\bfirst (?:drug|treatment|therapy|gene therapy)\b",
    r"\bphase (?:2|3|ii|iii)\b", r"\bclinical trial\b",
    r"\bremission\b", r"\breduced\b", r"\bimproved\b", r"\beffective\b",
]
MED_OBJECT = [
    r"\bdrug\b", r"\btreatment\b", r"\btherapy\b", r"\bvaccine\b",
    r"\bpatients?\b", r"\bdisease\b", r"\bcancer\b", r"\bsyndrome\b",
    r"\bdeficien", r"\bmultiple sclerosis\b", r"\btransplant\b",
]

HEALTH_ACTION = [
    r"\beliminat", r"\bcertif", r"\bcases? (?:declined|fell|reduced)\b",
    r"\b(?:decline|reduction) in cases\b",
]
HEALTH_OBJECT = [
    r"\bmalaria\b", r"\btrachoma\b", r"\bcholera\b", r"\bmeasles\b",
    r"\bpolio\b", r"\bdisease\b", r"\boutbreak\b",
]

SPACE_ACTION = [
    r"\bsuccess", r"\bfirst\b", r"\brecord\b", r"\bdiscover",
    r"\bdetect", r"\bconfirm", r"\bentered orbit\b", r"\blanded\b",
    r"\bseparation\b", r"\bflyby\b", r"\blaunched\b",
]
SPACE_OBJECT = [
    r"\bspacecraft\b", r"\btelescope\b", r"\bprobe\b", r"\bmission\b",
    r"\bengine\b", r"\bthruster\b", r"\brocket\b", r"\borbit\b",
    r"\basteroid\b", r"\bplanet\b", r"\bexoplanet\b", r"\bgalaxy\b",
    r"\bblack hole\b", r"\bmoon\b", r"\bmars\b", r"\bmercury\b",
    r"\bjupiter\b",
]

SCIENCE_ACTION = [
    r"\bdiscover", r"\bbreakthrough\b", r"\bfirst ever\b",
    r"\bfirst in the world\b", r"\bdemonstrat", r"\bachiev",
]
SCIENCE_OBJECT = [
    r"\bexperiment\b", r"\bmaterial\b", r"\bcell\b", r"\bprotein\b",
    r"\bgene\b", r"\borgan\b", r"\bquantum\b", r"\bfossil\b",
    r"\bparticle\b", r"\btransplant\b", r"\bmathemat",
]

ENERGY_ACTION = [
    r"\brecord\b", r"\bsurpass", r"\bovertook\b", r"\bovertake\b",
    r"\bgrew\b", r"\bgrowth\b", r"\breduced\b",
]
ENERGY_OBJECT = [
    r"\brenewable", r"\bsolar\b", r"\bwind\b", r"\bbattery\b",
    r"\belectricity\b", r"\bstorage\b", r"\bfusion\b",
]

ECO_ACTION = [
    r"\brecover", r"\brebound\b", r"\brestor", r"\bincreased\b",
    r"\bpopulation grew\b", r"\breturned\b",
]
ECO_OBJECT = [
    r"\bspecies\b", r"\bpopulation\b", r"\bhabitat\b", r"\bcoral\b",
    r"\bwhale\b", r"\bturtle\b", r"\bsalmon\b", r"\bbird\b",
    r"\bforest\b", r"\bwetland\b",
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

def any_match(text, patterns):
    low = text.lower()
    return any(re.search(p, low) for p in patterns)

def gate_for(category):
    if category == "医学":
        return MED_ACTION, MED_OBJECT
    if category == "健康":
        return HEALTH_ACTION, HEALTH_OBJECT
    if category == "航天":
        return SPACE_ACTION, SPACE_OBJECT
    if category == "科学":
        return SCIENCE_ACTION, SCIENCE_OBJECT
    if category == "能源":
        return ENERGY_ACTION, ENERGY_OBJECT
    return ECO_ACTION, ECO_OBJECT

def qualifies(category, title):
    low = title.lower()
    if "?" in title:
        return False
    if any_match(low, ADMIN_REJECT) or any_match(low, NEGATIVE_REJECT):
        return False
    action, obj = gate_for(category)
    return any_match(low, action) and any_match(low, obj)

def score_title(category, title, source):
    action, obj = gate_for(category)
    low = title.lower()
    a = sum(1 for p in action if re.search(p, low))
    b = sum(1 for p in obj if re.search(p, low))
    score = 58 + min(a, 3) * 8 + min(b, 2) * 5

    # Hard numbers are especially useful for "core fact" notifications.
    if re.search(r"\b\d+(?:\.\d+)?\s*%|\b\d{2,}\b", title):
        score += 7
    if re.search(r"\bfirst (?:drug|treatment|therapy|gene therapy)\b", low):
        score += 10

    trusted = (
        "FDA" in source or "NIH" in source or "NASA" in source or
        "European Space Agency" in source or "World Health Organization" in source or
        "IEA" in source or "NOAA" in source or "Nature" in source or
        "Science" in source
    )
    if trusted:
        score += 5
    return min(score, 99)

def translate_zh(text):
    text = clean_text(text)[:700]
    if not text:
        return ""
    params = urllib.parse.urlencode({
        "client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": text,
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
            print(f"skip query: {category}: {exc}")
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

            score = score_title(category, title, source)
            if score < 75:
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
                "score": score,
            })

    rows.sort(key=lambda x: (x["published"], x["score"]), reverse=True)
    return rows[:36]

def generated_items(rows):
    items = []
    for row in rows:
        fact_cn = translate_zh(row["title_raw"])
        ident = hashlib.sha256(
            (row["source"] + "|" + row["title_raw"]).encode("utf-8")
        ).hexdigest()[:16]
        items.append({
            "id": ident,
            "category": row["category"],
            "title": fact_cn,
            "text": fact_cn,
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

    # Verified seeds stay first in preference when dates are equal, but both
    # manual and automatic items must carry a concrete fact.
    for item in seed + generated:
        ident = item.get("id", "")
        title = clean_text(item.get("title", ""))
        text = clean_text(item.get("text", "")) or title
        key = re.sub(r"\W+", "", title.lower())
        if not ident or not key or ident in seen_ids or key in seen_titles:
            continue
        if len(title) < 8:
            continue
        item = dict(item)
        item["text"] = text
        seen_ids.add(ident)
        seen_titles.add(key)
        out.append(item)

    out.sort(key=lambda x: (x.get("published_at", ""), x.get("score", 0)), reverse=True)
    return out[:48]

def same_content(old, new_items):
    old_items = old.get("items", []) if isinstance(old, dict) else []
    fields = ("id", "category", "title", "text", "source", "url", "published_at", "score")
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
        "policy": "core facts only; strict object+result gate; no motivational or administrative filler",
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Wrote {len(items)} items ({len(auto)} auto + {len(seed)} verified seeds).")

if __name__ == "__main__":
    main()
