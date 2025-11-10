from typing import Any, Dict, Optional
from bs4 import BeautifulSoup
import re

def _extract_tp_rating(text: str) -> Optional[float]:
    # Find patterns like "4.2" or "Rating 4.2"
    m = re.search(r"([0-5](?:\.\d)?)\s*/?\s*5", text)
    if m:
        try:
            val = float(m.group(1))
            return max(0.0, min(val, 5.0))
        except ValueError:
            return None
    m2 = re.search(r"\b([0-5](?:\.\d)?)\b", text)
    if m2:
        try:
            val = float(m2.group(1))
            return max(0.0, min(val, 5.0))
        except ValueError:
            return None
    return None

def _extract_tp_count(text: str) -> Optional[int]:
    # Find "12,345 reviews"
    m = re.search(r"([\d,]+)\s+reviews?", text, flags=re.I)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None

def enrich_with_trustpilot(company: Dict[str, Any], client) -> Dict[str, Any]:
    """
    Best-effort enrichment via Trustpilot if a domain is present.
    This function is resilient: if network or parsing fails, original company is returned.
    """
    domain = (company.get("domain") or "").strip()
    if not domain:
        return company

    # Only attempt if client allows network (mock mode will just have client disabled)
    try:
        url = f"https://www.trustpilot.com/review/{domain.replace('https://', '').replace('http://', '').strip('/')}"
        html = client.get_text(url)
        soup = BeautifulSoup(html or "", "lxml")
        body_text = soup.get_text(separator=" ", strip=True)

        rating = _extract_tp_rating(body_text)
        count = _extract_tp_count(body_text)

        if rating is not None:
            company["trustpilot_avg_rating"] = rating
        if count is not None:
            company["trustpilot_review_count"] = count
        return company
    except Exception:
        # Keep existing values if any
        return company