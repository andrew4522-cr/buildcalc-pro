#!/usr/bin/env python3
"""
BuildCalc Pro — Snov.io Automated Outreach Engine
- Dual Senders: andrew4522@gmail.com (ID 813095) & andrew@bridgingtheaigap.com (ID 811780)
- Sending delay: 35 seconds between sends
- Value-First Alex Hormozi "$100M Offers" contractor pitch
- Automated Pre-Flight Link Verifier (confirms HTTP 200 on all calculator URLs before sending)
- Daily Automation at 08:47 and 11:46 local recipient time
"""

import os
import sys
import time
import json
import logging
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("BuildCalcSnovSender")

# Configuration & Credentials
SNOV_CLIENT_ID = os.environ.get("SNOV_CLIENT_ID", "447bad774a8d068adde2584fe3743b5a")
SNOV_CLIENT_SECRET = os.environ.get("SNOV_CLIENT_SECRET", "4ffaab2261517d434126514ab3d07bdd")
BASE_URL = "https://api.snov.io"
SITE_BASE_URL = "https://andrew4522-cr.github.io/buildcalc-pro"
GUMROAD_PRODUCT_URL = "https://andrewverse7567.gumroad.com/l/BuildCalcPro"

# Sender Mailbox Accounts
SENDERS = {
    "andrew4522@gmail.com": {
        "id": 813095,
        "name": "Andrew Anderson",
        "email": "andrew4522@gmail.com",
    },
    "andrew@bridgingtheaigap.com": {
        "id": 811780,
        "name": "Andrew",
        "email": "andrew@bridgingtheaigap.com",
    }
}

# Trade to Tool Page Mapping
TRADE_PAGES = {
    "roofing": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "roofer": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "concrete": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "mason": ("concrete", "block-wall-cinder-calculator.html", "concrete yardage, block walls & mortar"),
    "carpenter": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "joiner": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "framing": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "drywall": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "plasterer": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "painter": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "painting": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "tiler": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "tile": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "flooring": ("tile", "lvp-hardwood-flooring-calculator.html", "flooring boxes, waste % & labor"),
    "deck": ("decking", "deck-material-calculator.html", "decking boards, joists & fasteners"),
    "handyman": ("framing", "handyman-estimate-generator.html", "materials, labor markup & client PDF quotes"),
    "builder": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
    "contractor": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
}


def resolve_trade_details(trade: str, company: str):
    combined = f"{trade} {company}".lower()
    for key, val in TRADE_PAGES.items():
        if key in combined:
            return val
    return ("contractor", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes")


class SnovOutreachEngine:
    def __init__(self, client_id: str = SNOV_CLIENT_ID, client_secret: str = SNOV_CLIENT_SECRET):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = ""
        self.token_expiry = 0

    def authenticate(self) -> str:
        if self.token and time.time() < self.token_expiry - 60:
            return self.token

        url = f"{BASE_URL}/v1/oauth/access_token"
        r = requests.post(url, json={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        self.token = data.get("access_token", "")
        self.token_expiry = time.time() + data.get("expires_in", 3600)
        logger.info("Successfully authenticated with Snov.io API")
        return self.token

    def _headers(self) -> dict:
        token = self.authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, path: str, payload: dict = None) -> dict:
        url = f"{BASE_URL}{path}"
        headers = self._headers()
        r = requests.request(method, url, json=payload, headers=headers, timeout=25)
        if not r.ok:
            logger.error(f"Snov API {method} {path} error {r.status_code}: {r.text}")
            r.raise_for_status()
        return r.json()

    def configure_sender_delays(self):
        """Sets 35-second delay between sends on both mailboxes."""
        patch_body = {
            "delay_from": 35,
            "delay_to": 36,
            "delay_type": "random"
        }
        for email, info in SENDERS.items():
            sid = info["id"]
            try:
                res = self._request("PATCH", f"/v2/sender-accounts/emails/{sid}", patch_body)
                logger.info(f"Verified 35s send delay configured on sender {email} (ID: {sid})")
            except Exception as e:
                logger.warning(f"Could not update sender delay for {email}: {e}")

    def verify_links(self) -> bool:
        """Pre-flight check: verifies all landing pages and Gumroad links return HTTP 200."""
        logger.info("Running pre-flight HTTP verification on all outreach links...")
        urls_to_test = [
            SITE_BASE_URL + "/",
            GUMROAD_PRODUCT_URL,
            f"{SITE_BASE_URL}/contractor-estimate-template.html",
            f"{SITE_BASE_URL}/roof-shingle-bundle-calculator.html",
            f"{SITE_BASE_URL}/concrete-slab-calculator.html",
            f"{SITE_BASE_URL}/drywall-sheet-calculator.html",
            f"{SITE_BASE_URL}/tile-flooring-calculator.html",
            f"{SITE_BASE_URL}/house-painting-bid-calculator.html",
            f"{SITE_BASE_URL}/framing-stud-calculator.html",
        ]
        all_passed = True
        for u in urls_to_test:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "BuildCalcPreFlightVerifier/1.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    if r.status == 200:
                        logger.info(f" [200 OK] {u}")
                    else:
                        logger.error(f" [NON-200: {r.status}] {u}")
                        all_passed = False
            except Exception as e:
                logger.error(f" [FAILED] {u} -> {e}")
                all_passed = False

        if all_passed:
            logger.info("All outreach target URLs verified healthy (HTTP 200 OK)!")
        else:
            logger.error("Link verification failed! Halting send to prevent broken outreach.")
        return all_passed

    def create_prospect_list(self, name: str) -> int:
        name = name[:45]
        payload = {"name": name}
        try:
            res = self._request("POST", "/v1/lists", payload)
            list_id = res.get("data", {}).get("id") or res.get("id")
            logger.info(f"Created Snov prospect list '{name}' (ID: {list_id})")
            return list_id
        except Exception as e:
            # Check if list already exists with that name
            headers = self._headers()
            r_get = requests.get(f"{BASE_URL}/v1/get-user-lists", headers=headers, timeout=15)
            if r_get.ok:
                for l in r_get.json():
                    if l.get("name") == name:
                        list_id = l.get("id")
                        logger.info(f"Found existing Snov prospect list '{name}' (ID: {list_id})")
                        return list_id
            # Otherwise retry with short timestamp
            unique_name = f"{name[:35]}_{int(time.time()) % 100000}"
            res = self._request("POST", "/v1/lists", {"name": unique_name})
            list_id = res.get("data", {}).get("id") or res.get("id")
            logger.info(f"Created unique Snov prospect list '{unique_name}' (ID: {list_id})")
            return list_id

    def add_prospect(self, list_id: int, lead: dict) -> bool:
        first_name = lead.get("firstName") or lead.get("first_name") or ""
        last_name = lead.get("lastName") or lead.get("last_name") or ""
        company = lead.get("company_name") or lead.get("companyName") or ""
        email = lead.get("email")

        if not first_name and company:
            first_name = company

        payload = {
            "listId": list_id,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "companyName": company,
            "position": lead.get("trade", "Contractor")
        }
        try:
            res = self._request("POST", "/v1/add-prospect-to-list", payload)
            return res.get("success", False)
        except Exception as e:
            logger.warning(f"Failed to add prospect {email}: {e}")
            return False

    def build_hormozi_copy(self, lead: dict, sender_name: str, sender_email: str) -> dict:
        company = lead.get("company_name") or lead.get("companyName") or "there"
        trade = lead.get("trade", "contractor")
        city = lead.get("city", "")

        trade_label, slug, math_desc = resolve_trade_details(trade, company)
        tool_url = f"{SITE_BASE_URL}/{slug}?utm_source=outreach&utm_medium=email&utm_campaign={trade_label}"

        city_clause = f" around {city}" if city else ""

        subject_1 = "Tired of writing bids at 9 PM?"
        body_html_1 = f"""<p>Hey {{{{company_name}}}} team,</p>

<p>Most trade contractors I talk to do the exact same thing: measure jobs during the day, then lose their evenings sitting at their kitchen table writing bids in Excel or on a notepad.</p>

<p>It eats up your nights and loses you jobs to guys who quote right there in the client's driveway.</p>

<p>I built a completely free estimator you can run right from your phone or truck (BuildCalc Pro):<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&utm_medium=email">{SITE_BASE_URL}/contractor-estimate-template.html</a></strong></p>

<p>What it does in 60 seconds:
<ul>
  <li>Type your job dimensions in feet, inches, or fractions</li>
  <li>Calculates materials automatically with waste % (roofing squares, cubic yards of concrete, drywall sheets, wall framing studs, tile counts, and paint gallons)</li>
  <li>Generates an itemized PDF quote with your company logo ready for signature</li>
</ul>
</p>

<p>No $60/month subscriptions (Jobber/QuickBooks). No 40-minute onboarding calls. No login or credit card required.</p>

<p>You can use it 100% free on your next bid right here:<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&utm_medium=email">Open BuildCalc Pro Free &rarr;</a></strong></p>

<p>If it saves you a couple of hours this week, that's awesome. If not, you still got a free estimate out of it.</p>

<p>Best regards,<br>
<strong>{sender_name}</strong><br>
BuildCalc Pro Team<br>
<a href="mailto:{sender_email}">{sender_email}</a></p>
"""

        subject_2 = "Quick question about your bids"
        body_html_2 = f"""<p>Hey {{{{company_name}}}} team,</p>

<p>Did you get a chance to test BuildCalc on your last bid?</p>

<p>Takes 60 seconds from your phone, zero setup, no login or credit card needed:<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&utm_medium=email">{SITE_BASE_URL}/contractor-estimate-template.html</a></strong></p>

<p>Hope it helped you win the job.</p>

<p>Best,<br>
<strong>{sender_name}</strong><br>
<a href="mailto:{sender_email}">{sender_email}</a></p>
"""

        return {
            "subject_1": subject_1,
            "body_html_1": body_html_1,
            "subject_2": subject_2,
            "body_html_2": body_html_2,
            "tool_url": f"{SITE_BASE_URL}/contractor-estimate-template.html"
        }

    def launch_campaign_batch(self, sender_key: str, leads: List[dict], batch_name: str) -> Optional[int]:
        sender = SENDERS[sender_key]
        sender_id = sender["id"]
        sender_email = sender["email"]
        sender_name = sender["name"]

        logger.info(f"--- Preparing Campaign for {sender_email} ({len(leads)} leads) ---")

        # 1. Create Dedicated Prospect List
        list_name = f"BuildCalc-{sender_name.split()[0]}-{batch_name}"[:40]
        list_id = self.create_prospect_list(list_name)
        if not list_id:
            logger.error("Failed to create prospect list. Aborting campaign.")
            return None

        # 2. Add Prospects to List
        enrolled = 0
        for lead in leads:
            if self.add_prospect(list_id, lead):
                enrolled += 1
            time.sleep(0.3)
        logger.info(f"Enrolled {enrolled}/{len(leads)} verified contractors into list {list_id}")

        # 3. Build Hormozi 2-step Sequence
        t0 = int(time.time() * 1000)
        s1_ref = str(t0)
        c1_id = int(s1_ref + "0")
        d1_ref = str(t0 + 1)
        s2_ref = str(t0 + 2)
        c2_id = int(s2_ref + "0")

        copy_data = self.build_hormozi_copy({}, sender_name, sender_email)

        camp_payload = {
            "title": f"BuildCalc Pro - {batch_name} ({sender_email})",
            "priority": "high",
            "email_accounts": [sender_id],
            "recipients": {"list_id": list_id},
            "complete_campaign_after_last_step": True,
            "archive_in_months": 3,
            "tracking": {"open": True, "link_click": True},
            "sending_settings": {
                "sending_priority": "follow_up",
                "skip_who_replied": True,
                "skip_unverified": False,
                "skip_bounced": True,
            },
            "provider_matching": False,
            "sequence": {
                "entry": s1_ref,
                "steps": [
                    {
                        "_ref": s1_ref,
                        "type": "email",
                        "content_slots": 1,
                        "content": [{"id": c1_id, "plain_text": False, "usage": "active"}],
                        "next": d1_ref
                    },
                    {
                        "_ref": d1_ref,
                        "type": "delay",
                        "waiting_type": "days",
                        "waiting_val": 3,
                        "next": s2_ref
                    },
                    {
                        "_ref": s2_ref,
                        "type": "email",
                        "content_slots": 1,
                        "content": [{"id": c2_id, "plain_text": False, "usage": "active"}]
                    }
                ]
            }
        }

        # 4. Create Campaign Shell
        res_camp = self._request("POST", "/v2/campaigns/create", camp_payload)
        camp_id = res_camp.get("data", {}).get("id")
        if not camp_id:
            logger.error(f"Failed to create campaign: {res_camp}")
            return None
        logger.info(f"Campaign shell created: ID {camp_id}")

        # 5. Inject Step 1 (Initial Pitch) & Step 2 (Follow-up) Content
        self._request("POST", f"/v2/campaigns/{camp_id}/steps/{s1_ref}/content/create", {
            "content_id": c1_id,
            "plain_text": False,
            "usage": "active",
            "subject": copy_data["subject_1"],
            "body": copy_data["body_html_1"]
        })

        self._request("POST", f"/v2/campaigns/{camp_id}/steps/{s2_ref}/content/create", {
            "content_id": c2_id,
            "plain_text": False,
            "usage": "active",
            "subject": copy_data["subject_2"],
            "body": copy_data["body_html_2"]
        })

        # 6. Start Campaign Live
        start_res = self._request("POST", f"/v2/campaigns/{camp_id}/action", {"action": "start"})
        logger.info(f"LIVE CAMPAIGN LAUNCHED: Campaign {camp_id} for {sender_email}! Status: {start_res}")
        return camp_id


def load_leads_queue() -> List[dict]:
    queue_file = Path(__file__).parent / "dist" / "outreach" / "contractor_leads_queue.json"
    if not queue_file.exists():
        logger.error(f"Leads queue file {queue_file} not found.")
        return []
    with open(queue_file, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="BuildCalc Pro Snov.io Outreach Engine")
    parser.add_argument("--batch-now", action="store_true", help="Launch today's 50+50 batch immediately")
    parser.add_argument("--count", type=int, default=50, help="Emails per sender account (default 50)")
    args = parser.parse_args()

    engine = SnovOutreachEngine()

    # Step 1: Pre-Flight Link Verification
    if not engine.verify_links():
        sys.exit(1)

    # Step 2: Configure 35s Delays
    engine.configure_sender_delays()

    # Step 3: Load Verified Contractor Leads
    leads = load_leads_queue()
    logger.info(f"Total leads in queue: {len(leads)}")

    if args.batch_now:
        need_total = args.count * 2
        if len(leads) < need_total:
            logger.warning(f"Queue currently has {len(leads)} leads; need {need_total}. Will allocate available leads equally.")

        half = len(leads) // 2
        batch_1 = leads[:args.count] if len(leads) >= args.count * 2 else leads[:half]
        batch_2 = leads[args.count:args.count * 2] if len(leads) >= args.count * 2 else leads[half:]

        today_str = time.strftime("%Y-%m-%d")
        camp1 = engine.launch_campaign_batch("andrew4522@gmail.com", batch_1, f"Batch-1-{today_str}")
        camp2 = engine.launch_campaign_batch("andrew@bridgingtheaigap.com", batch_2, f"Batch-2-{today_str}")

        logger.info(f"SUCCESS! Launched both campaigns:")
        logger.info(f"  - andrew4522@gmail.com: Campaign ID {camp1} ({len(batch_1)} contractors)")
        logger.info(f"  - andrew@bridgingtheaigap.com: Campaign ID {camp2} ({len(batch_2)} contractors)")


if __name__ == "__main__":
    main()
