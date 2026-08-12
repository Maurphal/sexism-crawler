# -*- coding: utf-8 -*-
"""
Ευγενικό fetching σελίδων: σέβεται πάντα το robots.txt (μέσω urllib.robotparser),
κρατάει καθυστέρηση ανάμεσα σε requests προς το ίδιο domain, και εξάγει το κύριο
ορατό κείμενο της σελίδας (χωρίς <script>, <style>, menus κ.λπ.) με BeautifulSoup.
"""
from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "InclusiveLanguageCrawler/1.0 (+https://github.com/YOUR_USERNAME/YOUR_REPO)"
DEFAULT_DELAY_SECONDS = 3.0
REQUEST_TIMEOUT = 15

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_fetch_time: dict[str, float] = {}


@dataclass
class FetchResult:
    url: str
    ok: bool
    text: str = ""
    error: str = ""
    status_code: int | None = None
    skipped_by_robots: bool = False


def _get_robots_parser(base_url: str) -> urllib.robotparser.RobotFileParser:
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(origin + "/robots.txt")
        try:
            rp.read()
        except Exception:
            # Αν το robots.txt δεν είναι προσβάσιμο, προχωράμε σαν να επιτρέπει
            # τα πάντα (στάνταρ πρακτική· πολλοί μικροί ιστότοποι απλά δεν
            # έχουν robots.txt).
            pass
        _robots_cache[origin] = rp
    return _robots_cache[origin]


def is_allowed(url: str) -> bool:
    rp = _get_robots_parser(url)
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def _respect_delay(url: str) -> None:
    parsed = urlparse(url)
    domain = parsed.netloc
    rp = _get_robots_parser(url)
    delay = None
    try:
        delay = rp.crawl_delay(USER_AGENT)
    except Exception:
        pass
    wait_for = float(delay) if delay else DEFAULT_DELAY_SECONDS

    last = _last_fetch_time.get(domain)
    now = time.monotonic()
    if last is not None:
        elapsed = now - last
        if elapsed < wait_for:
            time.sleep(wait_for - elapsed)
    _last_fetch_time[domain] = time.monotonic()


def extract_main_text(html: str) -> str:
    """Αφαιρεί script/style/nav/header/footer/aside και επιστρέφει το ορατό κείμενο."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def fetch(url: str) -> FetchResult:
    if not is_allowed(url):
        return FetchResult(url=url, ok=False, skipped_by_robots=True,
                            error="Απαγορεύεται από το robots.txt")

    _respect_delay(url)

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return FetchResult(url=url, ok=False, error=str(exc))

    if resp.status_code != 200:
        return FetchResult(url=url, ok=False, status_code=resp.status_code,
                            error=f"HTTP {resp.status_code}")

    resp.encoding = resp.encoding or "utf-8"
    text = extract_main_text(resp.text)
    return FetchResult(url=url, ok=True, text=text, status_code=resp.status_code)
