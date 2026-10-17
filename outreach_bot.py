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


def scrape_osm_contractors(limit: int = 40) -> list[dict]:
    """
    Queries OpenStreetMap's free Overpass API using fast indexed exact-tag lookups
    specifically for construction, roofing, carpentry, painting, plumbing, electrical,
    and building trade contractors.
    """
    allowed_trades = {
        "roofer", "carpenter", "painter", "tiler", "plasterer", "builder",
        "floorer", "stonemason", "handyman", "plumber", "electrician",
        "hvac", "glazier", "insulation", "scaffolder", "parquet_layer",
        "window_construction", "construction", "contractor"
    }

    overpass_query = """[out:json][timeout:15];
(
  node["craft"](32.60,-97.50,33.15,-96.50);
  node["office"="construction"](32.60,-97.50,33.15,-96.50);
  node["craft"](29.50,-95.80,30.10,-95.10);
  node["office"="construction"](29.50,-95.80,30.10,-95.10);
  node["craft"](33.30,-112.30,33.75,-111.75);
  node["office"="construction"](33.30,-112.30,33.75,-111.75);
  node["craft"](51.35,-0.40,51.65,0.15);
  node["office"="construction"](51.35,-0.40,51.65,0.15);
);
out body 500;"""

    endpoints = [
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]
    data = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")

    elements = []
    for url in endpoints:
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": "BuildCalcDirectoryBot/1.0",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
                elements = payload.get("elements", [])
                if elements:
                    break
        except Exception as e:
            print(f"[WARN] Overpass endpoint {url} notice: {e}")

    leads = []
    seen_names = set()

    for el in elements:
        tags = el.get("tags", {}) or {}
        name = tags.get("name", "").strip()
        if not name or name.lower() in seen_names:
            continue

        trade = (tags.get("craft") or tags.get("office") or "contractor").lower()
        if trade not in allowed_trades:
            continue
        seen_names.add(name.lower())
        city = tags.get("addr:city") or tags.get("addr:state") or ""
        phone = tags.get("phone") or tags.get("contact:phone") or ""
        website = tags.get("website") or tags.get("contact:website") or ""
        email = tags.get("email") or tags.get("contact:email") or ""

        if not email and website and len(leads) < 15:
            email = extract_email_from_website(website)

        if not (email or website or phone):
            continue

        copy_data = build_hormozi_emails(name, trade, city)
        leads.append({
            "company_name": name,
            "trade": trade,
            "city": city,
            "email": email,
            "phone": phone,
            "website": website,
            **copy_data,
        })
        if len(leads) >= limit:
            break

    return leads


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
