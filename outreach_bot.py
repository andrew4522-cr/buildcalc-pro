#!/usr/bin/env python3
"""
BuildCalc Pro — Automated Contractor Lead Scraper & Alex Hormozi Outreach Engine
100% Free & Open-Source Connectors:
  - Lead Discovery: OpenStreetMap Overpass API (craft/construction/trade nodes & ways)
  - Email Extraction: Direct website HTML / mailto crawler
  - Outreach Copy: Alex Hormozi "$100M Offers / $100M Leads" Value-First Templates
  - Delivery: Built-in Python smtplib (Gmail / Brevo / any free SMTP) with CSV queue
"""

import argparse
import csv
import json
import os
import re
import smtplib
import ssl
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

SITE_BASE_URL = os.environ.get("BUILDCALC_URL", "https://andrew4522-cr.github.io/buildcalc-pro")

TRADE_LANDING_MAP = {
    "roofer": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "roofing": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "carpenter": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "framing": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "painter": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "tiler": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "flooring": ("tile", "lvp-hardwood-flooring-calculator.html", "flooring boxes, waste % & labor"),
    "plasterer": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "drywall": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "concrete": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "mason": ("concrete", "block-wall-cinder-calculator.html", "concrete yardage, block walls & mortar"),
    "deck": ("decking", "deck-material-calculator.html", "decking boards, joists & fasteners"),
    "handyman": ("framing", "handyman-estimate-generator.html", "materials, labor markup & client PDF quotes"),
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,10}")
IGNORED_EMAIL_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "domain.com", "email.com",
    "wordpress.org", "w3.org", "schema.org", "googleapis.com", "cloudflare.com"
}


def resolve_trade_info(raw_trade: str, company_name: str) -> tuple[str, str, str]:
    combined = f"{raw_trade} {company_name}".lower()
    for key, val in TRADE_LANDING_MAP.items():
        if key in combined:
            return val
    return ("concrete", "contractor-estimate-template.html", "concrete, framing, roofing & drywall materials")


def build_hormozi_emails(company_name: str, raw_trade: str, city: str) -> dict:
    trade_label, slug, math_desc = resolve_trade_info(raw_trade, company_name)
    tool_url = f"{SITE_BASE_URL}/{slug}?utm_source=outreach&utm_medium=email&utm_campaign={trade_label}"
    clean_name = company_name.strip() if company_name else "there"

    # Variant 1: Hormozi "9 PM Kitchen Table" Angle
    subj_1 = f"Tired of writing {trade_label} bids at 9 PM?"
    body_1 = f"""Hey {clean_name} team,

Most contractors I talk to{f' around {city}' if city else ''} do the same thing: measure the job during the day, then spend 2 hours at their kitchen table at night writing estimates in Excel or on a notepad.

It kills your evenings and loses you jobs to guys who quote on the spot.

I built a dead-simple estimator for your phone and laptop (BuildCalc):
{tool_url}

You plug in the job dimensions (feet, inches, fractions), it calculates your {math_desc} automatically with waste %, and turns it into a branded PDF quote with your logo in 60 seconds.

No $60/month subscriptions (Jobber/QuickBooks). No 40-minute onboarding setup. No login or credit card required.

You can use it 100% free on your next bid here:
{tool_url}

If you like it, cool. If not, you still got a free estimate out of it.

Best,
BuildCalc Team"""

    # Variant 2: Hormozi "Driveway Close / Grand Slam" Angle
    subj_2 = f"quick question about {clean_name}'s bidding process"
    body_2 = f"""Hey {clean_name} team,

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
BuildCalc Team"""

    return {
        "trade_category": trade_label,
        "landing_url": tool_url,
        "subject_v1": subj_1,
        "body_v1": body_1,
        "subject_v2": subj_2,
        "body_v2": body_2,
    }


def extract_email_from_website(url: str, timeout: int = 8) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read(250_000).decode("utf-8", errors="ignore")
        for match in EMAIL_REGEX.findall(html):
            email = match.strip().lower().rstrip(".")
            domain = email.split("@")[-1]
            if domain not in IGNORED_EMAIL_DOMAINS and not email.endswith((".png", ".jpg", ".webp", ".svg", ".js", ".css")):
                return email
    except Exception:
        pass
    return ""


METRO_BBOXES = [
    ("Dallas-Fort Worth, TX", 32.60, -97.50, 33.15, -96.50),
    ("Houston, TX", 29.50, -95.80, 30.10, -95.10),
    ("Austin, TX", 30.15, -97.90, 30.50, -97.60),
    ("Phoenix, AZ", 33.30, -112.30, 33.75, -111.75),
    ("Atlanta, GA", 33.65, -84.55, 33.90, -84.25),
    ("Denver, CO", 39.60, -105.10, 39.85, -104.85),
    ("Charlotte, NC", 35.10, -80.95, 35.35, -80.70),
    ("Tampa-St Pete, FL", 27.85, -82.65, 28.10, -82.35),
    ("Orlando, FL", 28.40, -81.50, 28.65, -81.25),
    ("Nashville, TN", 36.05, -86.90, 36.25, -86.65),
    ("Chicago, IL", 41.75, -87.80, 42.05, -87.55),
    ("Columbus, OH", 39.85, -83.10, 40.10, -82.85),
    ("Indianapolis, IN", 39.65, -86.30, 39.90, -86.00),
    ("Las Vegas, NV", 36.05, -115.30, 36.25, -115.05),
    ("Seattle, WA", 47.50, -122.45, 47.75, -122.25),
    ("San Diego, CA", 32.65, -117.25, 32.90, -117.00),
    ("Los Angeles, CA", 33.90, -118.45, 34.20, -118.15),
    ("San Antonio, TX", 29.30, -98.65, 29.60, -98.35),
    ("Miami, FL", 25.70, -80.35, 25.90, -80.10),
    ("London, UK", 51.35, -0.35, 51.65, 0.10),
    ("Manchester, UK", 53.40, -2.35, 53.55, -2.15),
    ("Birmingham, UK", 52.40, -2.00, 52.55, -1.80),
    ("Toronto, Canada", 43.60, -79.55, 43.80, -79.25),
    ("Vancouver, Canada", 49.20, -123.25, 49.35, -123.00),
    ("Dublin, Ireland", 53.25, -6.40, 53.45, -6.15),
    ("Sydney, Australia", -33.95, 151.05, -33.75, 151.30),
    ("Melbourne, Australia", -37.90, 144.85, -37.70, 145.10),
    ("Brisbane, Australia", -27.55, 152.90, -27.35, 153.15),
    ("Auckland, NZ", -36.95, 174.65, -36.75, 174.90),
    ("Philadelphia, PA", 39.85, -75.30, 40.10, -75.05),
    ("Boston, MA", 42.25, -71.20, 42.45, -70.95),
    ("San Francisco, CA", 37.70, -122.55, 37.85, -122.35),
    ("San Jose, CA", 37.25, -122.00, 37.45, -121.75),
    ("Portland, OR", 45.45, -122.80, 45.65, -122.55),
    ("Minneapolis, MN", 44.90, -93.35, 45.05, -93.20),
    ("Detroit, MI", 42.30, -83.25, 42.45, -82.95),
    ("St. Louis, MO", 38.55, -90.35, 38.75, -90.15),
    ("Pittsburgh, PA", 40.35, -80.10, 40.55, -79.85),
    ("Salt Lake City, UT", 40.65, -112.05, 40.85, -111.80),
    ("Kansas City, MO", 38.95, -94.75, 39.20, -94.45),
    ("Sacramento, CA", 38.45, -121.60, 38.65, -121.35),
    ("Raleigh, NC", 35.70, -78.75, 35.90, -78.50),
    ("Glasgow, UK", 55.80, -4.40, 55.95, -4.15),
    ("Edinburgh, UK", 55.88, -3.35, 55.98, -3.10),
    ("Leeds, UK", 53.75, -1.65, 53.85, -1.45),
    ("Bristol, UK", 51.40, -2.70, 51.52, -2.50),
    ("Calgary, Canada", 50.95, -114.20, 51.15, -113.95),
    ("Montreal, Canada", 45.45, -73.75, 45.65, -73.50),
]


def extract_emails_from_sites_concurrent(targets: list[tuple[str, str, str, str, str, str]]) -> list[dict]:
    """
    Crawls contractor websites concurrently using a worker pool to extract direct email addresses.
    targets is a list of tuples: (name, trade, city, phone, website, direct_email)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    leads = []
    need_crawl = []

    for name, trade, city, phone, website, direct_email in targets:
        if direct_email:
            copy_data = build_hormozi_emails(name, trade, city)
            leads.append({
                "company_name": name,
                "trade": trade,
                "city": city,
                "email": direct_email,
                "phone": phone,
                "website": website,
                **copy_data,
            })
        elif website:
            need_crawl.append((name, trade, city, phone, website))

    if need_crawl:
        def crawl_worker(item):
            c_name, c_trade, c_city, c_phone, c_site = item
            found_email = extract_email_from_website(c_site)
            if not found_email and not c_site.endswith("/contact"):
                # Try contact page as fallback
                contact_url = c_site.rstrip("/") + "/contact"
                found_email = extract_email_from_website(contact_url)
            if found_email:
                c_copy = build_hormozi_emails(c_name, c_trade, c_city)
                return {
                    "company_name": c_name,
                    "trade": c_trade,
                    "city": c_city,
                    "email": found_email,
                    "phone": c_phone,
                    "website": c_site,
                    **c_copy,
                }
            return None

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(crawl_worker, it) for it in need_crawl]
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    leads.append(res)

    return leads


def scrape_osm_contractors(target_email_count: int = 1000, limit: int = None) -> list[dict]:
    """
    Iterates through major metros, querying Overpass and extracting verified contractor emails
    until the target email count (e.g. 1,000) is reached.
    """
    if limit is not None:
        target_email_count = limit

    allowed_trades = {
        "roofer", "carpenter", "painter", "tiler", "plasterer", "builder",
        "floorer", "stonemason", "handyman", "plumber", "electrician",
        "hvac", "glazier", "insulation", "scaffolder", "parquet_layer",
        "window_construction", "construction", "contractor", "joiner",
        "metal_construction", "flooring", "roofing", "painting", "mason",
        "drywall", "decking", "bricklayer"
    }

    endpoints = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]

    out_dir = Path(__file__).parent / "dist" / "outreach"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_file = out_dir / "contractor_leads_queue.csv"
    json_file = out_dir / "contractor_leads_queue.json"

    all_verified_leads = []
    seen_emails = set()
    seen_names = set()

    # Load existing if available to avoid duplicates
    if csv_file.exists():
        try:
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    e = (r.get("email") or "").lower().strip()
                    if e and e not in seen_emails:
                        seen_emails.add(e)
                        seen_names.add(r.get("company_name", "").lower().strip())
                        all_verified_leads.append(r)
            print(f"[INFO] Loaded {len(all_verified_leads)} existing verified leads from disk.")
        except Exception:
            pass

    print(f"[INFO] Target: Collecting {target_email_count} verified contractor email leads...")

    for metro_name, min_lat, min_lon, max_lat, max_lon in METRO_BBOXES:
        if len(all_verified_leads) >= target_email_count:
            break

        print(f"[INFO] Querying {metro_name} contractors from Overpass...")
        query = f"""[out:json][timeout:15];
(
  node["craft"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["office"="construction"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out body 400;"""

        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        elements = []

        for ep in endpoints:
            req = urllib.request.Request(
                ep,
                data=data,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8", errors="replace"))
                    elements = payload.get("elements", [])
                    if elements:
                        break
            except Exception:
                time.sleep(1.0)

        targets = []
        for el in elements:
            tags = el.get("tags", {}) or {}
            name = tags.get("name", "").strip()
            if not name or name.lower() in seen_names:
                continue

            trade = (tags.get("craft") or tags.get("office") or "contractor").lower()
            if trade not in allowed_trades:
                continue

            seen_names.add(name.lower())
            city = tags.get("addr:city") or metro_name.split(",")[0]
            phone = tags.get("phone") or tags.get("contact:phone") or ""
            website = tags.get("website") or tags.get("contact:website") or ""
            direct_email = tags.get("email") or tags.get("contact:email") or ""

            if direct_email or website:
                targets.append((name, trade, city, phone, website, direct_email))

        if targets:
            print(f" -> Found {len(targets)} candidates with websites/emails in {metro_name}. Extracting emails...")
            extracted = extract_emails_from_sites_concurrent(targets)
            new_added = 0
            for lead in extracted:
                e = lead["email"].lower()
                if e and e not in seen_emails:
                    seen_emails.add(e)
                    all_verified_leads.append(lead)
                    new_added += 1

            print(f" -> Added {new_added} new verified emails. Total: {len(all_verified_leads)} / {target_email_count}")

            # Save incremental progress
            if all_verified_leads:
                json_file.write_text(json.dumps(all_verified_leads, indent=2, ensure_ascii=False), encoding="utf-8")
                fieldnames = list(all_verified_leads[0].keys())
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_verified_leads)

        time.sleep(1.0)

    return all_verified_leads[:target_email_count]


def send_smtp_batch(leads: list[dict], max_send: int = 25):
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        print("[INFO] Dry-run mode: Set SMTP_USER and SMTP_PASS environment variables to send live emails.")
        return

    emailable = [l for l in leads if l.get("email")][:max_send]
    print(f"Sending {len(emailable)} Hormozi outreach emails via {smtp_host}...")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
        server.login(smtp_user, smtp_pass)
        for lead in emailable:
            msg = EmailMessage()
            msg["Subject"] = lead["subject_v1"]
            msg["From"] = smtp_user
            msg["To"] = lead["email"]
            msg.set_content(lead["body_v1"])
            server.send_message(msg)
            print(f" -> Sent to {lead['company_name']} <{lead['email']}>")
            time.sleep(4.0)


def main():
    print("BuildCalc Pro outreach permanently KILLED (2026-10-28). Exiting immediately.")
    return
    parser = argparse.ArgumentParser(description="BuildCalc Pro Automated Contractor Scraper & Hormozi Outreach Bot")
    parser.add_argument("--limit", type=int, default=35, help="Max leads to scrape per run")
    parser.add_argument("--send", action="store_true", help="Send outreach emails via SMTP_USER / SMTP_PASS")
    args = parser.parse_args()

    out_dir = Path(__file__).parent / "dist" / "outreach"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Scraping live US trade contractors from OpenStreetMap Overpass API...")
    leads = scrape_osm_contractors(limit=args.limit)
    print(f"Scraped & enriched {len(leads)} real contractor leads with tailored Hormozi outreach copy.")

    json_file = out_dir / "contractor_leads_queue.json"
    csv_file = out_dir / "contractor_leads_queue.csv"

    json_file.write_text(json.dumps(leads, indent=2, ensure_ascii=False), encoding="utf-8")

    if leads:
        fieldnames = list(leads[0].keys())
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)

    print(f"Saved outreach queue to:\n  - {csv_file}\n  - {json_file}")

    if args.send:
        send_smtp_batch(leads)


if __name__ == "__main__":
    main()
