"""Add ?v=<content hash> to the card images in README.md.

GitHub and browsers cache images by URL, so without this the profile keeps
showing the old album or films for a while after the SVG changes.
Run: python3 scripts/bust.py
"""

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def version(match):
    path = match.group(1)
    digest = hashlib.sha1((ROOT / path).read_bytes()).hexdigest()[:8]
    return f"{path}?v={digest}"


text = README.read_text(encoding="utf-8")
new = re.sub(r"(assets/[\w-]+\.svg)(?:\?v=\w+)?", version, text)
if new != text:
    README.write_text(new, encoding="utf-8")
    print("README image versions updated")
