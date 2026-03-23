import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

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
    "User-Agent": "Mozilla/5.0",
}

# Regex to extract price and currency
PRICE_REGEX = re.compile(r"(\$|£|€)\s?(\d+\.?\d*)")

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def get_soup(url, lang):
    headers = HEADERS.copy()
    headers["Accept-Language"] = lang
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException:
        return None

def extract_price_info(text):
    match = PRICE_REGEX.search(text)
    if match:
        currency, price = match.groups()
        return currency, price
    return None, None

# -----------------------------
# SERVICE SCRAPERS
# -----------------------------
def scrape_spotify(region, lang):
    url = "https://www.spotify.com/premium/"
    soup = get_soup(url, lang)
    if not soup:
        return []

    data = []
    for plan_div in soup.find_all("div"):
        text = plan_div.get_text(" ", strip=True)
        if "month" in text.lower() or "$" in text or "£" in text:
            currency, price = extract_price_info(text)
            data.append({
                "service": "Spotify",
                "region": region,
                "plan_name": text[:50],
                "price": price,
                "currency": currency
            })
    return data

def scrape_apple(region, lang):
    url = "https://www.apple.com/apple-tv-plus/"
    soup = get_soup(url, lang)
    if not soup:
        return []

    data = []
    text = soup.get_text(" ", strip=True)
    for line in text.split("."):
        currency, price = extract_price_info(line)
        if price:
            data.append({
                "service": "Apple TV+",
                "region": region,
                "plan_name": line.strip()[:50],
                "price": price,
                "currency": currency
            })
    return data

def scrape_amazon(region, lang):
    url = "https://www.amazon.com/amazonprime"
    soup = get_soup(url, lang)
    if not soup:
        return []

    data = []
    text = soup.get_text(" ", strip=True)
    for line in text.split("."):
        currency, price = extract_price_info(line)
        if price:
            data.append({
                "service": "Amazon Prime",
                "region": region,
                "plan_name": line.strip()[:50],
                "price": price,
                "currency": currency
            })
    return data

# -----------------------------
# MAIN RUNNER
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
# SAVE RESULTS
# -----------------------------
df = pd.DataFrame(all_data)
df.drop_duplicates(inplace=True)
df.to_csv("streaming_prices3.csv", index=False)

print("Done! Data saved to streaming_prices.csv")
print(df.head())