"""Draw the last films logged on Letterboxd: posters, titles, ratings (light + dark).

Reads the public RSS feed, so no API key is needed.
Run: LETTERBOXD_USER=yourname python3 scripts/films.py
"""

import base64
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
COUNT = 4
NS = {"lb": "https://letterboxd.com"}

THEMES = {
    "light": {"fg": "#1f2328", "weak": "#656d76", "line": "#d0d7de", "star": "#00ac1c"},
    "dark": {"fg": "#e6edf3", "weak": "#8b949e", "line": "#30363d", "star": "#00e054"},
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rocco822-profile"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def films(user):
    root = ET.fromstring(get(f"https://letterboxd.com/{user}/rss/"))
    out = []
    for item in root.iter("item"):
        title = item.findtext("lb:filmTitle", namespaces=NS)
        if not title:          # lists and other non-diary entries
            continue
        poster = re.search(r'<img src="([^"]+)"', item.findtext("description") or "")
        if not poster:
            continue
        url = re.sub(r"-0-\d+-0-\d+-crop", "-0-230-0-345-crop", poster.group(1))
        out.append({
            "title": title,
            "year": item.findtext("lb:filmYear", namespaces=NS) or "",
            "rating": float(item.findtext("lb:memberRating", namespaces=NS) or 0),
            "liked": item.findtext("lb:memberLike", namespaces=NS) == "Yes",
            "poster": base64.b64encode(get(url)).decode(),
        })
        if len(out) == COUNT:
            break
    return out


def stars(rating):
    return "★" * int(rating) + ("½" if rating % 1 else "")


def fit(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def card(theme, items):
    c = THEMES[theme]
    pw, ph, gap = 120, 180, 20
    W, H = 720, 28 + ph + 56
    cells = []
    for i, f in enumerate(items):
        x = i * (pw + gap)
        heart = f'{" " if f["rating"] else ""}<tspan fill="{c["weak"]}">♥</tspan>' if f["liked"] else ""
        sep = "  " if f["rating"] or f["liked"] else ""
        cells.append(f"""
  <clipPath id="p{i}"><rect x="{x}" y="28" width="{pw}" height="{ph}" rx="4"/></clipPath>
  <image href="data:image/jpeg;base64,{f['poster']}" x="{x}" y="28" width="{pw}" height="{ph}" clip-path="url(#p{i})" preserveAspectRatio="xMidYMid slice"/>
  <rect x="{x + .5}" y="28.5" width="{pw - 1}" height="{ph - 1}" rx="4" fill="none" stroke="{c['line']}"/>
  <text x="{x}" y="{28 + ph + 22}" font-size="14" font-weight="600" fill="{c['fg']}">{escape(fit(f['title'], 15))}</text>
  <text x="{x}" y="{28 + ph + 42}" font-size="13" fill="{c['star']}">{stars(f['rating'])}{heart}<tspan fill="{c['weak']}">{sep}{f['year']}</tspan></text>""")
    names = ", ".join(f["title"] for f in items)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Recently watched: {escape(names)}">
  <style>text {{ font-family: {SANS}; white-space: pre; }}</style>
  <text x="0" y="14" font-size="12" font-weight="600" letter-spacing="1.5" fill="{c['weak']}">RECENTLY WATCHED</text>{"".join(cells)}
</svg>
"""


def single(theme, f):
    """One film: big poster with text beside it, same layout as the music card."""
    c = THEMES[theme]
    pw, ph = 112, 168
    W, H, tx, cy = 720, ph, 284, ph / 2  # tx matches the music card text column
    heart = f'{" " if f["rating"] else ""}<tspan fill="{c["weak"]}">♥</tspan>' if f["liked"] else ""
    sep = "  " if f["rating"] or f["liked"] else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Last watched: {escape(f['title'])}">
  <style>text {{ font-family: {SANS}; white-space: pre; }}</style>
  <clipPath id="p"><rect x="0" y="0" width="{pw}" height="{ph}" rx="4"/></clipPath>
  <image href="data:image/jpeg;base64,{f['poster']}" x="0" y="0" width="{pw}" height="{ph}" clip-path="url(#p)" preserveAspectRatio="xMidYMid slice"/>
  <rect x=".5" y=".5" width="{pw - 1}" height="{ph - 1}" rx="4" fill="none" stroke="{c['line']}"/>
  <text x="{tx}" y="{cy - 22}" font-size="12" font-weight="600" letter-spacing="1.5" fill="{c['weak']}">LAST WATCHED</text>
  <text x="{tx}" y="{cy + 10}" font-size="26" font-weight="700" fill="{c['fg']}">{escape(fit(f['title'], 30))}</text>
  <text x="{tx}" y="{cy + 38}" font-size="18" fill="{c['star']}">{stars(f['rating'])}{heart}<tspan fill="{c['weak']}">{sep}{f['year']}</tspan></text>
</svg>
"""


if __name__ == "__main__":
    user = os.environ.get("LETTERBOXD_USER") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not user:
        sys.exit("set LETTERBOXD_USER (or pass the username) to draw the films card")
    items = films(user)
    if not items:
        sys.exit(f"no diary entries found for {user!r}")
    OUT.mkdir(exist_ok=True)
    for t in THEMES:
        (OUT / f"films-{t}.svg").write_text(single(t, items[0]) if len(items) == 1 else card(t, items), encoding="utf-8")
    print(", ".join(f"{f['title']} {stars(f['rating'])}" for f in items))
