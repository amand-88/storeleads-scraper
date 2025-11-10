from typing import Any, Dict, List
from bs4 import BeautifulSoup

def _safe_text(node) -> str:
    return " ".join((node.get_text(separator=" ", strip=True) if node else "").split())

def parse_company_page(html: str, base_url: str = "") -> List[Dict[str, Any]]:
    """
    Parse a Storeleads search results HTML page to extract company rows.
    This parser is heuristic and resilient, focusing on commonly available fields.

    Returns a list of dicts. Each dict MAY include a temporary 'html' field
    (raw snippet) for downstream parsers (social/tech).
    """
    soup = BeautifulSoup(html or "", "lxml")
    results: List[Dict[str, Any]] = []

    # Heuristic 1: search for cards/rows that resemble company tiles
    cards = soup.select(".company, .result, .store, .company-card, li, .row")
    if not cards:
        # If we can't find specific containers, fallback to whole document as one
        title = _safe_text(soup.find("title"))
        results.append(
            {
                "region": "",
                "detailed_region": "",
                "title": title or "Unknown",
                "domain": "",
                "monthly_sales": "",
                "annual_sales": "",
                "location": "",
                "country": "",
                "employees": None,
                "monthly_visits": None,
                "monthly_page_views": None,
                "trustpilot_avg_rating": None,
                "trustpilot_review_count": None,
                "social_networks": [],
                "technologies": [],
                "cluster_domains": [],
                "features": [],
                "html": html,
            }
        )
        return results

    for c in cards:
        snippet_html = str(c)
        # Extract plausible fields via common patterns
        title_el = c.select_one(".name, .title, h2, h3, .company-name")
        domain_el = c.select_one("a[href*='http']")
        loc_el = c.select_one(".location, .address, .country")

        record = {
            "region": "",
            "detailed_region": "",
            "title": _safe_text(title_el),
            "domain": (domain_el.get("href", "") if domain_el else ""),
            "monthly_sales": "",
            "annual_sales": "",
            "location": _safe_text(loc_el),
            "country": "",
            "employees": None,
            "monthly_visits": None,
            "monthly_page_views": None,
            "trustpilot_avg_rating": None,
            "trustpilot_review_count": None,
            "social_networks": [],
            "technologies": [],
            "cluster_domains": [],
            "features": [],
            "html": snippet_html,
        }
        results.append(record)

    return results