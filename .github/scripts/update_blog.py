#!/usr/bin/env python3
"""Update the recent blog posts section in the profile README from the blog RSS feed."""

from __future__ import annotations

import argparse
import email.utils
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from pathlib import Path

START = "<!-- BLOG-POSTS:START -->"
END = "<!-- BLOG-POSTS:END -->"


def fetch_posts(feed_url: str, limit: int) -> list[tuple[str, str, str]]:
    if feed_url.startswith(("http://", "https://")):
        request = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "HGT158-profile-readme-updater/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
    else:
        payload = Path(feed_url).read_bytes()
    root = ET.fromstring(payload)

    posts: list[tuple[str, str, str]] = []
    for item in root.findall("./channel/item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        date = ""
        if published:
            parsed = email.utils.parsedate_to_datetime(published)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            date = parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")
        safe_title = title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
        posts.append((safe_title, link, date))
    return posts


def render(posts: list[tuple[str, str, str]]) -> str:
    lines = [START, "## 最近文章", ""]
    lines.extend(
        f"- [{title}]({link})" + (f" · {date}" if date else "")
        for title, link, date in posts
    )
    lines.extend(["", END])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--feed", default="https://blog.20061107.xyz/rss.xml")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    readme = Path(args.readme)
    content = readme.read_text(encoding="utf-8")
    section = render(fetch_posts(args.feed, args.limit))
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(content):
        raise SystemExit(f"README is missing {START} / {END} markers")
    updated = pattern.sub(section, content, count=1)
    if updated != content:
        readme.write_text(updated.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


