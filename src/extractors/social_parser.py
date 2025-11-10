from typing import Any, Dict, List
from bs4 import BeautifulSoup
import re

SOCIAL_PATTERNS = {
    "twitter": re.compile(r"https?://(www\.)?twitter\.com/([A-Za-z0-9_]{1,15})", re.I),
    "x": re.compile(r"https?://(www\.)?x\.com/([A-Za-z0-9_]{1,15})", re.I),
    "facebook": re.compile(r"https?://(www\.)?facebook\.com/([A-Za-z0-9\.\-_]+)/?", re.I),
    "instagram": re.compile(r"https?://(www\.)?instagram\.com/([A-Za-z0-9\._]+)/?", re.I),
    "youtube": re.compile(r"https?://(www\.)?youtube\.com/(?:@|c/|user/)?([A-Za-z0-9\._\-]+)/?", re.I),
    "linkedin": re.compile(r"https?://(www\.)?linkedin\.com/company/([A-Za-z0-9\._\-]+)/?", re.I),
    "tiktok": re.compile(r"https?://(www\.)?tiktok\.com/@([A-Za-z0-9\._\-]+)/?", re.I),
}

def extract_social_profiles(html: str) -> List[Dict[str, Any]]:
    """
    Extract social profile URLs and usernames from HTML.
    Follower counts require platform APIs; we return None for those values here.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    profiles: List[Dict[str, Any]] = []

    # Scan anchors
    links = [a.get("href", "") for a in soup.select("a[href]")]
    # Also search raw HTML for obfuscated forms
    raw = soup.decode()

    seen = set()
    for label, pattern in SOCIAL_PATTERNS.items():
        for source in links + [raw]:
            for m in pattern.finditer(source):
                url = m.group(0)
                username = m.group(2) if label in ("twitter", "x") else m.groups()[-1]
                key = (label, username.lower())
                if key in seen:
                    continue
                seen.add(key)
                profiles.append(
                    {
                        "network": "x" if label == "x" else label,
                        "url": url,
                        "username": username,
                        "follower_count": None,
                    }
                )
    return profiles