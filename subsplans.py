import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# -----------------------------
# CONFIG
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
# HELPER: Extract price
# -----------------------------
def extract_price(text):
    match = re.search(r'([\$£₹€])\s?(\d+(\.\d+)?)', text)
    if match:
        return match.group(1), float(match.group(2))
    return None, None

# -----------------------------
# SPOTIFY
# -----------------------------
def scrape_spotify(region, lang):
    url = "https://www.spotify.com/premium/"
    headers = HEADERS.copy()
    headers["Accept-Language"] = lang

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    plans = soup.find_all("div")

    for plan in plans:
        text = plan.get_text(" ", strip=True)

        if "Premium" in text and ("month" in text.lower()):
            currency, price = extract_price(text)

            results.append({
                "Service": "Spotify",
                "Region": region,
                "Plan": text.split(" ")[0],
                "Price": price,
                "Currency": currency,
                "Billing": "Monthly"
            })

    return results


# -----------------------------
# APPLE TV+
# -----------------------------
def scrape_apple(region, lang):
    url = "https://www.apple.com/apple-tv-plus/"
    headers = HEADERS.copy()
    headers["Accept-Language"] = lang

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(" ", strip=True)

    results = []

    currency, price = extract_price(text)

    if price:
        results.append({
            "Service": "Apple TV+",
            "Region": region,
            "Plan": "Standard",
            "Price": price,
            "Currency": currency,
            "Billing": "Monthly"
        })

    return results


# -----------------------------
# AMAZON PRIME
# -----------------------------
def scrape_amazon(region, lang):
    url = "https://www.amazon.com/amazonprime"
    headers = HEADERS.copy()
    headers["Accept-Language"] = lang

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(" ", strip=True)

    results = []

    currency, price = extract_price(text)

    if price:
        results.append({
            "Service": "Amazon Prime",
            "Region": region,
            "Plan": "Prime",
            "Price": price,
            "Currency": currency,
            "Billing": "Monthly/Yearly"
        })

    return results


# -----------------------------
# MAIN
# -----------------------------
all_data = []

for region, lang in REGIONS.items():
    print(f"Scraping {region}...")

    all_data.extend(scrape_spotify(region, lang))
    time.sleep(2)

    all_data.extend(scrape_apple(region, lang))
    time.sleep(2)

    all_data.extend(scrape_amazon(region, lang))
    time.sleep(2)

# -----------------------------
# DATAFRAME
# -----------------------------
df = pd.DataFrame(all_data)

# Remove duplicates
df = df.drop_duplicates()

# Sort nicely
df = df.sort_values(by=["Service", "Region"])

# -----------------------------
# SAVE TO EXCEL
# -----------------------------
df.to_excel("streaming_prices.xlsx", index=False)

print("\n✅ Excel file created: streaming_prices.xlsx")
print(df)