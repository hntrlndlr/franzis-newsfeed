import base64
import calendar
import html
import mimetypes
import re
from datetime import date
from pathlib import Path

import feedparser
import requests
import streamlit as st

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

ASSETS_DIR = Path(__file__).parent / "assets"

LOGO_FILES = {
    "taz": "taz.svg",
    "Die Zeit": "zeit.svg",
    "Tagesschau": "tagesschau.svg",
    "FAZ": "faz.svg",
    "NZZ": "nzz.svg",
}

ORIENTATIONS = {
    "taz": "grün-links, linksalternativ",
    "Die Zeit": "liberal, teils linksliberal",
    "Tagesschau": "öffentlich-rechtlich, überparteilich",
    "FAZ": "bürgerlich-konservativ",
    "NZZ": "konservativ, rechtsliberal",
}

ACCENT_COLORS = {
    "taz": "#a05c57",
    "Die Zeit": "#4e7f50",
    "Tagesschau": "#2e7b9c",
    "FAZ": "#7a659e",
    "NZZ": "#936831",
}

CSS_SLUGS = {
    "taz": "taz",
    "Die Zeit": "zeit",
    "Tagesschau": "tagesschau",
    "FAZ": "faz",
    "NZZ": "nzz",
}

WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

INNENPOLITIK_FEEDS = {
    "taz": "https://taz.de/Politik/Deutschland/!p4616;rss/",
    "Die Zeit": "https://newsfeed.zeit.de/politik/deutschland/index",
    "Tagesschau": "https://www.tagesschau.de/inland/innenpolitik/index~rss2.xml",
    "FAZ": "https://www.faz.net/rss/aktuell/politik/inland/",
    "NZZ": "https://www.nzz.ch/deutschland.rss",
}

AUSSENPOLITIK_FEEDS = {
    "taz": (
        "https://taz.de/Politik/Europa/!p4617;rss/",
        "https://taz.de/Politik/Amerika/!p4618;rss/",
        "https://taz.de/Politik/Asien/!p4619;rss/",
        "https://taz.de/Politik/Nahost/!p4620;rss/",
        "https://taz.de/Politik/Afrika/!p4621;rss/",
    ),
    "Die Zeit": "https://newsfeed.zeit.de/politik/ausland/index",
    "Tagesschau": "https://www.tagesschau.de/ausland/index~rss2.xml",
    "FAZ": "https://www.faz.net/rss/aktuell/politik/ausland/",
    "NZZ": "https://www.nzz.ch/international.rss",
}

DIRECT_LINK_OUTLETS = {"taz", "Tagesschau"}

LIVETICKER_KEYWORDS = ("liveticker", "live-ticker", "newsticker", "liveblog", "live-blog")

READER_CALLOUT_KEYWORDS = ("wo waren sie", "erinnern sie sich", "wissen sie noch")
READER_CALLOUT_PREFIXES = ("erinnerungen",)


def clean_description(raw_html):
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text).strip()
    return re.sub(r"\s*mehr\.\.\.$", "", text)


def is_liveticker(title, link):
    text = f"{title} {link}".lower()
    if any(keyword in text for keyword in LIVETICKER_KEYWORDS):
        return True
    if link.rstrip("/").lower().split("-")[-1] == "live":
        return True
    return title.strip().startswith("++") or title.strip().endswith("++")


def is_reader_callout(title):
    title_lower = title.lower()
    if any(keyword in title_lower for keyword in READER_CALLOUT_KEYWORDS):
        return True
    prefix = title_lower.split(":", 1)[0].strip()
    return prefix.startswith(READER_CALLOUT_PREFIXES)


def _parse_feed(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    articles = []
    for entry in feed.entries:
        if is_liveticker(entry.title, entry.link):
            continue
        if is_reader_callout(entry.title):
            continue
        published = entry.get("published_parsed")
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "description": clean_description(getattr(entry, "summary", "")),
            "published": calendar.timegm(published) if published else 0,
        })
    return articles


ARTICLES_PER_OUTLET = 2


def _dedupe_top(articles):
    seen_links = set()
    result = []
    for a in articles:
        if a["link"] in seen_links:
            continue
        seen_links.add(a["link"])
        result.append(a)
        if len(result) == ARTICLES_PER_OUTLET:
            break
    return result


@st.cache_data(ttl=3600)
def fetch_rss(url):
    try:
        articles = _parse_feed(url)
    except Exception:
        return []
    return _dedupe_top(articles)


@st.cache_data(ttl=3600)
def fetch_rss_combined(urls):
    combined = []
    for url in urls:
        try:
            combined.extend(_parse_feed(url))
        except Exception:
            continue
    combined.sort(key=lambda a: a["published"], reverse=True)
    return _dedupe_top(combined)


def make_archive_link(url):
    return f"https://archive.is/{url}"


def german_date_label():
    today = date.today()
    return f"{WEEKDAYS_DE[today.weekday()]}, {today.day}. {MONTHS_DE[today.month - 1]} {today.year}"


@st.cache_data
def load_logo_data_uri(outlet):
    path = ASSETS_DIR / LOGO_FILES[outlet]
    mime_type, _ = mimetypes.guess_type(path.name)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


GLOBAL_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=Inter:wght@400;500;600&display=swap');

.stApp {
    background-color: #fcf8f3;
    font-family: 'Inter', sans-serif;
}

.block-container {
    padding-top: 2rem;
}

.ff-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}
.ff-date {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #5a5450;
    margin-bottom: 6px;
}
.ff-header {
    font-family: 'Source Serif 4', Georgia, serif;
    color: #1a1512;
    font-weight: 700;
    font-size: clamp(28px, 4vw, 44px);
    letter-spacing: -0.01em;
    line-height: 1;
    margin-bottom: 0;
}
.ff-toggle {
    display: inline-flex;
    padding: 3px;
    background: #f2ede6;
    border: 1px solid #dcd6d1;
    border-radius: 8px;
    gap: 2px;
    flex-shrink: 0;
}
.ff-toggle-btn {
    font-family: 'Source Serif 4', Georgia, serif !important;
    font-size: 13px;
    padding: 7px 16px;
    border-radius: 6px;
    text-decoration: none !important;
    color: #5a5450 !important;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
}
.ff-toggle-btn:hover {
    background: #e8e2da;
}
.ff-tab-input {
    display: none;
}
#ff-tab-innen:checked ~ .ff-header-row label[for="ff-tab-innen"],
#ff-tab-aussen:checked ~ .ff-header-row label[for="ff-tab-aussen"] {
    background: #1a1512 !important;
    color: #fcf8f3 !important;
}
.ff-panel {
    display: none;
}
#ff-tab-innen:checked ~ #ff-panel-innen {
    display: block;
}
#ff-tab-aussen:checked ~ #ff-panel-aussen {
    display: block;
}
.ff-rule {
    border: none;
    border-top: 1px solid #dcd6d1;
    margin: 18px 0 24px 0;
    width: 100%;
}

.ff-gallery {
    display: flex;
    gap: 1rem;
}
.ff-slide {
    flex: 1 1 0;
    min-width: 0;
}

.ff-card {
    background-color: #fffdfa;
    border-radius: 4px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
    overflow: hidden;
}
.ff-accent {
    height: 3px;
}
.ff-card-body {
    padding: 11px 12px 9px 12px;
}

@media (max-width: 768px) {
    .ff-gallery {
        overflow-x: auto;
        scroll-snap-type: x mandatory;
        -webkit-overflow-scrolling: touch;
        gap: 0;
        margin: 0 -1rem;
    }
    .ff-slide {
        flex: 0 0 100%;
        scroll-snap-align: start;
        scroll-margin-left: 1rem;
        padding: 0 1rem;
        box-sizing: border-box;
    }
}

.ff-logo-wrap {
    text-align: center;
    margin-bottom: 3px;
}
.ff-logo {
    height: 22px;
    max-width: 100%;
    object-fit: contain;
}
.ff-tag {
    text-align: center;
    font-family: 'Inter', sans-serif;
    font-size: 9px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: #857f7a;
    margin-bottom: 7px;
}

.ff-article {
    padding: 6px 0;
    border-top: 1px solid #e8e4df;
}
.ff-article:first-child {
    border-top: none;
}
.ff-article:hover {
    background: #f7f5f1;
}
.ff-headline {
    display: block;
    font-family: 'Source Serif 4', Georgia, serif;
    color: #1a1512 !important;
    text-decoration: none !important;
    font-weight: 700;
    font-size: 12.5px;
    line-height: 1.26;
}
.ff-headline:hover {
    text-decoration: underline !important;
}
.ff-headline-lead {
    font-size: 14px;
}
.ff-description {
    display: block;
    margin-top: 3px;
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 11px;
    line-height: 1.34;
    color: #5a5450;
}
.ff-original {
    display: block;
    margin-top: 0.15rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 400 !important;
    color: #857f7a !important;
    text-decoration: none !important;
}
.ff-original:hover {
    text-decoration: underline !important;
}

.ff-empty-feed {
    color: #999;
    font-style: italic;
    font-size: 0.9rem;
    padding: 0.8rem 0;
}
.ff-footer {
    text-align: center;
    margin-top: 40px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #857f7a;
}
</style>
"""


def render_card_html(outlet, articles, section):
    logo_uri = load_logo_data_uri(outlet)

    if articles:
        rows = []
        for index, a in enumerate(articles):
            lead_class = " ff-headline-lead" if index == 0 else ""
            if outlet in DIRECT_LINK_OUTLETS:
                headline_href = a["link"]
            else:
                headline_href = make_archive_link(a["link"])

            content = f'<a href="{headline_href}" target="_blank" class="ff-headline{lead_class}">{a["title"]}</a>'
            if a.get("description"):
                content += f'<span class="ff-description">{a["description"]}</span>'
            if outlet not in DIRECT_LINK_OUTLETS:
                content += f'<a class="ff-original" href="{a["link"]}" target="_blank">Original</a>'

            rows.append(f'<div class="ff-article">{content}</div>')
        body = "".join(rows)
    else:
        body = '<div class="ff-empty-feed">Feed derzeit nicht verfuegbar.</div>'

    slug = CSS_SLUGS[outlet]
    return (
        f'<div class="ff-slide ff-slide-{slug}" id="ff-slide-{section}-{slug}"><div class="ff-card">'
        f'<div class="ff-accent" style="background:{ACCENT_COLORS[outlet]}"></div>'
        '<div class="ff-card-body">'
        f'<div class="ff-logo-wrap"><img class="ff-logo" src="{logo_uri}" alt="{outlet}"></div>'
        f'<div class="ff-tag">{ORIENTATIONS[outlet]}</div>'
        f"{body}"
        "</div></div></div>"
    )


OUTLET_ORDER = ["taz", "Die Zeit", "Tagesschau", "FAZ", "NZZ"]


def render_gallery_html(feeds, section):
    slides = []
    for outlet in OUTLET_ORDER:
        source = feeds[outlet]
        articles = fetch_rss_combined(source) if isinstance(source, tuple) else fetch_rss(source)
        slides.append(render_card_html(outlet, articles, section))
    return f'<div class="ff-gallery">{"".join(slides)}</div>'


def main():
    st.set_page_config(page_title="Franzis Newsfeed", layout="wide")
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

    innen_html = render_gallery_html(INNENPOLITIK_FEEDS, "innen")
    aussen_html = render_gallery_html(AUSSENPOLITIK_FEEDS, "aussen")

    st.markdown(
        '<div class="ff-app-shell">'
        '<input type="radio" name="ff-tab" id="ff-tab-innen" class="ff-tab-input" checked>'
        '<input type="radio" name="ff-tab" id="ff-tab-aussen" class="ff-tab-input">'
        '<div class="ff-header-row">'
        f'<div><div class="ff-date">{german_date_label()}</div>'
        '<div class="ff-header">Franzis Newsfeed</div></div>'
        '<div class="ff-toggle">'
        '<label for="ff-tab-innen" class="ff-toggle-btn">Innenpolitik</label>'
        '<label for="ff-tab-aussen" class="ff-toggle-btn">Außenpolitik</label>'
        "</div>"
        "</div>"
        '<hr class="ff-rule">'
        f'<div id="ff-panel-innen" class="ff-panel">{innen_html}</div>'
        f'<div id="ff-panel-aussen" class="ff-panel">{aussen_html}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ff-footer">Quellen: taz · Die Zeit · Tagesschau · FAZ · NZZ</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
