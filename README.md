# BuildCalc Pro — Contractor Estimator & Invoice Suite

A 100% client-side, zero-backend-cost software and Programmatic SEO + Cold Outreach engine built to generate recurring and lifetime license revenue from independent trade contractors.

## What Has Been Built

1. **Core Web App & 52 Programmatic SEO Pages (`dist/site/`)**
   - **8 Trade Calculators** with native **Feet / Inches / Fractions** (`14' 6-3/8"`) parser and quick tape-measure pad:
     - Concrete Slabs, Footings & Sonotube Piers
     - Wall Framing, Studs (`16" OC` / `24" OC`), Plates & OSB Sheathing
     - Roof Pitch Multiplier, Squares & Shingle Bundles
     - Drywall Sheets (`4x8` & `4x12`), Joint Compound & Tape
     - Stair Stringers, Rise/Run & IRC R311.7 Code Check
     - Decking Boards, Substructure Joists & Board-Feet
     - Interior/Exterior Paint & Primer Gallons
     - Tile, Flooring, Thinset Mortar, Backer Board & Grout
   - **1-Click Client Estimate & Invoice PDF Builder** with automatic Overhead/Profit Markup %, Tax %, Deposit Due %, and Customer Signature Block.
   - **Built-in Freemium Paywall & Zero-Backend License Verification** (verifies directly against Gumroad's free License Verification API + supports test key `DEMO-PRO-2026`).
   - **52 Static SEO Pages** + `sitemap.xml` + `robots.txt` + `llms.txt` + `manifest.webmanifest`.

2. **Chrome / Edge / Firefox Manifest V3 Extension (`dist/buildcalc-pro-extension-mv3.zip`)**
   - Toolbar Popup + Browser Side Panel (`sidePanel`) so contractors can calculate materials right next to Home Depot, Lowe's, or Ferguson tabs.
   - Pre-localized into **20 languages** (`dist/extension/_locales/`).

3. **Android Offline Bundle & 20-Language Google Play ASO Pack (`dist/android/`)**
   - Offline WebView assets (`dist/android/app/src/main/assets/`)
   - Complete 20-language store listing copy (`dist/android/google_play_aso_20_languages.json`).

4. **Automated Contractor Lead Scraper & Hormozi Outreach Bot (`outreach_bot.py`)**
   - Scrapes real trade contractors from OpenStreetMap Overpass API, crawls websites for email addresses, and generates tailored Alex Hormozi outreach emails (`dist/outreach/contractor_leads_queue.csv`).

5. **GitHub Actions Full Autopilot (`.github/workflows/deploy-and-outreach.yml`)**
   - Deploys the 52-page site to GitHub Pages for `$0/month` and runs the daily contractor scraping + SMTP outreach loop automatically at 9:00 AM EST.
