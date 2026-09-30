#!/usr/bin/env python3
import datetime as dt
import email.utils
import difflib
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

UA = "DopafountainScienceBot/0.4 (+https://github.com/matthew4yang/Dopafountain)"

ALLOWED_CATEGORIES = {"宇宙探索", "粒子物理", "古生物学"}

# Discovery is deliberately narrow: only authoritative institutions / journals,
# then a second-stage semantic gate rejects administrative or vague items.
QUERIES = [
    # 宇宙探索 / observational astronomy / planetary science
    ("宇宙探索", 'site:nasa.gov (spacecraft OR telescope OR probe OR asteroid OR exoplanet OR galaxy OR "black hole" OR Mars OR Moon) (discover OR detect OR observe OR image OR confirm OR launch OR land OR orbit OR flyby) when:120d'),
    ("宇宙探索", 'site:jpl.nasa.gov (spacecraft OR probe OR asteroid OR comet OR planet OR Mars OR Jupiter OR Saturn) (discover OR detect OR observe OR image OR confirm OR launch OR land OR orbit OR flyby) when:120d'),
    ("宇宙探索", 'site:esa.int (spacecraft OR telescope OR probe OR asteroid OR exoplanet OR galaxy OR "black hole") (discover OR detect OR observe OR image OR confirm OR launch OR land OR orbit OR flyby) when:120d'),
    ("宇宙探索", 'site:eso.org (exoplanet OR galaxy OR "black hole" OR star OR supernova OR universe) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:noirlab.edu (exoplanet OR galaxy OR "black hole" OR star OR asteroid OR universe) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:stsci.edu (Webb OR Hubble OR exoplanet OR galaxy OR "black hole" OR star) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:webbtelescope.org (exoplanet OR galaxy OR "black hole" OR star OR atmosphere OR universe) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:chandra.harvard.edu ("black hole" OR neutron OR supernova OR galaxy OR x-ray) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:almaobservatory.org (planet OR disk OR galaxy OR "black hole" OR star OR molecule) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:naoj.org (telescope OR exoplanet OR galaxy OR "black hole" OR star OR asteroid) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),
    ("宇宙探索", 'site:cfa.harvard.edu (exoplanet OR galaxy OR "black hole" OR star OR universe) (discover OR detect OR observe OR image OR reveal OR measure) when:180d'),

    # 粒子物理
    ("粒子物理", 'site:home.cern (LHC OR particle OR Higgs OR neutrino OR quark OR gluon OR muon OR antimatter OR hadron) (observe OR discover OR measure OR detect OR evidence OR decay OR collision) when:180d'),
    ("粒子物理", 'site:fnal.gov (particle OR neutrino OR muon OR collider OR antimatter OR "dark matter" OR DUNE) (observe OR discover OR measure OR detect OR evidence OR constraint) when:180d'),
    ("粒子物理", 'site:bnl.gov (particle OR RHIC OR quark OR gluon OR neutrino OR collider OR ion) (observe OR discover OR measure OR detect OR evidence OR collision) when:180d'),
    ("粒子物理", 'site:desy.de (particle OR photon OR axion OR "dark matter" OR neutrino OR collider OR Higgs) (observe OR discover OR measure OR detect OR evidence OR constraint) when:180d'),
    ("粒子物理", 'site:slac.stanford.edu (particle OR neutrino OR muon OR "dark matter" OR axion OR collider) (observe OR discover OR measure OR detect OR evidence OR constraint) when:180d'),
    ("粒子物理", 'site:kek.jp (particle OR neutrino OR Belle OR muon OR quark OR collider OR hadron) (observe OR discover OR measure OR detect OR evidence OR decay) when:180d'),
    ("粒子物理", 'site:infn.it (particle OR neutrino OR muon OR antimatter OR "dark matter" OR collider) (observe OR discover OR measure OR detect OR evidence OR constraint) when:180d'),
    ("粒子物理", 'site:j-parc.jp (neutrino OR muon OR hadron OR proton OR particle) (observe OR discover OR measure OR detect OR evidence OR decay) when:180d'),
    ("粒子物理", 'site:icecube.wisc.edu (neutrino OR particle OR cosmic) (observe OR discover OR measure OR detect OR evidence OR source) when:180d'),
    ("粒子物理", 'site:belle2.org (particle OR Belle II OR quark OR lepton OR tau OR decay) (observe OR discover OR measure OR detect OR evidence OR constraint) when:180d'),
    ("粒子物理", 'site:symmetrymagazine.org (particle OR Higgs OR neutrino OR muon OR quark OR collider OR "dark matter") (observed OR discovered OR measured OR detected OR evidence OR result) when:180d'),
    ("粒子物理", 'site:journals.aps.org/prl (particle OR Higgs OR neutrino OR muon OR quark OR boson OR "dark matter") (observation OR measurement OR evidence OR search OR constraint) when:180d'),

    # 古生物学 / paleoanthropology
    ("古生物学", 'site:nature.com (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin OR Cambrian OR Jurassic OR Cretaceous) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:240d'),
    ("古生物学", 'site:science.org (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin OR Cambrian OR Jurassic OR Cretaceous) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:240d'),
    ("古生物学", 'site:pnas.org (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin OR Cambrian OR Jurassic OR Cretaceous) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:240d'),
    ("古生物学", 'site:si.edu (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:240d'),
    ("古生物学", 'site:humanorigins.si.edu (hominin OR fossil OR human OR footprint OR stone tool) (discover OR reveal OR evidence OR oldest OR earliest OR dated) when:365d'),
    ("古生物学", 'site:nhm.ac.uk (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:240d'),
    ("古生物学", 'site:amnh.org (fossil OR dinosaur OR paleontolog OR extinct OR hominin) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:365d'),
    ("古生物学", 'site:fieldmuseum.org (fossil OR dinosaur OR paleontolog OR extinct) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:365d'),
    ("古生物学", 'site:burkemuseum.org (fossil OR dinosaur OR paleontolog OR extinct) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:365d'),
    ("古生物学", 'site:plos.org (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:365d'),
    ("古生物学", 'site:peerj.com (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:365d'),
    ("古生物学", 'site:royalsocietypublishing.org (fossil OR dinosaur OR paleontolog OR palaeontolog OR extinct OR hominin) (discover OR reveal OR evidence OR oldest OR earliest OR "new species" OR dated) when:365d'),
    ("古生物学", 'site:cell.com/current-biology (fossil OR dinosaur OR extinct OR hominin OR ancient) (discover OR reveal OR evidence OR oldest OR earliest OR dated) when:365d'),
]

ADMIN_REJECT = [
    r"\bdialogue\b", r"\bspeech\b", r"\bremarks\b", r"\bwebinar\b",
    r"\bmeeting\b", r"\bconference\b", r"\bworkshop\b", r"\bforum\b",
    r"\bfunding opportunity\b", r"\bgrant opportunity\b", r"\bcall for\b",
    r"\bguideline(?:s)?\b", r"\bguidance\b", r"\broadmap\b", r"\bstrategy\b",
    r"\bpolicy\b", r"\bplan\b", r"\bprogramme?\b", r"\bregulation(?:s)?\b",
    r"\banniversary\b", r"\bhistory of\b", r"\bparticipation\b",
    r"\bcase report\b", r"\bprotocol\b", r"\bsystematic review\b",
    r"\bmeta-analysis\b", r"\bperspective\b", r"\beditorial\b",
    r"\binterview\b", r"\bdebate\b", r"\bexplainer\b", r"\bwhat to know\b",
    r"\bjob\b", r"\bvacancy\b", r"\baward\b", r"\bprize\b",
]

SPACE_ACTION = [
    r"\bdiscover", r"\bdetect", r"\bconfirm", r"\bobserv",
    r"\bfirst image\b", r"\bfirst observation\b", r"\blanded\b",
    r"\breveal", r"\bimage", r"\bmap", r"\bmeasure", r"\bfind", r"\bfound\b",
    r"\blaunched\b", r"\bentered orbit\b", r"\bflyby\b",
    r"\bsample return\b", r"\bseparation\b", r"\brecord\b",
]
SPACE_OBJECT = [
    r"\bspacecraft\b", r"\btelescope\b", r"\bprobe\b", r"\bmission\b",
    r"\basteroid\b", r"\bcomet\b", r"\bplanet\b", r"\bexoplanet\b",
    r"\bgalaxy\b", r"\bblack hole\b", r"\bmoon\b", r"\bmars\b",
    r"\bmercury\b", r"\bjupiter\b", r"\bsaturn\b", r"\buniverse\b",
]

PARTICLE_ACTION = [
    r"\bdiscover", r"\bobserv", r"\bdetect", r"\bmeasur", r"\bevidence\b",
    r"\bfirst\b", r"\bprecision\b", r"\bconstraint", r"\bexcess\b",
    r"\bdecay\b", r"\bcollision", r"\bresult", r"\bsearch", r"\blimit", r"\bhint",
]
PARTICLE_OBJECT = [
    r"\bparticle\b", r"\blhc\b", r"\bcollider\b", r"\bneutrino\b",
    r"\bhiggs\b", r"\bmuon\b", r"\bquark\b", r"\bgluon\b",
    r"\bboson\b", r"\bantimatter\b", r"\bdark matter\b", r"\baxion\b",
    r"\bmeson\b", r"\bbaryon\b", r"\bproton\b", r"\bion\b",
    r"\blepton\b", r"\btau\b", r"\bcharm\b", r"\btop quark\b",
    r"\btetraquark\b", r"\bpentaquark\b", r"\bplasma\b",
]

PALEO_ACTION = [
    r"\bdiscover", r"\breveal", r"\bevidence\b", r"\boldest\b",
    r"\bearliest\b", r"\bnew species\b", r"\breconstruct",
    r"\bdated\b", r"\bidentif", r"\btrace fossil\b",
    r"\bfind", r"\bfound\b", r"\bdescribe", r"\breconstruct", r"\btrackway\b",
]
PALEO_OBJECT = [
    r"\bfossil\b", r"\bdinosaur\b", r"\bpaleontolog", r"\bpalaeontolog",
    r"\bextinct\b", r"\bhominin\b", r"\bCambrian\b", r"\bJurassic\b",
    r"\bCretaceous\b", r"\bPleistocene\b", r"\bMesozoic\b",
    r"\bvertebrate\b", r"\bichnofossil\b", r"\bamber\b",
    r"\bfootprint\b", r"\btrackway\b", r"\bskull\b", r"\bbone\b",
    r"\barchosaur\b", r"\btheropod\b", r"\bsauropod\b",
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
    return any(re.search(p, low, re.I) for p in patterns)

def gate_for(category):
    if category == "宇宙探索":
        return SPACE_ACTION, SPACE_OBJECT
    if category == "粒子物理":
        return PARTICLE_ACTION, PARTICLE_OBJECT
    if category == "古生物学":
        return PALEO_ACTION, PALEO_OBJECT
    return [], []

def qualifies(category, title, source):
    if category not in ALLOWED_CATEGORIES or "?" in title:
        return False
    low = title.lower()
    if any_match(low, ADMIN_REJECT):
        return False
    action, obj = gate_for(category)
    return any_match(low, action) and any_match(low, obj)

def score_title(category, title, source):
    action, obj = gate_for(category)
    low = title.lower()
    a = sum(1 for p in action if re.search(p, low, re.I))
    b = sum(1 for p in obj if re.search(p, low, re.I))
    score = 64 + min(a, 3) * 7 + min(b, 2) * 6
    if re.search(r"\b\d+(?:\.\d+)?\s*%|\b\d{2,}\b", title):
        score += 6
    # Every discovery query is already locked to an approved source domain.
    score += 6
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
            return clean_text("".join(part[0] for part in data[0] if part and part[0]))
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

            if source:
                for sep in (" - ", " – ", " — "):
                    suffix = sep + source
                    if title.endswith(suffix):
                        title = title[:-len(suffix)].strip()
                        break

            if not title or not link or not qualifies(category, title, source):
                continue
            if (now - published).days > 125:
                continue

            score = score_title(category, title, source)
            if score < 78:
                continue

            key = re.sub(r"\W+", "", title.lower())
            if not key or key in seen_titles:
                continue
            seen_titles.add(key)

            source_clean = source
            aliases = [
                (r"(?i).*cern.*", "CERN"),
                (r"(?i).*fermilab.*", "Fermilab"),
                (r"(?i).*brookhaven.*|.*bnl.*", "Brookhaven National Laboratory"),
                (r"(?i).*desy.*", "DESY"),
                (r"(?i).*slac.*", "SLAC"),
                (r"(?i).*belle.?2.*", "Belle II"),
                (r"(?i).*nasa.*", "NASA"),
                (r"(?i).*jet propulsion.*|.*jpl.*", "NASA/JPL"),
                (r"(?i).*european space agency.*|^esa$", "ESA"),
                (r"(?i).*science.*aaas.*|^science$", "Science"),
                (r"(?i).*smithsonian.*", "Smithsonian"),
            ]
            for pattern, label in aliases:
                if re.match(pattern, source_clean):
                    source_clean = label
                    break

            rows.append({
                "category": category,
                "title_raw": title,
                "source": source_clean or source,
                "url": link,
                "published": published,
                "score": score,
            })

    rows.sort(key=lambda x: (x["published"], x["score"]), reverse=True)

    # Prevent one field from drowning out the others.
    balanced = []
    for category in ("宇宙探索", "粒子物理", "古生物学"):
        balanced.extend([r for r in rows if r["category"] == category][:24])
    balanced.sort(key=lambda x: (x["published"], x["score"]), reverse=True)
    return balanced[:72]

def generated_items(rows):
    items = []
    for row in rows:
        fact_cn = translate_zh(row["title_raw"])
        ident = hashlib.sha256(
            (row["category"] + "|" + row["source"] + "|" + row["title_raw"]).encode("utf-8")
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
        raw = json.loads(SEED.read_text("utf-8")).get("items", [])
        return [x for x in raw if x.get("category") in ALLOWED_CATEGORIES]
    except Exception:
        return []

def event_signature(title):
    generic = {
        "nasa", "space", "spacecraft", "mission", "telescope", "particle",
        "physics", "fossil", "study", "research", "first", "new", "european",
        "science", "universe", "galaxy"
    }
    return {
        t for t in re.findall(r"[a-z0-9][a-z0-9-]{4,}", title.lower())
        if t not in generic
    }

def merge_items(seed, generated):
    out = []
    seen_ids = set()
    seen_titles = set()
    seen_signatures = []
    for item in seed + generated:
        if item.get("category") not in ALLOWED_CATEGORIES:
            continue
        ident = item.get("id", "")
        title = clean_text(item.get("title", ""))
        text = clean_text(item.get("text", "")) or title
        key = re.sub(r"\W+", "", title.lower())
        if not ident or not key or ident in seen_ids or key in seen_titles or len(title) < 8:
            continue

        sig = event_signature(title)
        duplicate_event = False
        for old_title, old_sig, old_category in seen_signatures:
            if old_category != item.get("category"):
                continue
            similar = difflib.SequenceMatcher(None, title.lower(), old_title.lower()).ratio() >= 0.80
            shared_entity = bool(sig and old_sig and (sig & old_sig))
            if similar or shared_entity:
                duplicate_event = True
                break
        if duplicate_event:
            continue

        item = dict(item)
        item["text"] = text
        seen_ids.add(ident)
        seen_titles.add(key)
        seen_signatures.append((title, sig, item.get("category")))
        out.append(item)

    # Balance the final feed too.
    final = []
    for category in ("宇宙探索", "粒子物理", "古生物学"):
        bucket = [x for x in out if x.get("category") == category]
        bucket.sort(key=lambda x: (x.get("published_at", ""), x.get("score", 0)), reverse=True)
        final.extend(bucket[:24])
    final.sort(key=lambda x: (x.get("published_at", ""), x.get("score", 0)), reverse=True)
    return final[:72]

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

    if len(items) < 2:
        raise RuntimeError("Strict science gate produced too few items; keeping previous feed.")

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
        "policy": "ONLY 宇宙探索 / 粒子物理 / 古生物学; core facts only; authoritative-source whitelist",
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Wrote {len(items)} items ({len(auto)} auto + {len(seed)} verified seeds).")

if __name__ == "__main__":
    main()
