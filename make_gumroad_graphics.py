import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out_dir = Path(r"C:\Users\Users\.gemini\antigravity\scratch\app-factory\buildcalc-pro\dist\gumroad-assets")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Generate Cover (1280x720)
cover = Image.new("RGB", (1280, 720), color=(15, 23, 42)) # Slate 900
d = ImageDraw.Draw(cover)

# Accent gradient/lines
d.rectangle([0, 0, 1280, 8], fill=(245, 158, 11)) # Amber top bar
d.rectangle([40, 60, 220, 95], fill=(245, 158, 11)) # Badge
d.rectangle([50, 120, 1230, 660], outline=(30, 41, 59), width=2) # Frame

# Try to get default font or truetype
try:
    font_large = ImageFont.truetype("arial.ttf", 52)
    font_med = ImageFont.truetype("arial.ttf", 28)
    font_small = ImageFont.truetype("arial.ttf", 20)
    font_badge = ImageFont.truetype("arialbd.ttf", 20)
    font_hero = ImageFont.truetype("arialbd.ttf", 64)
except Exception:
    font_large = font_med = font_small = font_badge = font_hero = ImageFont.load_default()

d.text((55, 67), "BUILDCALC PRO", fill=(15, 23, 42), font=font_badge)
d.text((50, 140), "Contractor Estimator & Quote Suite", fill=(255, 255, 255), font=font_hero)
d.text((50, 230), "Turn job measurements into branded client PDF estimates in 60 seconds.", fill=(203, 213, 225), font=font_med)

features = [
    "✓ 8 Trade Calculators (Concrete, Framing, Roofing, Drywall, Stairs, Decks, Paint, Tile)",
    "✓ Native Feet, Inches & Fraction Tape-Measure Pad (14' 6-3/8\")",
    "✓ 1-Click Client Estimate & Invoice PDF Maker with Your Company Logo",
    "✓ Remove All Watermarks + Customer Acceptance Signature Block",
    "✓ Works 100% Offline in your truck — Zero monthly subscription fees"
]

y_off = 310
for f in features:
    d.text((70, y_off), f, fill=(245, 158, 11) if "✓" in f else (255, 255, 255), font=font_med)
    y_off += 55

d.rectangle([70, 590, 420, 650], fill=(245, 158, 11))
d.text((95, 605), "LIFETIME PRO LICENSE", fill=(15, 23, 42), font=font_badge)

cover_path = out_dir / "cover_1280x720.png"
cover.save(cover_path)

# 2. Generate Thumbnail (600x600)
thumb = Image.new("RGB", (600, 600), color=(15, 23, 42))
dt = ImageDraw.Draw(thumb)
dt.rectangle([0, 0, 600, 10], fill=(245, 158, 11))
dt.rectangle([20, 20, 580, 580], outline=(30, 41, 59), width=3)

# Logo box
dt.rectangle([190, 80, 410, 260], fill=(245, 158, 11))
try:
    font_logo = ImageFont.truetype("arialbd.ttf", 96)
except Exception:
    font_logo = ImageFont.load_default()
dt.text((225, 120), "BC", fill=(15, 23, 42), font=font_logo)

dt.text((120, 290), "BuildCalc Pro", fill=(255, 255, 255), font=font_large)
dt.text((105, 360), "Contractor Estimator & PDF Suite", fill=(245, 158, 11), font=font_small)
dt.text((150, 420), "• Concrete, Framing, Roofs", fill=(203, 213, 225), font=font_small)
dt.text((150, 455), "• 60-Sec Branded Invoices", fill=(203, 213, 225), font=font_small)
dt.text((150, 490), "• Lifetime Offline Access", fill=(203, 213, 225), font=font_small)

thumb_path = out_dir / "thumbnail_600x600.png"
thumb.save(thumb_path)

print(f"Created: {cover_path}")
print(f"Created: {thumb_path}")
