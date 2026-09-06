import base64
import mimetypes
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

RSS_FEEDS = {
    "taz": "https://taz.de/!p4608;rss/",
    "Die Zeit": "https://newsfeed.zeit.de/index",
    "FAZ": "https://www.faz.net/rss/aktuell/",
    "NZZ": "https://www.nzz.ch/recent.rss",
}

TAGESSCHAU_URL = "https://www.tagesschau.de/api2u/homepage"

DIRECT_LINK_OUTLETS = {"taz", "Tagesschau"}

LIVETICKER_KEYWORDS = ("liveticker", "live-ticker", "newsticker", "liveblog", "live-blog")


def is_liveticker(title, link):
    text = f"{title} {link}".lower()
    if any(keyword in text for keyword in LIVETICKER_KEYWORDS):
        return True
    if link.rstrip("/").lower().split("-")[-1] == "live":
        return True
    return title.strip().startswith("++") or title.strip().endswith("++")


@st.cache_data(ttl=3600)
def fetch_rss(url):
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        seen_links = set()
        articles = []
        for entry in feed.entries:
            if entry.link in seen_links or is_liveticker(entry.title, entry.link):
                continue
            seen_links.add(entry.link)
            articles.append({"title": entry.title, "link": entry.link})
        return articles[:3]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def fetch_tagesschau():
    try:
        response = requests.get(
            TAGESSCHAU_URL, headers={"User-Agent": USER_AGENT}, timeout=10
        )
        response.raise_for_status()
        data = response.json()
        items = []
        for entry in data.get("news", []):
            link = entry.get("shareURL") or entry.get("detailsweb")
            title = entry.get("title")
            if title and link and not is_liveticker(title, link):
                items.append({"title": title, "link": link})
            if len(items) == 3:
                break
        return items
    except Exception:
        return []


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

.ff-date {
    text-align: center;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #5a5450;
    margin-bottom: 10px;
}
.ff-header {
    text-align: center;
    font-family: 'Source Serif 4', Georgia, serif;
    color: #1a1512;
    font-weight: 700;
    font-size: clamp(34px, 5vw, 52px);
    letter-spacing: -0.01em;
    line-height: 1;
    margin-bottom: 0;
}
.ff-rule {
    border: none;
    border-top: 1px solid #dcd6d1;
    margin: 26px auto 32px auto;
    width: 60%;
    max-width: 220px;
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
    padding: 16px 16px 14px 16px;
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
    margin-bottom: 6px;
}
.ff-logo {
    height: 28px;
    max-width: 100%;
    object-fit: contain;
}
.ff-tag {
    text-align: center;
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: #857f7a;
    margin-bottom: 12px;
}

.ff-article {
    padding: 10px 0;
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
    font-weight: 400;
    font-size: 14.5px;
    line-height: 1.32;
}
.ff-headline:hover {
    text-decoration: underline !important;
}
.ff-headline-lead {
    font-weight: 700;
    font-size: 16px;
}
.ff-original {
    display: block;
    margin-top: 0.2rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
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


def render_card_html(outlet, articles):
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
            if outlet not in DIRECT_LINK_OUTLETS:
                content += f'<a class="ff-original" href="{a["link"]}" target="_blank">Original</a>'

            rows.append(f'<div class="ff-article">{content}</div>')
        body = "".join(rows)
    else:
        body = '<div class="ff-empty-feed">Feed derzeit nicht verfuegbar.</div>'

    slug = CSS_SLUGS[outlet]
    return (
        f'<div class="ff-slide ff-slide-{slug}" id="ff-slide-{slug}"><div class="ff-card">'
        f'<div class="ff-accent" style="background:{ACCENT_COLORS[outlet]}"></div>'
        '<div class="ff-card-body">'
        f'<div class="ff-logo-wrap"><img class="ff-logo" src="{logo_uri}" alt="{outlet}"></div>'
        f'<div class="ff-tag">{ORIENTATIONS[outlet]}</div>'
        f"{body}"
        "</div></div></div>"
    )


def main():
    st.set_page_config(page_title="Franzis Newsfeed", layout="wide")
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

    st.markdown(
        f'<div class="ff-date">{german_date_label()}</div>'
        '<div class="ff-header">Franzis Newsfeed</div>'
        '<hr class="ff-rule">',
        unsafe_allow_html=True,
    )

    outlets = ["taz", "Die Zeit", "Tagesschau", "FAZ", "NZZ"]
    slides = [
        render_card_html(
            outlet,
            fetch_tagesschau() if outlet == "Tagesschau" else fetch_rss(RSS_FEEDS[outlet]),
        )
        for outlet in outlets
    ]

    st.markdown(f'<div class="ff-gallery">{"".join(slides)}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="ff-footer">Quellen: taz · Die Zeit · Tagesschau · FAZ · NZZ</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
