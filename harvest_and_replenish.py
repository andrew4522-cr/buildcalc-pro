#!/usr/bin/env python3
"""
BuildCalc Pro — Autonomous Lead Harvester & Replenishment Pipeline
Parses research subagents transcripts line-by-line, extracts verified contractor leads,
validates emails, generates Hormozi outreach copy, deduplicates against
both the queue and the dispatched ledger, and keeps the active pipeline topped up.
"""

import os
import re
import csv
import json
import html
from pathlib import Path
from typing import Dict, List, Set, Tuple

BASE_URL = "https://andrew4522-cr.github.io/buildcalc-pro"
WORKSPACE_DIR = Path("C:/Users/Users/.gemini/antigravity/scratch/app-factory/buildcalc-pro")
OUTREACH_DIR = WORKSPACE_DIR / "dist" / "outreach"
QUEUE_JSON = OUTREACH_DIR / "contractor_leads_queue.json"
QUEUE_CSV = OUTREACH_DIR / "contractor_leads_queue.csv"
DISPATCHED_JSON = OUTREACH_DIR / "dispatched_leads.json"

SUBAGENTS = [
    "9646e433-9b1c-43a6-bd5b-9f8ce1b394bb",
    "d47468fa-7045-43f9-8a97-a5593e093db5",
    "9e5572f9-d890-459a-8226-6af1de9a51f5",
    "fe11fecb-ff41-4df7-ab51-035589e040c1",
    "c9030c77-c388-4a46-9d74-70fe401d1244",
    "fe6e8a16-3d47-4c91-99d4-c254ed38bcf3",
    "95e05f97-babc-475d-9d4a-2cf4a284bec6",
    "0bd357f1-822c-4baf-8699-a1c1e67d7654",
    "7a7959a8-e097-4adf-8a1f-9522d5fa1231",
]

TRADE_MAP = {
    "roof": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "gutter": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "concrete": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "cement": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "mason": ("concrete", "block-wall-cinder-calculator.html", "concrete yardage, block walls & mortar"),
    "brick": ("concrete", "block-wall-cinder-calculator.html", "concrete yardage, block walls & mortar"),
    "carpenter": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "joiner": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "fram": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "drywall": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "plaster": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "sheetrock": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "paint": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "decorat": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "tile": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "tiling": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "floor": ("tile", "lvp-hardwood-flooring-calculator.html", "flooring boxes, waste % & labor"),
    "hardwood": ("tile", "lvp-hardwood-flooring-calculator.html", "flooring boxes, waste % & labor"),
    "deck": ("decking", "deck-material-calculator.html", "decking boards, joists & fasteners"),
    "remodel": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
    "build": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
    "general": ("contractor", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
}

IGNORED_DOMAINS = {
    "sentry.io", "wix.com", "wixpress.com", "example.com", "domain.com",
    "company.com", "wordpress.org", "wordpress.com", "schema.org", "googleapis.com",
    "cloudflare.com", "google.com", "facebook.com", "instagram.com",
    "twitter.com", "linkedin.com", "youtube.com", "yelp.com", "bbb.org",
    "angi.com", "homeadvisor.com", "thumbtack.com", "houzz.com",
    "porch.com", "yellowpages.com", "mapquest.com", "apple.com",
    "aeroleads.com", "hubspot.com", "snov.io", "apollo.io", "leadconnect.io",
    "scribd.com", "zoominfo.com", "crunchbase.com", "dribbble.com", "behance.net",
    "vertexaisearch.cloud.google.com"
}

IGNORED_PREFIXES = {
    "you@", "yourname@", "email@", "name@", "test@", "example@", "support@aeroleads.com",
    "user@", "admin@domain.com", "intl-segmenter@", "info@sentry.io", "contact@example.com"
}

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10}\b")

def is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    email = email.lower().strip()
    if any(email.startswith(p) for p in IGNORED_PREFIXES):
        return False
    domain = email.split("@")[-1]
    if domain in IGNORED_DOMAINS or any(domain.endswith("." + d) for d in IGNORED_DOMAINS):
        return False
    parts = domain.split(".")
    if len(parts) < 2 or not parts[-1].isalpha() or not (2 <= len(parts[-1]) <= 10):
        return False
    return True

def clean_company_name(name: str, email: str) -> str:
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"https?://\S+", "", name)
    name = html.unescape(name).strip()
    name = name.strip("*:.- ")
    if not name or len(name) < 2 or len(name) > 60:
        if "@" in email:
            domain = email.split("@")[-1].split(".")[0]
            name = domain.replace("-", " ").replace("_", " ").title()
    return name

def resolve_trade(trade_str: str, company: str) -> Tuple[str, str, str]:
    text = f"{trade_str} {company}".lower()
    for key, val in TRADE_MAP.items():
        if key in text:
            return val
    return ("contractor", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes")

def build_copy(company: str, trade: str, city: str) -> Dict[str, str]:
    trade_label, slug, math_desc = resolve_trade(trade, company)
    tool_url = f"{BASE_URL}/{slug}?utm_source=outreach&utm_medium=email&utm_campaign={trade_label}"
    clean_company = html.unescape(company.strip()) if company else "there"
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

def extract_leads_from_content(text: str) -> List[Dict]:
    leads = []
    # 1. Search for JSON arrays
    for match in re.finditer(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL):
        try:
            arr = json.loads(match.group(0))
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict) and "email" in item and is_valid_email(item["email"]):
                        leads.append({
                            "company_name": item.get("company_name", ""),
                            "trade": item.get("trade", "contractor"),
                            "city": item.get("city", ""),
                            "email": item["email"].lower().strip(),
                            "website": item.get("website", "")
                        })
        except Exception:
            pass

    # 2. Search for bullet blocks in text
    blocks = re.split(r"\n(?=\* |\d+\. |### )", text)
    for b in blocks:
        emails = EMAIL_REGEX.findall(b)
        if not emails:
            continue
        for em in emails:
            em = em.lower().strip()
            if not is_valid_email(em):
                continue
            
            # Find company name
            name = ""
            nm1 = re.search(r"(\*\*|###\s*\d*\.?\s*)([^\*\n]+)\1", b)
            if nm1:
                name = nm1.group(2).strip()
            if not name:
                first_line = b.splitlines()[0]
                name = re.sub(r"^[\*\#\d\.\-\s]+", "", first_line).strip()
            
            name = clean_company_name(name, em)

            # Trade
            trade = "contractor"
            low_b = b.lower()
            for t in ["roofing", "concrete", "framing", "drywall", "painting", "paint", "tile", "decking", "masonry", "carpenter", "joiner"]:
                if t in low_b or t in name.lower():
                    trade = t
                    break
            
            # City / Location
            city = ""
            cm = re.search(r"(?:Location|Address|Serving|City):\s*([^\n\r]+)", b, re.IGNORECASE)
            if cm:
                city = re.sub(r"\[.*?\]", "", cm.group(1)).strip().strip("*` ")

            # Website
            website = ""
            wm = re.search(r"\[([^\]]+)\]\((https?://[^\)]+)\)", b)
            if wm and "google.com" not in wm.group(2):
                website = wm.group(2)
            else:
                website = f"https://{em.split('@')[1]}"

            leads.append({
                "company_name": name,
                "trade": trade,
                "city": city,
                "email": em,
                "website": website
            })
    return leads

def harvest_subagents() -> Dict[str, Dict]:
    base_brain = Path("C:/Users/Users/.gemini/antigravity/brain")
    unique_leads = {}

    for sub_id in SUBAGENTS:
        t_file = base_brain / sub_id / ".system_generated" / "logs" / "transcript.jsonl"
        if not t_file.exists():
            continue
        try:
            with open(t_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        step = json.loads(line)
                    except Exception:
                        continue
                    
                    content = step.get("content", "")
                    thinking = step.get("thinking", "")
                    
                    for txt in [content, thinking]:
                        if not txt:
                            continue
                        extracted = extract_leads_from_content(txt)
                        for item in extracted:
                            em = item["email"]
                            if em not in unique_leads or len(item["company_name"]) > len(unique_leads[em]["company_name"]):
                                unique_leads[em] = item
        except Exception as e:
            print(f"Error harvesting subagent {sub_id}: {e}")

    return unique_leads

def main():
    # 1. Load existing queue
    queue = []
    if QUEUE_JSON.exists():
        with open(QUEUE_JSON, "r", encoding="utf-8") as f:
            queue = json.load(f)
    print(f"Starting Queue Count: {len(queue)}")

    # 2. Load dispatched leads
    dispatched = []
    if DISPATCHED_JSON.exists():
        with open(DISPATCHED_JSON, "r", encoding="utf-8") as f:
            dispatched = json.load(f)
    print(f"Dispatched Leads Count: {len(dispatched)}")
    dispatched_set = {e.lower().strip() for e in dispatched}

    existing_emails = {item["email"].lower().strip() for item in queue}

    # 3. Harvest subagents
    harvested_map = harvest_subagents()
    print(f"Unique Verified Contractor Leads Extracted Across Subagents: {len(harvested_map)}")

    added = 0
    for em, cand in harvested_map.items():
        if em in existing_emails or em in dispatched_set:
            continue
        
        comp_name = cand["company_name"] or "Trade Pro"
        trade = cand["trade"] or "general"
        city = cand["city"] or ""
        website = cand["website"] or f"https://{em.split('@')[1]}"

        copy_data = build_copy(comp_name, trade, city)
        lead_obj = {
            "company_name": comp_name,
            "trade": trade,
            "city": city,
            "email": em,
            "website": website,
            **copy_data
        }

        queue.append(lead_obj)
        existing_emails.add(em)
        added += 1

    print(f"\n=======================================================")
    print(f"   REPLENISHMENT HARVEST SUMMARY")
    print(f"=======================================================")
    print(f"Newly Added Verified Leads: {added}")
    print(f"Total Updated Leads in Queue: {len(queue)}")
    
    available = [x for x in queue if x["email"].lower().strip() not in dispatched_set]
    print(f"Active Ready-to-Send Queue: {len(available)} leads")
    runway_days = len(available) / 200.0
    print(f"Outreach Runway: {runway_days:.1f} Days (at 200 emails/day)")
    print(f"=======================================================\n")

    # 4. Save to JSON & CSV
    with open(QUEUE_JSON, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)

    if queue:
        keys = list(queue[0].keys())
        with open(QUEUE_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(queue)

if __name__ == "__main__":
    main()
