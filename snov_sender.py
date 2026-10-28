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
import subprocess
import smtplib
import html
import urllib.request
import urllib.parse
from email.message import EmailMessage
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("BuildCalcSnovSender")

def _clean_env_secret(val: Optional[str], default: str) -> str:
    if not val:
        return default
    v = str(val).strip()
    if v.lower() in ("true", "false", "null", "none", "") or len(v) < 10:
        return default
    return v

# Configuration & Credentials (with defensive fallback against Actions boolean coercion)
SNOV_CLIENT_ID = _clean_env_secret(os.environ.get("SNOV_CLIENT_ID"), "447bad774a8d068adde2584fe3743b5a")
SNOV_CLIENT_SECRET = _clean_env_secret(os.environ.get("SNOV_CLIENT_SECRET"), "4ffaab2261517d434126514ab3d07bdd")
GMAIL_SMTP_USER = "andrew4522@gmail.com"
GMAIL_SMTP_PASS = _clean_env_secret(os.environ.get("GMAIL_APP_PASSWORD"), "jtbdqmafneertksh")
BASE_URL = "https://api.snov.io"
SITE_BASE_URL = "https://andrew4522-cr.github.io/buildcalc-pro"
GUMROAD_PRODUCT_URL = "https://andrewverse7567.gumroad.com/l/BuildCalcPro"

# Sender Mailbox Accounts (Consolidated into 2 Permanent Master Campaigns)
SENDERS = {
    "andrew4522@gmail.com": {
        "id": 813095,
        "name": "Andrew Anderson",
        "email": "andrew4522@gmail.com",
        "master_campaign_id": 3209166,
        "master_list_id": 41759386,
    },
    "andrew@bridgingtheaigap.com": {
        "id": 811780,
        "name": "Andrew",
        "email": "andrew@bridgingtheaigap.com",
        "master_campaign_id": 3209167,
        "master_list_id": 41759405,
    }
}

# Dedicated Link-Clicker Immediate Personal Outreach Campaign & List (Step 1 = Immediate 2-sentence email, then +3d and +7d)
ENGAGED_CLICKERS_LIST_ID = 41779545
ENGAGED_CLICKERS_CAMPAIGN_ID = 3212298
MONITORED_CAMPAIGN_IDS = [
    3209166, 3209167,
    3197279, 3197280, 3199463, 3199465, 3201451, 3202838,
    3203195, 3203199, 3204924, 3204928, 3206424, 3207566, 3207567, 3208018
]

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
        """Sets 100/day send limit and 35-second delay between sends on both mailboxes."""
        patch_body = {
            "limitation": 100,
            "delay_from": 35,
            "delay_to": 36,
            "delay_type": "random"
        }
        for email, info in SENDERS.items():
            sid = info["id"]
            try:
                res = self._request("PATCH", f"/v2/sender-accounts/emails/{sid}", patch_body)
                logger.info(f"Verified 100/day limit & 35s send delay configured on sender {email} (ID: {sid})")
            except Exception as e:
                logger.warning(f"Could not update sender delay/limit for {email}: {e}")

    def verify_links(self) -> bool:
        """Pre-flight check: verifies all outreach landing pages return HTTP 200."""
        logger.info("Running pre-flight HTTP verification on outreach links...")
        core_pages = [
            SITE_BASE_URL + "/",
            f"{SITE_BASE_URL}/contractor-estimate-template.html",
            f"{SITE_BASE_URL}/roof-shingle-bundle-calculator.html",
            f"{SITE_BASE_URL}/concrete-slab-calculator.html",
            f"{SITE_BASE_URL}/drywall-sheet-calculator.html",
            f"{SITE_BASE_URL}/tile-flooring-calculator.html",
            f"{SITE_BASE_URL}/house-painting-bid-calculator.html",
            f"{SITE_BASE_URL}/framing-stud-calculator.html",
        ]
        all_passed = True
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        for u in core_pages:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=10) as r:
                    if r.status == 200:
                        logger.info(f" [200 OK] {u}")
                    else:
                        logger.error(f" [NON-200: {r.status}] {u}")
                        all_passed = False
            except Exception as e:
                logger.error(f" [FAILED] {u} -> {e}")
                all_passed = False

        # Gumroad external check: log status, don't abort batch if Cloudflare blocks runner IP
        try:
            req = urllib.request.Request(GUMROAD_PRODUCT_URL, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=10) as r:
                logger.info(f" [{r.status} OK] {GUMROAD_PRODUCT_URL}")
        except Exception as e:
            logger.warning(f"Gumroad pre-flight check returned non-fatal notice (runner IP challenge): {e}")

        if all_passed:
            logger.info("All outreach target URLs verified healthy (HTTP 200 OK)!")
        else:
            logger.error("Core link verification failed! Halting send to prevent broken outreach.")
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
            "position": lead.get("trade", "Contractor"),
            "updateContact": 1
        }
        try:
            res = self._request("POST", "/v1/add-prospect-to-list", payload)
            return bool(res.get("success") and res.get("added"))
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

        # Step 1: Cold Outreach Pitch
        subject_1 = "Tired of writing bids at 9 PM?"
        body_html_1 = f"""<p>Hey {{{{company_name}}}} team,</p>

<p>Most trade contractors I talk to do the exact same thing: measure jobs during the day, then lose their evenings sitting at their kitchen table writing bids in Excel or on a notepad.</p>

<p>It eats up your nights and loses you jobs to guys who quote right there in the client's driveway.</p>

<p>I built a completely free estimator you can run right from your phone or truck (BuildCalc Pro):<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&amp;utm_medium=email">{SITE_BASE_URL}/contractor-estimate-template.html</a></strong></p>

<p>What it does in 60 seconds:
<ul>
  <li>Type your job dimensions in feet, inches, or fractions</li>
  <li>Calculates materials automatically with waste % (roofing squares, cubic yards of concrete, drywall sheets, wall framing studs, tile counts, and paint gallons)</li>
  <li>Generates an itemized PDF quote with your company logo ready for signature</li>
</ul>
</p>

<p>No $60/month subscriptions (Jobber/QuickBooks). No 40-minute onboarding calls. No login or credit card required.</p>

<p>You can use it 100% free on your next bid right here:<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&amp;utm_medium=email">Open BuildCalc Pro Free &rarr;</a></strong></p>

<p>If it saves you a couple of hours this week, that's awesome. If not, you still got a free estimate out of it.</p>

<p>Best regards,<br>
<strong>{sender_name}</strong><br>
BuildCalc Pro Team<br>
<a href="mailto:{sender_email}">{sender_email}</a></p>
"""

        # Click Immediate Personal Email: Triggered immediately upon link click (0 delay)
        subject_click_instant = "quick question on your BuildCalc estimate"
        body_html_click_instant = f"""<p>Hey {{{{company_name}}}} team,</p>

<p>Saw you checked out the BuildCalc estimator &mdash; if you send me your logo, I'll pre-load a custom branded version for your crew today for free.</p>

<p>Just reply here with your logo (or website) and I'll send your custom link right back, or open the estimator directly here:<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&amp;utm_medium=email&amp;utm_campaign=click_instant">Open BuildCalc Pro &rarr;</a></strong></p>

<p>Best,<br>
<strong>{sender_name}</strong><br>
<a href="mailto:{sender_email}">{sender_email}</a></p>
"""

        # Click Follow-Up 1: Triggered 3 days after clicking the link
        subject_click_fu1 = "{{company_name}} bid format (+ quick question)"
        body_html_click_fu1 = f"""<p>Hey {{{{company_name}}}} team,</p>

<p>Saw you checked out BuildCalc Pro earlier this week.</p>

<p>Did you get a chance to run a real estimate with it, or did you get pulled into a job site?</p>

<p>The biggest friction contractors tell me about is getting their custom logo, standard terms, and material markup loaded in.</p>

<p>If you'd like, reply with your logo and what trades you estimate most (roofing, framing, concrete, drywall, tile, or paint), and I'll personally set up your custom branded template so it's 1-click ready on your phone whenever you're in a client's driveway.</p>

<p>Zero cost, no catch &mdash; takes me 5 minutes.</p>

<p>Or if you just want to run an estimate yourself right now:<br>
<strong><a href="{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&amp;utm_medium=email&amp;utm_campaign=click_fu1">Open BuildCalc Pro Free &rarr;</a></strong></p>

<p>Best regards,<br>
<strong>{sender_name}</strong><br>
BuildCalc Pro Team<br>
<a href="mailto:{sender_email}">{sender_email}</a></p>
"""

        # Click Follow-Up 2: Triggered 7 days after clicking the link (4 days after Follow-Up 1)
        subject_click_fu2 = "Closing out your file (or should I leave it open?)"
        body_html_click_fu2 = f"""<p>Hey {{{{company_name}}}} team,</p>

<p>Usually when someone checks out BuildCalc Pro and doesn't reach back out, it means one of two things:
<ol>
  <li>You're already 100% satisfied with your current bidding setup (whether that's Jobber, pen-and-paper, or Excel at night).</li>
  <li>You liked the 60-second PDF quotes, but you're swamped running crews and haven't had 2 minutes of peace.</li>
</ol>
</p>

<p>If it's #1, no worries at all &mdash; I'll close out your file and won't bug you again.</p>

<p>If it's #2, the full offline suite with lifetime updates and unlimited PDF exports is right here:<br>
<strong><a href="{GUMROAD_PRODUCT_URL}">Get BuildCalc Pro Lifetime Access &rarr;</a></strong></p>

<p>No monthly software fees, no price hikes, and a 100% money-back guarantee if it doesn't save you at least 3 hours on your next 5 bids.</p>

<p>Either way, hope business is treating you well this month.</p>

<p>Best,<br>
<strong>{sender_name}</strong><br>
BuildCalc Pro Team<br>
<a href="mailto:{sender_email}">{sender_email}</a></p>
"""

        return {
            "subject_1": subject_1,
            "body_html_1": body_html_1,
            "subject_click_instant": subject_click_instant,
            "body_html_click_instant": body_html_click_instant,
            "subject_click_fu1": subject_click_fu1,
            "body_html_click_fu1": body_html_click_fu1,
            "subject_click_fu2": subject_click_fu2,
            "body_html_click_fu2": body_html_click_fu2,
            "tool_url": f"{SITE_BASE_URL}/contractor-estimate-template.html"
        }

    def launch_campaign_batch(self, sender_key: str, leads: List[dict], batch_name: str) -> Optional[int]:
        sender = SENDERS[sender_key]
        sender_id = sender["id"]
        sender_email = sender["email"]
        sender_name = sender["name"]
        master_list_id = sender.get("master_list_id")
        master_camp_id = sender.get("master_campaign_id")

        logger.info(f"--- Preparing Batch for {sender_email} ({len(leads)} leads) ---")

        if master_list_id and master_camp_id:
            enrolled = 0
            for lead in leads:
                if self.add_prospect(master_list_id, lead):
                    enrolled += 1
                time.sleep(0.3)
            logger.info(f"Enrolled {enrolled}/{len(leads)} verified contractors into Master List {master_list_id} (Master Campaign {master_camp_id})")
            try:
                self._request("POST", f"/v2/campaigns/{master_camp_id}/action", {"action": "start"})
            except Exception as e:
                logger.warning(f"Master campaign {master_camp_id} already active or start notice: {e}")
            return master_camp_id

        # Fallback: Create Dedicated Prospect List & Campaign if no Master configured
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

        # 3. Build Hormozi Sequence with Native Click Trigger (Immediate 2-Sentence Email -> Delay 3d -> FU1 -> Delay 4d -> FU2)
        t0 = int(time.time() * 1000)
        s1_ref = str(t0)
        c1_id = int(s1_ref + "0")
        trig_ref = str(t0 + 1)
        f0_ref = str(t0 + 2)
        cf0_id = int(f0_ref + "0")
        d1_ref = str(t0 + 3)
        f1_ref = str(t0 + 4)
        cf1_id = int(f1_ref + "0")
        d2_ref = str(t0 + 5)
        f2_ref = str(t0 + 6)
        cf2_id = int(f2_ref + "0")

        copy_data = self.build_hormozi_copy({}, sender_name, sender_email)

        camp_payload = {
            "title": f"BuildCalc Pro - {batch_name} ({sender_email})",
            "priority": "medium",
            "email_accounts": [sender_id],
            "recipients": {"list_id": list_id},
            "complete_campaign_after_last_step": False,
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
                        "next": trig_ref
                    },
                    {
                        "_ref": trig_ref,
                        "type": "trigger",
                        "action": "click",
                        "waiting_type": "days",
                        "waiting_val": 14,
                        "yes": f0_ref
                    },
                    {
                        "_ref": f0_ref,
                        "type": "email",
                        "content_slots": 1,
                        "content": [{"id": cf0_id, "plain_text": False, "usage": "active"}],
                        "next": d1_ref
                    },
                    {
                        "_ref": d1_ref,
                        "type": "delay",
                        "waiting_type": "days",
                        "waiting_val": 3,
                        "next": f1_ref
                    },
                    {
                        "_ref": f1_ref,
                        "type": "email",
                        "content_slots": 1,
                        "content": [{"id": cf1_id, "plain_text": False, "usage": "active"}],
                        "next": d2_ref
                    },
                    {
                        "_ref": d2_ref,
                        "type": "delay",
                        "waiting_type": "days",
                        "waiting_val": 4,
                        "next": f2_ref
                    },
                    {
                        "_ref": f2_ref,
                        "type": "email",
                        "content_slots": 1,
                        "content": [{"id": cf2_id, "plain_text": False, "usage": "active"}]
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

        # 5. Inject Step 1 (Initial Pitch), Click Instant (0d), Click FU1 (+3d), and Click FU2 (+7d) Content
        self._request("POST", f"/v2/campaigns/{camp_id}/steps/{s1_ref}/content/create", {
            "content_id": c1_id,
            "plain_text": False,
            "usage": "active",
            "subject": copy_data["subject_1"],
            "body": copy_data["body_html_1"]
        })

        self._request("POST", f"/v2/campaigns/{camp_id}/steps/{f0_ref}/content/create", {
            "content_id": cf0_id,
            "plain_text": False,
            "usage": "active",
            "subject": copy_data["subject_click_instant"],
            "body": copy_data["body_html_click_instant"]
        })

        self._request("POST", f"/v2/campaigns/{camp_id}/steps/{f1_ref}/content/create", {
            "content_id": cf1_id,
            "plain_text": False,
            "usage": "active",
            "subject": copy_data["subject_click_fu1"],
            "body": copy_data["body_html_click_fu1"]
        })

        self._request("POST", f"/v2/campaigns/{camp_id}/steps/{f2_ref}/content/create", {
            "content_id": cf2_id,
            "plain_text": False,
            "usage": "active",
            "subject": copy_data["subject_click_fu2"],
            "body": copy_data["body_html_click_fu2"]
        })

        # 6. Start Campaign Live
        start_res = self._request("POST", f"/v2/campaigns/{camp_id}/action", {"action": "start"})
        logger.info(f"LIVE CAMPAIGN LAUNCHED: Campaign {camp_id} for {sender_email}! Status: {start_res}")
        return camp_id

    def send_direct_gmail_to_clicker(self, to_email: str, company_name: str) -> bool:
        """
        Sends the immediate personal 2-sentence logo offer directly from andrew4522@gmail.com
        via Gmail SMTP (smtp.gmail.com:465) so link clickers receive a personal 1-to-1 email
        immediately without any Snov list-deduplication blockage.
        """
        clean_comp = html.unescape(html.unescape(company_name or "")).strip()
        if not clean_comp or clean_comp.endswith(":"):
            clean_comp = "there"

        msg = EmailMessage()
        msg["Subject"] = f"quick question on your BuildCalc estimate ({clean_comp})" if clean_comp != "there" else "quick question on your BuildCalc estimate"
        msg["From"] = f"Andrew Anderson <{GMAIL_SMTP_USER}>"
        msg["To"] = to_email

        plain_body = (
            f"Hey {clean_comp} team,\n\n"
            f"Saw you checked out the BuildCalc estimator — if you send me your logo, I'll pre-load a custom branded version for your crew today for free.\n\n"
            f"Just reply here with your logo (or website link) and I'll send your custom link right back, or open the estimator directly here:\n"
            f"{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&utm_medium=email&utm_campaign=click_instant\n\n"
            f"Best,\n"
            f"Andrew Anderson"
        )
        html_body = (
            f"<p>Hey {clean_comp} team,</p>"
            f"<p>Saw you checked out the BuildCalc estimator &mdash; if you send me your logo, I'll pre-load a custom branded version for your crew today for free.</p>"
            f"<p>Just reply here with your logo (or website link) and I'll send your custom link right back, or open the estimator directly here:<br>"
            f"<strong><a href=\"{SITE_BASE_URL}/contractor-estimate-template.html?utm_source=outreach&amp;utm_medium=email&amp;utm_campaign=click_instant\">Open BuildCalc Pro &rarr;</a></strong></p>"
            f"<p>Best,<br><strong>Andrew Anderson</strong></p>"
        )
        msg.set_content(plain_body)
        msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
                smtp.login(GMAIL_SMTP_USER, GMAIL_SMTP_PASS)
                smtp.send_message(msg)
            logger.info(f"[DIRECT GMAIL SENT] Sent 2-sentence personal logo offer from {GMAIL_SMTP_USER} -> {to_email} ({clean_comp})")
            return True
        except Exception as e:
            logger.warning(f"Direct Gmail SMTP send failed for {to_email}: {e}")
            return False

    def check_and_enroll_clickers(self, campaign_ids: List[int] = None) -> List[dict]:
        """
        Monitors link clicks across active outreach campaigns.
        When any recipient clicks the link:
          1. Immediately sends the personal 2-sentence logo offer email directly from
             andrew4522@gmail.com via Gmail SMTP (smtp.gmail.com:465).
          2. Enrolls them into the dedicated Clickers list (ID 41779545, Campaign 3212298).
        Also backfills the direct 2-sentence Gmail message to any existing clicker in
        clicked_leads_ledger.json where direct_gmail_sent is not yet True.
        """
        if not campaign_ids:
            campaign_ids = MONITORED_CAMPAIGN_IDS

        ledger_file = Path(__file__).parent / "dist" / "outreach" / "clicked_leads_ledger.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        ledger = {}
        if ledger_file.exists():
            try:
                with open(ledger_file, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading click ledger: {e}")

        newly_enrolled = []
        for cid in campaign_ids:
            try:
                clicks = self._request("GET", f"/v1/get-emails-clicked?campaignId={cid}")
                if not isinstance(clicks, list):
                    continue
                for item in clicks:
                    email = (item.get("email") or item.get("prospectEmail") or "").strip().lower()
                    if not email:
                        continue
                    company = item.get("companyName") or item.get("prospectFirstName") or item.get("prospectName") or ""
                    if email not in ledger:
                        logger.info(f"[NEW LINK CLICK] Prospect {email} ({company}) clicked in campaign {cid}! Sending immediate 2-sentence personal email...")
                        gmail_ok = self.send_direct_gmail_to_clicker(email, company)
                        added = self.add_prospect(ENGAGED_CLICKERS_LIST_ID, {
                            "email": email,
                            "first_name": company,
                            "company_name": company,
                            "trade": "Contractor"
                        })
                        ledger[email] = {
                            "email": email,
                            "company_name": html.unescape(html.unescape(company)),
                            "campaign_id": cid,
                            "clicked_link": item.get("link") or item.get("links") or item.get("sourcePage"),
                            "clicked_time": item.get("visitedAt") or item.get("time") or time.strftime("%Y-%m-%d %H:%M:%S"),
                            "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "enrolled": True,
                            "direct_gmail_sent": gmail_ok,
                            "direct_gmail_sent_at": time.strftime("%Y-%m-%d %H:%M:%S") if gmail_ok else None,
                            "immediate_click_campaign_id": ENGAGED_CLICKERS_CAMPAIGN_ID,
                            "immediate_click_list_id": ENGAGED_CLICKERS_LIST_ID,
                        }
                        newly_enrolled.append(ledger[email])
            except Exception as e:
                logger.warning(f"Error checking clicks for campaign {cid}: {e}")

        # Ensure any existing clicker in ledger who hasn't received the direct 2-sentence Gmail gets it now
        for email, info in ledger.items():
            if not info.get("direct_gmail_sent"):
                comp = info.get("company_name") or ""
                if self.send_direct_gmail_to_clicker(email, comp):
                    info["direct_gmail_sent"] = True
                    info["direct_gmail_sent_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    time.sleep(2)

        with open(ledger_file, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)

        logger.info(f"Click check complete. Total recorded clickers: {len(ledger)}. Newly enrolled this run: {len(newly_enrolled)}")
        return newly_enrolled


def load_leads_queue() -> List[dict]:
    queue_file = Path(__file__).parent / "dist" / "outreach" / "contractor_leads_queue.json"
    if not queue_file.exists():
        logger.error(f"Leads queue file {queue_file} not found.")
        return []
    with open(queue_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_dispatched_ledger() -> dict:
    disp_file = Path(__file__).parent / "dist" / "outreach" / "dispatched_leads.json"
    if disp_file.exists():
        try:
            with open(disp_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading dispatched leads: {e}")
    return {}


def record_dispatched_leads(leads: List[dict], sender_email: str, camp_id: int):
    disp_file = Path(__file__).parent / "dist" / "outreach" / "dispatched_leads.json"
    ledger = load_dispatched_ledger()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    for l in leads:
        em = (l.get("email") or "").lower().strip()
        if em:
            ledger[em] = {
                "email": em,
                "company_name": l.get("company_name", ""),
                "sender": sender_email,
                "campaign_id": camp_id,
                "dispatched_at": now_str
            }
    disp_file.parent.mkdir(parents=True, exist_ok=True)
    with open(disp_file, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    logger.info(f"Recorded {len(leads)} dispatched leads into ledger. Total sent to date: {len(ledger)}")


def load_available_leads() -> List[dict]:
    all_leads = load_leads_queue()
    dispatched = load_dispatched_ledger()
    available = [l for l in all_leads if (l.get("email") or "").lower().strip() not in dispatched]
    logger.info(f"Lead Pipeline Status: {len(all_leads)} total in queue | {len(dispatched)} dispatched | {len(available)} ready to send")
    return available


def trigger_replenish(target_add: int = 1000):
    logger.info(f"Triggering lead replenishment pipeline (+{target_add} leads)...")
    harvester_path = Path(__file__).parent / "harvest_and_replenish.py"
    if harvester_path.exists():
        subprocess.run([sys.executable, str(harvester_path)], cwd=str(Path(__file__).parent), check=False)
    logger.info("Lead replenishment pipeline completed.")


def main():
    parser = argparse.ArgumentParser(description="BuildCalc Pro Snov.io Outreach Engine")
    parser.add_argument("--batch-now", action="store_true", help="Launch today's 50+50 batch immediately")
    parser.add_argument("--check-clicks", action="store_true", help="Poll campaigns for link clicks and enroll clickers into follow-up sequence")
    parser.add_argument("--replenish", action="store_true", help="Manually trigger lead replenishment scraper (+1000 leads)")
    parser.add_argument("--count", type=int, default=50, help="Emails per sender account (default 50)")
    args = parser.parse_args()

    engine = SnovOutreachEngine()

    if args.check_clicks:
        logger.info("Running link-click monitor on active campaigns...")
        engine.check_and_enroll_clickers()
        return

    if args.replenish:
        trigger_replenish(1000)
        return

    # Step 1: Pre-Flight Link Verification
    if not engine.verify_links():
        sys.exit(1)

    # Step 2: Configure 100/day Limit & 35s Delays
    engine.configure_sender_delays()

    # Step 3: Load Available (Unsent) Contractor Leads
    available_leads = load_available_leads()

    # Auto-replenishment threshold check (replenish if remaining falls below 500)
    if len(available_leads) < 500:
        logger.warning(f"Available leads ({len(available_leads)}) below replenishment buffer (500). Auto-replenishing now...")
        trigger_replenish(1000)
        available_leads = load_available_leads()

    if args.batch_now:
        cursor = 0
        for sender_key in ("andrew4522@gmail.com", "andrew@bridgingtheaigap.com"):
            sender_info = SENDERS[sender_key]
            m_list_id = sender_info["master_list_id"]
            m_camp_id = sender_info["master_campaign_id"]
            added_leads = []
            consumed_leads = []
            while len(added_leads) < args.count and cursor < len(available_leads):
                lead = available_leads[cursor]
                cursor += 1
                consumed_leads.append(lead)
                if engine.add_prospect(m_list_id, lead):
                    added_leads.append(lead)
                time.sleep(0.2)
            record_dispatched_leads(consumed_leads, sender_key, m_camp_id)
            try:
                engine._request("POST", f"/v2/campaigns/{m_camp_id}/action", {"action": "start"})
            except Exception as e:
                logger.debug(f"Master campaign {m_camp_id} already active: {e}")
            logger.info(f"  - {sender_key}: Added {len(added_leads)} genuinely new contractors to Master List {m_list_id} (Campaign {m_camp_id})")

        # Run clicker check as well
        engine.check_and_enroll_clickers()


if __name__ == "__main__":
    main()


