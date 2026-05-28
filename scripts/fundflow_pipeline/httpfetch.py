"""HTTP fetching and BOK market-indicator page discovery."""

from __future__ import annotations

import re
import ssl
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from .config import (
    USER_AGENT,
    BOK_MARKET_LIST_URL,
    BOK_MARKET_RSS_URL,
    DETAIL_URL_PATTERN,
    Attachment,
)

class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._current_href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            label = " ".join("".join(self._text_parts).split())
            self.links.append((self._current_href, label))
            self._current_href = None
            self._text_parts = []


def fetch_bytes(url: str) -> bytes:
    context = ssl._create_unverified_context()
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30, context=context) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", "replace")


def extract_title(html: str) -> str:
    meta_match = re.search(
        r'<meta\s+property=["\']title["\']\s+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if meta_match:
        return meta_match.group(1).strip()

    match = re.search(r"<h[12][^>]*>\s*(.*?)\s*</h[12]>", html, re.I | re.S)
    if match:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1))).strip()
    match = re.search(r"<title>\s*(.*?)\s*</title>", html, re.I | re.S)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return "(title not found)"


def extract_attachments(page_url: str, html: str) -> list[Attachment]:
    parser = LinkParser()
    parser.feed(html)

    by_url: dict[str, Attachment] = {}
    for href, label in parser.links:
        text = unquote(" ".join([href, label]))
        if not re.search(r"\.(xlsx|xls)\b", text, re.I):
            continue
        file_label = label or Path(unquote(href).split("?")[0]).name
        absolute_url = urljoin(page_url, href)
        current = by_url.get(absolute_url)
        if current is None or re.search(r"\.(xlsx|xls)\b", file_label, re.I):
            by_url[absolute_url] = Attachment(label=file_label, url=absolute_url)

    return list(by_url.values())


def choose_balance_attachment(attachments: Iterable[Attachment]) -> Attachment:
    candidates = list(attachments)
    if not candidates:
        raise RuntimeError("No Excel attachments found on the page.")

    balance = [item for item in candidates if "잔액" in unquote(item.label)]
    if balance:
        return balance[0]
    return candidates[0]


def extract_ntt_id(url: str) -> int | None:
    parsed = urlparse(url)
    raw = parse_qs(parsed.query).get("nttId", [None])[0]
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def canonicalize_detail_url(url: str) -> str | None:
    ntt_id = extract_ntt_id(url)
    if ntt_id is None:
        return None
    return f"https://www.bok.or.kr/portal/bbs/P0002018/view.do?nttId={ntt_id}&menuNo=200366"


def extract_related_page_urls(page_url: str, html: str) -> list[str]:
    related = []
    seen = set()
    for match in DETAIL_URL_PATTERN.findall(html):
        absolute = urljoin(page_url, match)
        canonical = canonicalize_detail_url(absolute)
        if canonical and canonical not in seen:
            seen.add(canonical)
            related.append(canonical)
    return related


def discover_recent_page_urls(seed_url: str, count: int, max_pages: int = 24) -> tuple[list[str], dict[str, str]]:
    seed = canonicalize_detail_url(seed_url)
    if seed is None:
        raise RuntimeError("Seed URL does not contain nttId.")

    queue = deque([seed])
    html_cache: dict[str, str] = {}

    while queue and len(html_cache) < max_pages:
        current_url = queue.popleft()
        if current_url in html_cache:
            continue
        try:
            html = fetch_text(current_url)
        except Exception as exc:  # pragma: no cover - network boundary
            print(f"warning: failed to fetch {current_url}: {exc}")
            continue

        html_cache[current_url] = html
        for related in extract_related_page_urls(current_url, html):
            if related not in html_cache and related not in queue:
                queue.append(related)

        if len(html_cache) >= max(count + 3, count * 2):
            break

    sorted_urls = sorted(
        html_cache.keys(),
        key=lambda url: extract_ntt_id(url) or 0,
        reverse=True,
    )
    return sorted_urls[:count], html_cache


def extract_rss_page_urls(limit: int = 40) -> list[str]:
    rss = fetch_text(BOK_MARKET_RSS_URL)
    pattern = re.compile(
        r"<link><!\[CDATA\[(https://www\.bok\.or\.kr/portal/bbs/P0002018/view\.do\?[^]]+)\]\]></link>",
        re.I,
    )
    urls = []
    seen = set()
    for raw in pattern.findall(rss):
        canonical = canonicalize_detail_url(raw)
        if canonical and canonical not in seen:
            seen.add(canonical)
            urls.append(canonical)
        if len(urls) >= limit:
            break
    return urls


def safe_filename(name: str) -> str:
    cleaned = unquote(name).strip().replace("/", "_")
    return cleaned or "bok_market_indicator.xlsx"


