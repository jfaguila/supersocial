"""
RSS feed signal source.

Reads configured RSS/Atom feeds from tech and business media,
extracts titles and descriptions as trend signals.
"""
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

# Default feeds — tech, AI, business
DEFAULT_FEEDS: list[dict[str, str]] = [
    {"url": "https://feeds.feedburner.com/TechCrunch/", "category": "technology"},
    {"url": "https://www.theverge.com/rss/index.xml", "category": "technology"},
    {"url": "https://hnrss.org/frontpage", "category": "technology"},
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "category": "technology"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "category": "business"},
]


class RSSSource:
    """Fetch signals from RSS/Atom feeds."""

    def __init__(self, feeds: Optional[list[dict[str, str]]] = None):
        self.feeds = feeds or DEFAULT_FEEDS

    async def fetch(self) -> list[dict]:
        signals: list[dict] = []
        now = int(time.time())

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for feed_config in self.feeds:
                try:
                    resp = await client.get(feed_config["url"])
                    if resp.status_code != 200:
                        continue
                    items = self._parse_feed(resp.text)
                    category = feed_config.get("category", "general")

                    for item in items[:10]:  # top 10 per feed
                        title = item.get("title", "").strip()
                        if not title or len(title) < 5:
                            continue

                        signals.append({
                            "source": "rss",
                            "keyword": title,
                            "volume": 0,
                            "trending_score": 50.0,  # RSS items are inherently topical
                            "region": "global",
                            "category": category,
                            "raw_data": {
                                "feed_url": feed_config["url"],
                                "link": item.get("link", ""),
                                "description": item.get("description", "")[:500],
                                "pub_date": item.get("pub_date", ""),
                            },
                            "captured_at": now,
                        })
                except Exception:
                    continue

        return signals

    def _parse_feed(self, xml_text: str) -> list[dict]:
        """Parse RSS 2.0 or Atom feed into list of {title, link, description, pub_date}."""
        items: list[dict] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return items

        # RSS 2.0
        for item in root.iter("item"):
            items.append({
                "title": self._text(item, "title"),
                "link": self._text(item, "link"),
                "description": self._strip_html(self._text(item, "description")),
                "pub_date": self._text(item, "pubDate"),
            })

        # Atom
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                link_el = entry.find("atom:link", ns)
                items.append({
                    "title": self._text_ns(entry, "title", ns),
                    "link": link_el.get("href", "") if link_el is not None else "",
                    "description": self._strip_html(
                        self._text_ns(entry, "summary", ns)
                        or self._text_ns(entry, "content", ns)
                    ),
                    "pub_date": self._text_ns(entry, "published", ns)
                              or self._text_ns(entry, "updated", ns),
                })

        return items

    @staticmethod
    def _text(el: ET.Element, tag: str) -> str:
        child = el.find(tag)
        return (child.text or "").strip() if child is not None else ""

    @staticmethod
    def _text_ns(el: ET.Element, tag: str, ns: dict) -> str:
        child = el.find(f"atom:{tag}", ns)
        return (child.text or "").strip() if child is not None else ""

    @staticmethod
    def _strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()
