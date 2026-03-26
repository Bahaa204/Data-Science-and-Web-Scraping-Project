import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------------
# CONFIG
# -----------------------------
REGIONS = [
    ("US", "en-US"),
    ("UK", "en-GB"),
    ("India", "en-IN"),
    ("Lebanon", "en-LB"),
    ("Canada", "en-CA"),
    ("Germany", "de-DE"),
    ("Australia", "en-AU")
]

INDEX_FILE = "region_index.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

PRICE_REGEX = re.compile(r"(\$|£|€)\s?(\d+\.?\d*)")

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -----------------------------
# REGION ROTATION
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
def extract_prices(text):
    matches = PRICE_REGEX.findall(text)
    if len(matches) >= 2:
        (currency1, original), (currency2, discounted) = matches[:2]
        return original, discounted, currency1
    elif len(matches) == 1:
        (currency, discounted) = matches[0]
        return "", discounted, currency
    else:
        return "", "", ""

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def safe_request(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        return res
    except Exception as e:
        print(f"Request failed for {url}: {e}")
        return None

# -----------------------------
# SELENIUM DRIVER
# -----------------------------
def get_driver():
    options = Options()
    options.add_argument("--headless=new")  # modern headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver

# -----------------------------
# SCRAPERS
# -----------------------------
def scrape_spotify(region, lang):
    print(f"Scraping Spotify for {region}...")
    url = "https://www.spotify.com/premium/"
    res = safe_request(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    data = []

    for div in soup.find_all("div"):
        text = clean_text(div.get_text())
        if "month" in text.lower():
            original, discounted, currency = extract_prices(text)
            if discounted:
                data.append({
                    "service": "Spotify",
                    "region": region,
                    "plan_type": "Music",
                    "plan_name": text[:100],
                    "price_original": original,
                    "price_discounted": discounted,
                    "currency": currency
                })

    return data


def scrape_netflix(region, lang):
    print(f"Scraping Netflix for {region}...")
    data = []
    driver = None

    try:
        driver = get_driver()
        driver.get("https://www.netflix.com/signup")
        time.sleep(5)

        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//*[contains(text(),'$') or contains(text(),'£') or contains(text(),'€')]")
            )
        )

        for el in elements:
            text = clean_text(el.text)
            original, discounted, currency = extract_prices(text)

            if discounted:
                data.append({
                    "service": "Netflix",
                    "region": region,
                    "plan_type": "Streaming",
                    "plan_name": text[:100],
                    "price_original": original,
                    "price_discounted": discounted,
                    "currency": currency
                })

    except Exception as e:
        print(f"Netflix scraping failed: {e}")

    finally:
        if driver:
            driver.quit()

    return data


def scrape_apple(region, lang):
    print(f"Scraping Apple TV+ for {region}...")
    url = "https://www.apple.com/apple-tv-plus/"
    res = safe_request(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    data = []

    text = soup.get_text(" ", strip=True)

    for line in text.split("."):
        line = clean_text(line)
        original, discounted, currency = extract_prices(line)

        if discounted:
            data.append({
                "service": "Apple TV+",
                "region": region,
                "plan_type": "Streaming",
                "plan_name": line[:100],
                "price_original": original,
                "price_discounted": discounted,
                "currency": currency
            })

    return data


def scrape_youtube(region, lang):
    print(f"Scraping YouTube Premium for {region}...")
    data = []
    driver = None

    try:
        driver = get_driver()
        driver.get("https://www.youtube.com/premium")
        time.sleep(5)

        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//*[contains(text(),'$') or contains(text(),'£') or contains(text(),'€')]")
            )
        )

        for el in elements:
            text = clean_text(el.text)
            original, discounted, currency = extract_prices(text)

            if discounted:
                data.append({
                    "service": "YouTube Premium",
                    "region": region,
                    "plan_type": "Video+Music",
                    "plan_name": text[:100],
                    "price_original": original,
                    "price_discounted": discounted,
                    "currency": currency
                })

    except Exception as e:
        print(f"YouTube scraping failed: {e}")

    finally:
        if driver:
            driver.quit()

    return data

# -----------------------------
# MAIN
# -----------------------------
def run():
    index = get_region_index()
    region, lang = REGIONS[index]

    print("=" * 50)
    print(f"Running scraper for region: {region}")
    print("=" * 50)

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

        filename = os.path.join(
            OUTPUT_FOLDER,
            f"data_{region}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )

        df.to_csv(filename, index=False)
        print(f"\nSaved successfully: {filename}")
        print(df.head())
    else:
        print("\nNo data found for this run.")

    next_index = (index + 1) % len(REGIONS)
    save_region_index(next_index)
    print(f"Next region index saved: {next_index}")


if __name__ == "__main__":
    run()