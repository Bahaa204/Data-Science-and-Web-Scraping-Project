import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
REGIONS = [
    ("US", "en-US"),
    ("UK", "en-GB"),
    ("India", "en-IN"),
    ("Lebanon", "en-LB")
]

INDEX_FILE = "region_index.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

PRICE_REGEX = re.compile(r"(\$|£|€)\s?(\d+\.?\d*)")

# -----------------------------
# REGION ROTATION (PERSISTENT)
# -----------------------------
def get_region_index():
    try:
        with open(INDEX_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_region_index(index):
    with open(INDEX_FILE, "w") as f:
        f.write(str(index))

# -----------------------------
# HELPERS
# -----------------------------
def get_soup(url, lang):
    headers = HEADERS.copy()
    headers["Accept-Language"] = lang
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except:
        return None

def extract_price_info(text):
    match = PRICE_REGEX.search(text)
    if match:
        return match.group(2), match.group(1)
    return None, None

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# -----------------------------
# SCRAPERS (same as before)
# -----------------------------
def scrape_spotify(region, lang):
    url = "https://www.spotify.com/premium/"
    soup = get_soup(url, lang)
    if not soup:
        return []

    data = []
    for div in soup.find_all("div"):
        text = clean_text(div.get_text())
        if "month" in text.lower():
            price, currency = extract_price_info(text)
            if price:
                data.append({
                    "service": "Spotify",
                    "region": region,
                    "plan_type": "Music",
                    "plan_name": text[:60],
                    "price": price,
                    "currency": currency
                })
    return data


def scrape_netflix(region, lang):
    url = "https://www.netflix.com/"
    soup = get_soup(url, lang)
    if not soup:
        return []

    data = []
    text = soup.get_text(" ", strip=True)

    for line in text.split("."):
        if "month" in line.lower():
            price, currency = extract_price_info(line)
            if price:
                data.append({
                    "service": "Netflix",
                    "region": region,
                    "plan_type": "Streaming",
                    "plan_name": clean_text(line[:60]),
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
        price, currency = extract_price_info(line)
        if price:
            data.append({
                "service": "Apple TV+",
                "region": region,
                "plan_type": "Streaming",
                "plan_name": clean_text(line[:60]),
                "price": price,
                "currency": currency
            })
    return data


def scrape_youtube(region, lang):
    url = "https://www.youtube.com/premium"
    soup = get_soup(url, lang)
    if not soup:
        return []

    data = []
    text = soup.get_text(" ", strip=True)

    for line in text.split("."):
        price, currency = extract_price_info(line)
        if price:
            data.append({
                "service": "YouTube Premium",
                "region": region,
                "plan_type": "Video+Music",
                "plan_name": clean_text(line[:60]),
                "price": price,
                "currency": currency
            })
    return data


# -----------------------------
# MAIN
# -----------------------------
def run():
    index = get_region_index()
    region, lang = REGIONS[index]

    print(f"Running for region: {region}")

    data = []

    data.extend(scrape_spotify(region, lang))
    time.sleep(2)

    data.extend(scrape_netflix(region, lang))
    time.sleep(2)

    data.extend(scrape_apple(region, lang))
    time.sleep(2)

    data.extend(scrape_youtube(region, lang))

    if data:
        df = pd.DataFrame(data)
        df.drop_duplicates(inplace=True)

        filename = f"data_{region}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False)

    # update region index
    next_index = (index + 1) % len(REGIONS)
    save_region_index(next_index)


if __name__ == "__main__":
    run()
