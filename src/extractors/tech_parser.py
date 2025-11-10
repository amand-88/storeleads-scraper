from typing import List
from bs4 import BeautifulSoup

FINGERPRINTS = {
    "Cloudflare": ["cf-ray", "__cf_bm", "cloudflare"],
    "Shopify": ["cdn.shopify.com", "Shopify.theme", "x-shopify-stage"],
    "WooCommerce": ["woocommerce_params", "woocommerce"],
    "React": ["data-reactroot", "react.development.js"],
    "Next.js": ["__NEXT_DATA__", "next/data"],
    "Vue.js": ["__VUE_DEVTOOLS_GLOBAL_HOOK__", "vue.runtime"],
    "Google Analytics": ["gtag('config'", "www.googletagmanager.com/gtag/js"],
    "Facebook Pixel": ["fbq(", "connect.facebook.net/en_US/fbevents.js"],
    "Stripe": ["js.stripe.com", "Stripe("],
    "Node.js": ["x-powered-by", "Express"],
}

def detect_technologies(html: str, domain: str = "") -> List[str]:
    """
    Naive technology detector using HTML fingerprints.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    text = soup.decode().lower()
    hits = set()
    for tech, needles in FINGERPRINTS.items():
        for n in needles:
            if n.lower() in text:
                hits.add(tech)
                break
    return sorted(hits)