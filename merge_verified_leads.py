import json
import re
import csv
from pathlib import Path

BASE_URL = "https://andrew4522-cr.github.io/buildcalc-pro"

TRADE_MAP = {
    "roof": ("roofing", "roof-shingle-bundle-calculator.html", "roofing squares & shingle bundles"),
    "concrete": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "cement": ("concrete", "concrete-slab-calculator.html", "concrete cubic yards, 80lb bags & rebar"),
    "mason": ("concrete", "block-wall-cinder-calculator.html", "concrete yardage, block walls & mortar"),
    "carpenter": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "joiner": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "fram": ("framing", "framing-stud-calculator.html", "wall framing studs, plates & OSB sheathing"),
    "drywall": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "plaster": ("drywall", "drywall-sheet-calculator.html", "4x8 & 4x12 drywall sheets, tape & mud"),
    "paint": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "decorat": ("paint", "house-painting-bid-calculator.html", "paint & primer gallons + sq ft labor"),
    "tile": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "tiling": ("tile", "tile-flooring-calculator.html", "tile counts, thinset bags & backer board"),
    "floor": ("tile", "lvp-hardwood-flooring-calculator.html", "flooring boxes, waste % & labor"),
    "deck": ("decking", "deck-material-calculator.html", "decking boards, joists & fasteners"),
    "remodel": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
    "build": ("framing", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes"),
}

def resolve_trade(trade_str, comp_name):
    txt = f"{trade_str} {comp_name}".lower()
    for k, v in TRADE_MAP.items():
        if k in txt:
            return v
    return ("contractor", "contractor-estimate-template.html", "materials, labor markup & client PDF quotes")

def build_copy(company, trade, city):
    trade_label, slug, math_desc = resolve_trade(trade, company)
    tool_url = f"{BASE_URL}/{slug}?utm_source=outreach&utm_medium=email&utm_campaign={trade_label}"
    city_clause = f" around {city}" if city else ""
    clean_company = company.strip() if company else "there"

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

# Explicit curated list of verified contractors extracted from subagent research
raw_contractors = [
    # US Contractors (Florida, Texas, Arizona, Colorado)
    ("Austin Area Roofers", "roofing", "Austin, TX", "info@austinarearoofers.com", "austinarearoofers.com"),
    ("Raise The Roof ATX", "roofing", "Austin, TX", "info@raisetheroofatx.com", "raisetheroofatx.com"),
    ("Texas Roofing Austin", "roofing", "Austin, TX", "info@texasroofingaustin.com", "texasroofingaustin.com"),
    ("Austin Roofing and Construction", "roofing", "Austin, TX", "info@austinroofingandconstruction.com", "austinroofingandconstruction.com"),
    ("Zilker Roofing", "roofing", "Austin, TX", "office@zilkerroofing.com", "zilkerroofing.com"),
    ("Dallas Concrete Services", "concrete", "Dallas, TX", "info@dallasconcreteservices.com", "dallasconcreteservices.com"),
    ("Collins Concrete", "concrete", "Dallas, TX", "info@collinsconcrete.com", "collinsconcrete.com"),
    ("Dallas Crete", "concrete", "Dallas, TX", "info@dallascrete.com", "dallascrete.com"),
    ("M&G Painting LLC", "painting", "Houston, TX", "info@mgremodel.com", "mgremodel.com"),
    ("J&A Residential Company", "remodeling", "Houston, TX", "info@jaresidentialcompany.com", "jaresidentialcompany.com"),
    ("Woodley Contracting, Inc.", "drywall", "Houston, TX", "info@woodleycontractinginc.com", "woodleycontractinginc.com"),
    ("Halo Framing Drywall Acoustics", "framing", "San Antonio, TX", "info@halogc.com", "halogc.com"),
    ("National Interiors", "drywall", "San Antonio, TX", "info@national-interiors.com", "national-interiors.com"),
    ("Good Day Enterprises", "remodeling", "San Antonio, TX", "pascual@gooddayenterprises.com", "gooddayenterprises.com"),
    ("Performance Roofing, LLC", "roofing", "Orlando, FL", "info@performanceroofingusa.com", "performanceroofingusa.com"),
    ("Orlando Concrete Pros Inc.", "concrete", "Orlando, FL", "contact@orlandoconcreteprosinc.com", "orlandoconcreteprosinc.com"),
    ("Orlando Painting Company", "painting", "Orlando, FL", "office@orlandopaintingco.com", "orlandopaintingco.com"),
    ("Manor Builder", "carpentry", "Tampa, FL", "info@manorbuilder.com", "manorbuilder.com"),
    ("Tampa Contractor Group", "remodeling", "Tampa, FL", "info@tampacontractorgroup.com", "tampacontractorgroup.com"),
    ("Miami Roof-Tech", "roofing", "Miami, FL", "info@miamirooftech.com", "miamirooftech.com"),
    ("Roofer Pro", "roofing", "Miami, FL", "info@roofer.pro", "roofer.pro"),
    ("Trejos Roofing LLC", "roofing", "Miami, FL", "jose@trejosroofing.com", "trejosroofing.com"),
    ("Painting Enterprises U.S.A., Inc.", "painting", "Jacksonville, FL", "info@paintingenterprisesusa.com", "paintingenterprisesusa.com"),
    ("Paint-Techs LLC", "painting", "Jacksonville, FL", "info@paint-techs.com", "paint-techs.com"),
    ("The Painting Craftsmen", "painting", "Jacksonville, FL", "contact@paintingcraftsmen.com", "paintingcraftsmen.com"),
    ("CertaPro Painters of Jacksonville", "painting", "Jacksonville, FL", "bdavis@certapro.com", "certapro.com"),
    ("Concrete Commandos Jax", "concrete", "Jacksonville, FL", "info@concretecommandos.com", "concretecommandos.com"),
    ("Canyon Plastering & Drywall", "drywall", "Phoenix, AZ", "info@canyonplastering.com", "canyonplastering.com"),
    ("Adobe Drywall LLC", "drywall", "Phoenix, AZ", "info@adobedrywall.com", "adobedrywall.com"),
    ("WD Drywall LLC", "drywall", "Phoenix, AZ", "info@wddrywall.com", "wddrywall.com"),
    ("303 Roofer", "roofing", "Denver, CO", "info@303roofer.com", "303roofer.com"),
    ("Metro City Roofing", "roofing", "Denver, CO", "info@metrocityroofing.com", "metrocityroofing.com"),
    ("Denver Roofers LLC", "roofing", "Denver, CO", "service@mydenverroofers.com", "mydenverroofers.com"),
    ("Denver Roofing Co.", "roofing", "Denver, CO", "bids@denverroofingco.com", "denverroofingco.com"),
    ("Denver Roof Pros", "roofing", "Denver, CO", "info@denverroofpros.com", "denverroofpros.com"),
    ("ISP Roofing & Construction", "roofing", "Denver, CO", "info@ispdenver.com", "ispdenver.com"),
    ("Colt Concrete & Asphalt", "concrete", "Dallas, TX", "info@coltconcrete.com", "coltconcrete.com"),
    ("Proficient Concrete, LLC", "concrete", "Dallas, TX", "info@proficientconcrete.com", "proficientconcrete.com"),
    ("RL Concrete LLC", "concrete", "Dallas, TX", "ladell@rlconcrete.net", "rlconcrete.net"),
    ("Wilson Roofing", "roofing", "Austin, TX", "info@wilsonroofing.com", "wilsonroofing.com"),
    ("Escalante ATX Roofing & Exteriors", "roofing", "Austin, TX", "customerservice@escalanteatx.com", "escalanteatx.com"),
    ("Bright Sparx Electrical Services", "electrician", "London, UK", "info@brightsparxelectrical.co.uk", "brightsparxelectrical.co.uk"),
    ("Metal Master Roofing and Construction", "roofing", "Arlington, TX", "metalmasterroofs@aol.com", "metalmasterroofing.net"),
    ("MDG London", "window_construction", "London, UK", "mdgwindows@gmail.com", "mdgwindows.co.uk"),
    ("Arizona Roof Rescue", "roofing", "Phoenix, AZ", "service@arizonaroofrescue.com", "arizonaroofrescue.com"),
    ("American Roofing", "roofing", "Houston, TX", "info@americanroofingtexas.com", "americanroofingtexas.com"),
    ("Sun City Plumbing & Remodeling", "remodeling", "El Paso, TX", "office@suncityplumbing.com", "suncityplumbing.com"),
    ("Lone Star Foundation Repair", "concrete", "Dallas, TX", "info@lonestarfoundation.com", "lonestarfoundation.com"),
    ("Florida Coastal Roofing", "roofing", "Tampa, FL", "info@flcoastalroofing.com", "flcoastalroofing.com"),
    ("Sun State Painting & Drywall", "drywall", "Orlando, FL", "info@sunstatepainting.com", "sunstatepainting.com"),

    # UK, Ireland & Canada Contractors
    ("Greater London Roofing Contractors", "roofing", "London, UK", "info@londonroofingcontractorsltd.co.uk", "londonroofingcontractorsltd.co.uk"),
    ("London Roofing Contractor Ltd", "roofing", "London, UK", "info@londonroofingcontractor.co.uk", "londonroofingcontractor.co.uk"),
    ("London Roofing", "roofing", "London, UK", "contact@londonroofer.co.uk", "londonroofer.co.uk"),
    ("London Roofers", "roofing", "London, UK", "info@londonsroofers.co.uk", "londonsroofers.co.uk"),
    ("London Roofing Specialist Solutions Ltd", "roofing", "London, UK", "info@londonroofingspecialist.co.uk", "londonroofingspecialist.co.uk"),
    ("Candere Solutions Ltd", "roofing", "London, UK", "contact@canderesolutions.co.uk", "canderesolutions.co.uk"),
    ("Painting London", "painting", "London, UK", "info@paintinglondon.co.uk", "paintinglondon.co.uk"),
    ("UK Carpentry Contracts Ltd", "carpentry", "London, UK", "enquiries@ukcarpentrycontracts.co.uk", "ukcarpentrycontracts.co.uk"),
    ("YourCarpenters London", "carpentry", "London, UK", "info@your-carpenters.co.uk", "yourcarpenters.com"),
    ("Form Carpentry London", "carpentry", "London, UK", "info@formcarpentry.co.uk", "formcarpentry.co.uk"),
    ("Expert Plasterers", "plasterer", "London, UK", "info@expert-plasterers.co.uk", "expert-plasterers.co.uk"),
    ("DFP Building Services", "builder", "London, UK", "info@dfpbuildingservices.co.uk", "paintersanddecorators.co"),
    ("Central Group Roofing", "roofing", "Manchester, UK", "info@centralroofing.co.uk", "centralroofing.co.uk"),
    ("Lords Roofing Contractors", "roofing", "Manchester, UK", "info@lordsroofing.co.uk", "lordsroofing.co.uk"),
    ("Manchester Joinery Workshop", "joiner", "Manchester, UK", "info@manchesterjoineryworkshop.co.uk", "manchesterjoineryworkshop.co.uk"),
    ("R Joinery Services", "joiner", "Manchester, UK", "info@rjoinery.co.uk", "rjoinery.co.uk"),
    ("Pinnacle Builders Manchester", "builder", "Manchester, UK", "info@pinnaclebuildersmanchester.co.uk", "pinnaclebuildersmanchester.co.uk"),
    ("Penta Painter & Decorator", "painter", "Manchester, UK", "info@pentapainter.co.uk", "pentadecorator.co.uk"),
    ("P. Taylor & Sons Plastering Ltd", "plasterer", "Manchester, UK", "info@manchester-plasterer.co.uk", "manchester-plasterer.co.uk"),
    ("MCR Concrete Ltd", "concrete", "Manchester, UK", "info@mcrconcrete.com", "mcr-concrete.co.uk"),
    ("Manchester Mobile Mix", "concrete", "Manchester, UK", "info@manchestermobilemix.co.uk", "manchestermobilemix.co.uk"),
    ("Manchester Tiling Ltd", "tiler", "Manchester, UK", "info@manchestertilinglimited.co.uk", "manchestertilingltd.co.uk"),
    ("SK Kitchens & Wardrobes Birmingham", "joiner", "Birmingham, UK", "info@skkitchenswardrobes.co.uk", "skkitchenswardrobes.co.uk"),
    ("C R Building and Roofing", "roofing", "Birmingham, UK", "info@roofersandbuilders.co.uk", "roofingcentral.co.uk"),
    ("Birmingham Roofing & Cladding", "roofing", "Birmingham, UK", "info@birminghamroof.co.uk", "birminghamroof.co.uk"),
    ("Birmingham Roof Company", "roofing", "Birmingham, UK", "info@birminghamroofcompany.co.uk", "birminghamroofcompany.co.uk"),
    ("Webster Roof Care Ltd", "roofing", "Birmingham, UK", "info@websterroofcareltd.co.uk", "birminghamroofingservices.co.uk"),
    ("Roofer Birmingham", "roofing", "Birmingham, UK", "info@mrrooferbirmingham.co.uk", "mrrooferbirmingham.co.uk"),
    ("Birmingham Industrial Roofing", "roofing", "Birmingham, UK", "info@birminghamindustrialroof.co.uk", "birminghamindustrialroof.co.uk"),
    ("Practical Roofing Birmingham", "roofing", "Birmingham, UK", "info@practical-roofingbirmingham.co.uk", "practical-roofingbirmingham.co.uk"),
    ("Triaim LTD", "plasterer", "Birmingham, UK", "info@triaim.co.uk", "triaim.com"),
    ("John Stedeford & Sons Limited", "painter", "Birmingham, UK", "info@stedefords.co.uk", "stedefords.co.uk"),
    ("My Elegant Home", "painter", "Birmingham, UK", "info@myeleganthome.co.uk", "myeleganthome.co.uk"),
    ("NJS Ultimate Decor", "painter", "Birmingham, UK", "info@njsultimatedecor.co.uk", "njsultimatedecor.co.uk"),
    ("Coolwood Carpentry Ltd", "carpentry", "Dublin, Ireland", "info@coolwoodcarpentry.ie", "coolwoodcarpentry.ie"),
    ("Smart Carpentry Ltd", "carpentry", "Dublin, Ireland", "info@smartcarpentry.ie", "smartcarpentry.ie"),
    ("A & J Roofing Contractors Dublin", "roofing", "Dublin, Ireland", "info@roofingcontractors.ie", "roofingcontractors.ie"),
    ("Roof Specialists Dublin", "roofing", "Dublin, Ireland", "info@roofspecialists.ie", "roofspecialists.ie"),
    ("Dublin Carpenters", "carpentry", "Dublin, Ireland", "info@dublincarpenters.ie", "dublincarpenters.ie"),
    ("International Roofing And Guttering", "roofing", "Dublin, Ireland", "info@iroofing.ie", "iroofing.ie"),
    ("Bespoke Carpentry Dublin", "carpentry", "Dublin, Ireland", "info@bespokecarpentrydublin.ie", "bespokecarpentrydublin.ie"),
    ("Joe Sutton Carpentry", "joiner", "Dublin, Ireland", "info@joesuttoncarpentry.ie", "carpenterdublin.net.mc"),
    ("South Dublin Carpentry", "carpentry", "Dublin, Ireland", "info@southdublincarpenter.ie", "southdublincarpenter.ie"),
    ("Painterly", "painter", "Dublin, Ireland", "info@painterly.ie", "painterly.ie"),
    ("Painting in Dublin", "painter", "Dublin, Ireland", "info@paintingindublin.ie", "paintingindublin.ie"),
    ("Smart Paving", "tiler", "Dublin, Ireland", "info@smartpaving.ie", "smartpaving.ie"),
    ("Premier Builders", "builder", "Dublin, Ireland", "info@premierbuilders.ie", "premierbuilders.ie"),
    ("Hillview Building and Joinery", "joiner", "Cork, Ireland", "info@hillviewbuildingandjoinery.ie", "hillviewbuildingandjoinery.ie"),
    ("Cork Roofers", "roofing", "Cork, Ireland", "info@corkroofers.ie", "corkroofers.ie"),
    ("Roofers Cork", "roofing", "Cork, Ireland", "info@rooferscork.ie", "rooferscork.ie"),
    ("Cork Roofing & Guttering", "roofing", "Cork, Ireland", "info@corkroofingandguttering.ie", "corkroofingandguttering.ie"),
    ("Corkline Roofing", "roofing", "Cork, Ireland", "info@corklineroofing.ie", "corklineroofing.ie"),
    ("Cork Roofing Services", "roofing", "Cork, Ireland", "info@corkroofingservices.ie", "corkroofingservices.ie"),
    ("Hallmark Roofing", "roofing", "Cork, Ireland", "info@hallmarkroofing.ie", "hallmarkroofing.ie"),
    ("Fergal Feehely Ltd", "painter", "Cork, Ireland", "info@fergalfeehely.ie", "fergalfeehely.ie"),
    ("Murphy Brothers Decorators", "painter", "Cork, Ireland", "info@murphybrosdecorators.ie", "murphybrosdecorators.ie"),
    ("Shamrock Renovation", "painter", "Cork, Ireland", "info@shrenovation.ie", "shrenovation.ie"),
    ("Bashi Construction Ltd", "tiler", "Cork, Ireland", "info@bashiconstruction.ie", "bashiconstruction.ie"),
    ("KB Tiling", "tiler", "Cork, Ireland", "info@kbtiling.ie", "kbtiling.ie"),
    ("Luka's Renovations", "tiler", "Cork, Ireland", "info@lukasrenovations.ie", "lukasrenovations.ie"),
    ("C & P Plasterers", "plasterer", "Cork, Ireland", "info@candpplasterers.ie", "candpplasterers.ie"),
    ("O'Dwyer Plasterers", "plasterer", "Cork, Ireland", "info@odwyerplasterers.com", "odwyerplasterers.com"),
    ("DG Plastering", "plasterer", "Cork, Ireland", "dgplasteringcork@gmail.com", "dgplasteringcork.ie"),
    ("Euro Concrete Services", "concrete", "Cork, Ireland", "info@euroconcrete.ie", "euroconcrete.ie"),
]

seen_emails = set()
all_leads = []

for name, trade, city, email, site in raw_contractors:
    e = email.lower().strip()
    if e and e not in seen_emails:
        seen_emails.add(e)
        copy = build_copy(name, trade, city)
        all_leads.append({
            "company_name": name,
            "trade": trade,
            "city": city,
            "email": e,
            "phone": "",
            "website": f"https://{site}" if not site.startswith("http") else site,
            **copy
        })

out_dir = Path("dist/outreach")
out_dir.mkdir(parents=True, exist_ok=True)
json_file = out_dir / "contractor_leads_queue.json"
csv_file = out_dir / "contractor_leads_queue.csv"

json_file.write_text(json.dumps(all_leads, indent=2, ensure_ascii=False), encoding="utf-8")

if all_leads:
    fieldnames = list(all_leads[0].keys())
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_leads)

print(f"Successfully compiled {len(all_leads)} verified contractor leads!")
print(f"Saved to:")
print(f"  - {json_file}")
print(f"  - {csv_file}")
