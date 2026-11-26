"""Draw the "on repeat" record: album sleeve with a spinning vinyl (light + dark).

Where the album comes from:
  - LASTFM_API_KEY and LASTFM_USER set -> your most played album of the last 7 days
  - otherwise -> music.txt, one line: "Artist" or "Artist — Album"
The cover comes from the iTunes Search API, or Deezer as a fallback (no keys) and is embedded in the SVG,
because GitHub does not load external images inside an SVG.

Run: python3 scripts/music.py
"""

import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
MANUAL = ROOT / "music.txt"

THEMES = {
    "light": {"fg": "#1f2328", "weak": "#656d76", "sleeve": "#d0d7de", "rim": "#111"},
    "dark": {"fg": "#e6edf3", "weak": "#8b949e", "sleeve": "#30363d", "rim": "#484f58"},
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"


def get(url, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": "rocco822-profile"})
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception:
            if attempt == tries:
                raise
            time.sleep(attempt * 5)


def from_lastfm(key, user):
    q = urllib.parse.urlencode({"method": "user.gettopalbums", "user": user, "api_key": key,
                                "period": "7day", "limit": 1, "format": "json"})
    albums = json.loads(get(f"https://ws.audioscrobbler.com/2.0/?{q}"))["topalbums"]["album"]
    if not albums:
        return None
    return albums[0]["artist"]["name"], albums[0]["name"]


def from_file():
    line = MANUAL.read_text(encoding="utf-8").strip().splitlines()[0]
    for sep in (" — ", " - "):
        if sep in line:
            artist, album = line.split(sep, 1)
            return artist.strip(), album.strip()
    return line.strip(), None


def norm(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def matches(want_artist, want_album, artist, album):
    if norm(want_artist) not in norm(artist) and norm(artist) not in norm(want_artist):
        return False
    return not want_album or norm(want_album) in norm(album)


def itunes(artist, album):
    for term in dict.fromkeys(filter(None, [f"{artist} {album or ''}".strip(), album, artist])):
        q = urllib.parse.urlencode({"term": term, "entity": "album", "limit": 25, "country": "it"})
        for r in json.loads(get(f"https://itunes.apple.com/search?{q}"))["results"]:
            if matches(artist, album, r["artistName"], r["collectionName"]):
                return r["collectionName"], r["artistName"], r["artworkUrl100"].replace("100x100bb", "400x400bb")


def deezer(artist, album):
    q = urllib.parse.urlencode({"q": f"{artist} {album or ''}".strip()})
    for r in json.loads(get(f"https://api.deezer.com/search/album?{q}")).get("data", []):
        if matches(artist, album, r["artist"]["name"], r["title"]):
            return r["title"], r["artist"]["name"], r["cover_big"]


def cover(artist, album):
    """Return (album title, artist, base64 jpeg). Only accepts a result whose artist
    and album actually match, so a bad search never puts the wrong cover on the card."""
    for source in (itunes, deezer):
        try:
            hit = source(artist, album)
        except Exception as e:
            print(f"warning: {source.__name__} failed ({e})", file=sys.stderr)
            continue
        if hit:
            name, artist_name, url = hit
            return album or name, artist_name, base64.b64encode(get(url)).decode()
    raise LookupError(f"no cover found for {artist!r} / {album!r}")


def fit(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def record(theme, title, artist, img):
    c = THEMES[theme]
    s = 168                      # sleeve size
    cx, cy, r = s - 8 + 6, s / 2, s / 2 - 6   # vinyl peeks out on the right
    grooves = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{g}" fill="none" stroke="#2a2a2a" stroke-width="1"/>'
        for g in range(int(r) - 6, 34, -7)
    )
    W, H = 720, s
    tx = cx + r + 40
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="On repeat this week: {escape(title)} by {escape(artist)}">
  <defs>
    <clipPath id="label"><circle cx="{cx}" cy="{cy}" r="30"/></clipPath>
    <clipPath id="sleeve"><rect x="0" y="0" width="{s}" height="{s}" rx="4"/></clipPath>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset=".45" stop-color="#fff" stop-opacity=".10"/>
      <stop offset=".55" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: {SANS}; }}
    .spin {{ transform-origin: {cx}px {cy}px; animation: spin 6s linear infinite; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    @media (prefers-reduced-motion: reduce) {{ .spin {{ animation: none; }} }}
  </style>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#111" stroke="{c['rim']}" stroke-width="1.5"/>
  <g class="spin">
    {grooves}
    <image href="data:image/jpeg;base64,{img}" x="{cx - 30}" y="{cy - 30}" width="60" height="60" clip-path="url(#label)" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#shine)"/>
  <circle cx="{cx}" cy="{cy}" r="3.5" fill="{c['sleeve']}"/>
  <image href="data:image/jpeg;base64,{img}" x="0" y="0" width="{s}" height="{s}" clip-path="url(#sleeve)" preserveAspectRatio="xMidYMid slice"/>
  <rect x="0.5" y="0.5" width="{s - 1}" height="{s - 1}" rx="4" fill="none" stroke="{c['sleeve']}"/>
  <text x="{tx}" y="{cy - 22}" font-size="12" font-weight="600" letter-spacing="1.5" fill="{c['weak']}">ON REPEAT THIS WEEK</text>
  <text x="{tx}" y="{cy + 10}" font-size="26" font-weight="700" fill="{c['fg']}">{escape(fit(title, 26))}</text>
  <text x="{tx}" y="{cy + 38}" font-size="18" fill="{c['weak']}">{escape(fit(artist, 34))}</text>
</svg>
"""


if __name__ == "__main__":
    key, user = os.environ.get("LASTFM_API_KEY"), os.environ.get("LASTFM_USER")
    picked = None
    if key and user:
        try:
            picked = from_lastfm(key, user)
        except Exception as e:
            # A Last.fm hiccup shouldn't swap the card for music.txt or fail the workflow.
            print(f"warning: last.fm failed ({e}), keeping the current card", file=sys.stderr)
            sys.exit(0)
    artist, album = picked or from_file()
    try:
        title, artist_name, img = cover(artist, album)
    except Exception as e:
        # Keep the previous card rather than failing the whole workflow.
        print(f"warning: cover lookup failed ({e}), keeping the current card", file=sys.stderr)
        sys.exit(0)
    OUT.mkdir(exist_ok=True)
    for t in THEMES:
        (OUT / f"music-{t}.svg").write_text(record(t, title, artist, img), encoding="utf-8")
    print(f"{title} — {artist} ({'last.fm' if picked else 'music.txt'})")
