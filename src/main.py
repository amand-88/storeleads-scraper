import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

# Local imports
from utils.http_client import HttpClient
from utils.json_exporter import JsonExporter
from extractors.company_parser import parse_company_page
from extractors.trustpilot_parser import enrich_with_trustpilot
from extractors.tech_parser import detect_technologies
from extractors.social_parser import extract_social_profiles

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("storeleads-scraper")

def read_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                yield line

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Storeleads Scraper: extract structured ecommerce intelligence."
    )
    p.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample_input.txt"),
        help="Path to a file containing Storeleads search URLs (one per line).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("data/sample_output.json"),
        help="Path to write JSON array output.",
    )
    p.add_argument(
        "--cookies",
        type=str,
        default=os.getenv("STORELEADS_COOKIES", ""),
        help="Raw cookie string (e.g. 'key=value; key2=value2').",
    )
    p.add_argument(
        "--cookies-file",
        type=Path,
        help="Path to a file containing raw cookie string.",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="(Reserved) Concurrency level. Requests are currently sequential for stability.",
    )
    p.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (generate deterministic synthetic data without network).",
    )
    p.add_argument(
        "--user-agent",
        type=str,
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) StoreleadsScraper/1.0 Safari/537.36",
    )
    return p

def load_cookies_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    return text

def synthesize_from_query(query: str) -> Dict[str, Any]:
    """
    Deterministic synthetic record used in --mock mode.
    Converts an input line (Storeleads URL or search text) into a realistic record.
    """
    import hashlib
    h = hashlib.sha256(query.encode("utf-8")).hexdigest()
    seed = int(h[:8], 16)
    # Some deterministic pseudo-values
    monthly_visits = (seed % 5_000_000) + 100_000
    employees = (seed % 5000) + 10
    sales = (seed % 5_000_000) * 2.37
    tp_rating = round(((seed % 45) / 10.0) + 1.0, 1)  # 1.0 - 5.4 -> cap to 5.0 later

    domain_guess = query
    if "://" in query:
        domain_guess = query.split("://", 1)[1].split("/", 1)[0]
    elif "/" in query:
        domain_guess = query.split("/", 1)[0]

    record = {
        "region": "Americas",
        "detailed_region": "Northern America",
        "title": domain_guess.split(".")[0].capitalize(),
        "domain": domain_guess,
        "monthly_sales": f"USD ${sales:,.2f}",
        "annual_sales": f"USD ${sales*12:,.2f}",
        "location": "Remote",
        "country": "United States",
        "employees": employees,
        "monthly_visits": monthly_visits,
        "monthly_page_views": int(monthly_visits * 2.7),
        "trustpilot_avg_rating": min(tp_rating, 5.0),
        "trustpilot_review_count": (seed % 50000),
        "social_networks": [
            {
                "url": f"https://twitter.com/{domain_guess.split('.')[0]}",
                "username": domain_guess.split(".")[0],
                "follower_count": (seed % 2_000_000),
            }
        ],
        "technologies": ["Cloudflare", "React", "Node.js"],
        "cluster_domains": [
            domain_guess,
            f"www.{domain_guess}",
            f"shop.{domain_guess}",
        ],
        "features": ["https", "cdn", "spa"],
        "source_query": query,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "mock": True,
    }
    return record

def process_query(query: str, client: HttpClient, mock: bool) -> List[Dict[str, Any]]:
    """
    Given a single Storeleads search URL or term, return a list of company records.
    In real mode, we attempt to fetch and parse; in mock mode, we synthesize one record per line.
    """
    if mock:
        return [synthesize_from_query(query)]

    logger.info("Fetching search URL: %s", query)
    html = client.get_text(query)
    # Parse company rows from search results
    companies = parse_company_page(html, base_url=query)
    enriched: List[Dict[str, Any]] = []
    for company in companies:
        # Enrich with social profiles, technologies and trustpilot
        company["social_networks"] = extract_social_profiles(company.get("html", ""))
        company["technologies"] = detect_technologies(company.get("html", ""), company.get("domain", ""))
        company = enrich_with_trustpilot(company, client)
        # housekeeping
        company.pop("html", None)
        company["source_query"] = query
        company["scraped_at"] = datetime.utcnow().isoformat() + "Z"
        company["mock"] = False
        enriched.append(company)
    return enriched

def main() -> int:
    args = build_arg_parser().parse_args()

    cookies = args.cookies
    if args.cookies_file:
        try:
            cookies = load_cookies_from_file(args.cookies_file)
        except Exception as e:
            logger.error("Failed to read cookies file: %s", e)
            return 2

    # If no cookies provided, default to mock mode for reliability.
    mock = args.mock or (cookies.strip() == "")
    if mock:
        logger.warning("Running in MOCK mode (no network requests will be made).")
    else:
        logger.info("Running in LIVE mode with provided cookies.")

    client = HttpClient(
        cookies=cookies,
        user_agent=args.user_agent,
    )

    queries = list(read_lines(args.input))
    if not queries:
        logger.error("Input file %s contains no queries/URLs.", args.input)
        return 3

    all_records: List[Dict[str, Any]] = []
    for q in queries:
        try:
            all_records.extend(process_query(q, client, mock))
        except Exception as e:
            logger.exception("Error while processing query %s: %s", q, e)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    JsonExporter.write_array(args.output, all_records)
    logger.info("Wrote %d records to %s", len(all_records), args.output)
    return 0

if __name__ == "__main__":
    sys.exit(main())