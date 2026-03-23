import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# -----------------------------
# CONFIG: Regions
# -----------------------------
REGIONS = {
    "US": "en-US",
    "UK": "en-GB",
    "India": "en-IN",
    "Lebanon": "en-LB"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -----------------------------
# HELPER: Extract price info
# -----------------------------
def extract_price_info(text):
    """
    Extracts currency, price, and billing period from text
    """
    currency, price = None, None
    match = re.search(r'([\$£₹€])\s?(\d+(\.\d+)?)', text)
    if match:
        currency = match.group(1)
        price = float(match.group(2))

    # Billing period
    if "month" in text.lower():
        billing = "Monthly"
    elif "year" in text.lower():
        billing = "Yearly"
    else:
        billing = "Unknown"

    return currency, price, billing

# -----------------------------
# GENERAL SCRAPER FUNCTION
# -----------------------------
def scrape_platform(name, url, region, lang, plan_name="Standard"):
    """
    Generic scraper for platforms with public pages
    """
    results = []
    try:
        headers = HEADERS.copy()
        headers["Accept-Language"] = lang
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        
        currency, price, billing = extract_price_info(text)
        if price:
            results.append({
                "Service": name,
                "Region": region,
                "Plan": plan_name,
                "Price": price,
                "Currency": currency,
                "Billing": billing
            })
    except Exception as e:
        print(f"Error scraping {name} ({region}): {e}")
    return results

# -----------------------------
# PLATFORMS CONFIG
# -----------------------------
platforms = [
    {"name": "Spotify", "url": "https://www.spotify.com/premium/", "plan": "Premium"},
    {"name": "Apple TV+", "url": "https://www.apple.com/apple-tv-plus/", "plan": "Standard"},
    {"name": "Amazon Prime", "url": "https://www.amazon.com/amazonprime", "plan": "Prime"},
    {"name": "YouTube Premium", "url": "https://www.youtube.com/premium", "plan": "Premium"},
    {"name": "Deezer", "url": "https://www.deezer.com/offers", "plan": "Premium"}
]

# -----------------------------
# SCRAPE ALL REGIONS & PLATFORMS
# -----------------------------
all_data = []

for region, lang in REGIONS.items():
    print(f"Scraping region: {region}")
    for platform in platforms:
        all_data += scrape_platform(
            platform["name"],
            platform["url"],
            region,
            lang,
            platform["plan"]
        )
        time.sleep(2)  # polite delay

# -----------------------------
# CREATE CLEAN DATAFRAME
# -----------------------------
df = pd.DataFrame(all_data)
df = df.drop_duplicates()
df = df.sort_values(by=["Service", "Region", "Plan"])

# -----------------------------
# SAVE TO EXCEL
# -----------------------------
excel_file = "streaming_prices_clean.xlsx"
df.to_excel(excel_file, index=False)
print(f"\n✅ Excel file created: {excel_file}")
print(df)