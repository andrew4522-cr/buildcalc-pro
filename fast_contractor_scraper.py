#!/usr/bin/env python3
"""
BuildCalc Pro — High-Speed Automated Contractor Lead Scraper
Compiles verified trade contractor leads (Roofing, Concrete, Framing, Drywall, Paint, Tile, Decking)
with direct email addresses, websites, and Hormozi outreach copy.
"""

import os
import re
import csv
import json
import time
import html
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ContractorScraper")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SITE_BASE_URL = "https://andrew4522-cr.github.io/buildcalc-pro"

# Strict email regex requiring alphabetic TLD
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10}\b")

IGNORED_DOMAINS = {
    "sentry.io", "wix.com", "wixpress.com", "example.com", "domain.com",
    "company.com", "wordpress.org", "wordpress.com", "schema.org", "googleapis.com",
    "cloudflare.com", "google.com", "facebook.com", "instagram.com",
    "twitter.com", "linkedin.com", "youtube.com", "yelp.com", "bbb.org",
    "angi.com", "homeadvisor.com", "thumbtack.com", "houzz.com",
    "porch.com", "yellowpages.com", "mapquest.com", "apple.com",
    "aeroleads.com", "hubspot.com", "snov.io", "apollo.io", "leadconnect.io"
}

IGNORED_PREFIXES = {
    "you@", "yourname@", "email@", "name@", "test@", "example@", "support@aeroleads.com",
    "user@", "admin@domain.com", "intl-segmenter@"
}

IGNORED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css", ".js", ".woff", ".woff2")

TRADE_CONFIG = {
    "roofing": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "concrete": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "framing": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "drywall": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "painting": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "tiling": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "decking": ("decking", "deck-material-calculator.html", "decking boards, joists & fasteners"),
    "handyman": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
    "masonry": ("concrete", "block-wall-cinder-calculator.html", "concrete yardage, block walls & mortar"),
}

CITIES = [
    # US Sunbelt & West
    ("Austin", "TX"), ("Dallas", "TX"), ("Houston", "TX"), ("San Antonio", "TX"), ("Fort Worth", "TX"),
    ("Phoenix", "AZ"), ("Tucson", "AZ"), ("Mesa", "AZ"), ("Scottsdale", "AZ"),
    ("Miami", "FL"), ("Orlando", "FL"), ("Tampa", "FL"), ("Jacksonville", "FL"), ("St. Petersburg", "FL"),
    ("Denver", "CO"), ("Colorado Springs", "CO"), ("Aurora", "CO"),
    ("Las Vegas", "NV"), ("Reno", "NV"),
    ("San Diego", "CA"), ("Los Angeles", "CA"), ("San Jose", "CA"), ("Sacramento", "CA"),
    ("Seattle", "WA"), ("Spokane", "WA"), ("Tacoma", "WA"),
    ("Portland", "OR"), ("Salt Lake City", "UT"),
    # US Midwest & East
    ("Atlanta", "GA"), ("Savannah", "GA"),
    ("Charlotte", "NC"), ("Raleigh", "NC"), ("Greensboro", "NC"),
    ("Nashville", "TN"), ("Memphis", "TN"), ("Knoxville", "TN"),
    ("Chicago", "IL"), ("Naperville", "IL"),
    ("Columbus", "OH"), ("Cleveland", "OH"), ("Cincinnati", "OH"),
    ("Indianapolis", "IN"), ("Detroit", "MI"), ("Grand Rapids", "MI"),
    ("Philadelphia", "PA"), ("Pittsburgh", "PA"),
    ("Boston", "MA"), ("Richmond", "VA"), ("Virginia Beach", "VA"),
    # UK & Ireland
    ("London", "UK"), ("Birmingham", "UK"), ("Manchester", "UK"), ("Leeds", "UK"),
    ("Glasgow", "UK"), ("Sheffield", "UK"), ("Bristol", "UK"), ("Newcastle", "UK"),
    ("Dublin", "Ireland"), ("Cork", "Ireland"), ("Galway", "Ireland"), ("Limerick", "Ireland"),
    # Canada & Australia
    ("Toronto", "Canada"), ("Vancouver", "Canada"), ("Calgary", "Canada"), ("Ottawa", "Canada"),
    ("Sydney", "Australia"), ("Melbourne", "Australia"), ("Brisbane", "Australia"), ("Perth", "Australia"),
]


def resolve_trade(trade_str: str) -> tuple[str, str, str]:
    t = trade_str.lower()
    for key, val in TRADE_CONFIG.items():
        if key in t:
            return val
    return ("contractor", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes")


def build_hormozi_copy(company_name: str, trade: str, city: str) -> dict:
    trade_label, slug, math_desc = resolve_trade(trade)
    tool_url = f"{SITE_BASE_URL}/{slug}?utm_source=outreach&utm_medium=email&utm_campaign={trade_label}"
    clean_company = html.unescape(company_name.strip()) if company_name else "there"
    city_clause = f" around {city}" if city else ""

    subj_1 = f"Tired of writing {trade_label} bids at 9 PM?"
    body_1 = f"""Hey {clean_company} team,

Most contractors I talk to{city_clause} do the same thing: measure the job during the day, then spend 2 hours at their kitchen table at night writing estimates in Excel or on a notepad.

It kills your evenings and loses you jobs to guys who quote on the spot.

I built a dead-simple estimator for your phone and laptop (BuildCalc):
{tool_url}

You plug in the job dimensions (feet, inches, fractions), it calculates your {math_desc} automatically with waste %, and turns it into a branded PDF quote with your logo in 60 seconds.

No $60/month subscriptions (Jobber/QuickBooks). No 40-minute onboarding setup. No login or credit card required.

You can use it 100% free on your next bid here:
{tool_url}

If you like it, cool. If not, you still got a free estimate out of it.

Best,
BuildCalc Pro Team"""

    subj_2 = f"quick question about {clean_company}'s bidding process"
    body_2 = f"""Hey {clean_company} team,

If you could hand a homeowner an itemized, professional PDF quote while still standing in their driveway—and close the job before your competitors even open their email—would that be useful to you?

Big software companies charge $50 to $150 every single month for bloated apps that take a week to learn.

We built the opposite for {trade_label} pros:
- Zero setup: Open it on your phone or computer, type the job measurements in feet & inches.
- Automatic trade math: Calculates {math_desc} + labor + your markup instantly.
- Looks like a Fortune 500 company: Drops it into a clean PDF with your logo and a signature block.

No login required, no credit card, and completely free to test on your next bid:
{tool_url}

Hope it saves you a couple of hours this week.

Best,
BuildCalc Pro Team"""

    return {
        "trade_category": trade_label,
        "landing_url": tool_url,
        "subject_v1": subj_1,
        "body_v1": body_1,
        "subject_v2": subj_2,
        "body_v2": body_2,
    }


def is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    email = email.lower().strip()
    if any(email.startswith(p) for p in IGNORED_PREFIXES):
        return False
    domain = email.split("@")[-1]
    if domain in IGNORED_DOMAINS or any(domain.endswith("." + d) for d in IGNORED_DOMAINS):
        return False
    # Ensure TLD is purely letters between 2 and 10 chars
    parts = domain.split(".")
    if len(parts) < 2 or not parts[-1].isalpha() or not (2 <= len(parts[-1]) <= 10):
        return False
    return True


def search_ddg(query: str, max_links: int = 15) -> list[str]:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    urls = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html_text = resp.read().decode("utf-8", errors="ignore")
            raw_links = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"', html_text)
            for link in raw_links:
                if "uddg=" in link:
                    actual = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                else:
                    actual = link
                if actual.startswith("http"):
                    domain = urllib.parse.urlparse(actual).netloc.lower().replace("www.", "")
                    if not any(ign in domain for ign in IGNORED_DOMAINS):
                        urls.append(actual)
                if len(urls) >= max_links:
                    break
    except Exception as e:
        logger.debug(f"DDG query '{query}' error: {e}")
    return urls


def crawl_site_for_email(base_url: str, timeout: int = 7) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    name_guess = parsed.netloc.replace("www.", "").split(".")[0].replace("-", " ").title()

    urls_to_try = [root, f"{root}/contact", f"{root}/contact-us", f"{root}/about", f"{root}/about-us"]

    found_email = ""
    for u in urls_to_try:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                html_text = r.read(200_000).decode("utf-8", errors="ignore")

                if u == root:
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE)
                    if title_match:
                        raw_title = title_match.group(1).split("|")[0].split("-")[0].strip()
                        raw_title = html.unescape(raw_title)
                        if 3 < len(raw_title) < 50:
                            name_guess = raw_title

                for match in EMAIL_REGEX.findall(html_text):
                    em = match.strip().lower().rstrip(".")
                    if is_valid_email(em):
                        found_email = em
                        return found_email, name_guess
        except Exception:
            continue

    return "", name_guess


def clean_existing_leads(json_path: Path, csv_path: Path):
    if not json_path.exists():
        return [], set(), set()
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            leads = json.load(f)
        cleaned = []
        seen_emails = set()
        seen_domains = set()
        for l in leads:
            em = (l.get("email") or "").lower().strip()
            if is_valid_email(em) and em not in seen_emails:
                seen_emails.add(em)
                l["company_name"] = html.unescape(l.get("company_name", ""))
                site = l.get("website", "")
                if site:
                    dom = urllib.parse.urlparse(site).netloc.lower().replace("www.", "")
                    seen_domains.add(dom)
                cleaned.append(l)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        if cleaned:
            fieldnames = list(cleaned[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(cleaned)
        logger.info(f"Cleaned queue: {len(cleaned)} verified leads active.")
        return cleaned, seen_emails, seen_domains
    except Exception as e:
        logger.error(f"Error cleaning leads: {e}")
        return [], set(), set()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BuildCalc Fast Contractor Scraper")
    parser.add_argument("--target", type=int, default=1000, help="Target total verified leads")
    parser.add_argument("--workers", type=int, default=16, help="Worker threads for crawling")
    args = parser.parse_args()

    out_dir = Path(__file__).parent / "dist" / "outreach"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "contractor_leads_queue.json"
    csv_path = out_dir / "contractor_leads_queue.csv"

    leads, seen_emails, seen_domains = clean_existing_leads(json_path, csv_path)

    if len(leads) >= args.target:
        logger.info(f"Queue already has {len(leads)} leads (target: {args.target}). Exiting.")
        return

    logger.info(f"Starting scrape: currently {len(leads)} leads, target {args.target}...")

    trades = list(TRADE_CONFIG.keys())

    for city_name, state_or_country in CITIES:
        if len(leads) >= args.target:
            break

        for trade in trades:
            if len(leads) >= args.target:
                break

            query = f"{trade} contractor {city_name} {state_or_country} email contact"
            logger.info(f"Searching: '{query}' (Progress: {len(leads)}/{args.target})")
            candidate_urls = search_ddg(query, max_links=12)

            fresh_urls = []
            for u in candidate_urls:
                dom = urllib.parse.urlparse(u).netloc.lower().replace("www.", "")
                if dom and dom not in seen_domains:
                    seen_domains.add(dom)
                    fresh_urls.append(u)

            if not fresh_urls:
                time.sleep(0.8)
                continue

            with ThreadPoolExecutor(max_workers=min(args.workers, len(fresh_urls))) as pool:
                futures = {pool.submit(crawl_site_for_email, u): u for u in fresh_urls}
                for fut in as_completed(futures):
                    orig_url = futures[fut]
                    try:
                        em, comp_name = fut.result()
                        if em and is_valid_email(em) and em not in seen_emails:
                            seen_emails.add(em)
                            loc_str = f"{city_name}, {state_or_country}"
                            copy = build_hormozi_copy(comp_name, trade, city_name)

                            lead_record = {
                                "company_name": comp_name,
                                "trade": trade,
                                "city": loc_str,
                                "email": em,
                                "phone": "",
                                "website": orig_url,
                                **copy
                            }
                            leads.append(lead_record)
                            logger.info(f" [+] Found lead ({len(leads)}/{args.target}): {comp_name} | {em} | {trade} ({city_name})")

                            if len(leads) % 5 == 0:
                                with open(json_path, "w", encoding="utf-8") as f:
                                    json.dump(leads, f, indent=2, ensure_ascii=False)
                                fieldnames = list(leads[0].keys())
                                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                                    writer.writeheader()
                                    writer.writerows(leads)
                    except Exception:
                        pass

            if leads:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(leads, f, indent=2, ensure_ascii=False)
                fieldnames = list(leads[0].keys())
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(leads)

            time.sleep(1.0)

    logger.info(f"Scraping complete! Total leads in queue: {len(leads)}")


if __name__ == "__main__":
    main()
