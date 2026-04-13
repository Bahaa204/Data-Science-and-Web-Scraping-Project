import os
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup

import Constants
from Helpers import make_row, extract_segment, extract_price, DATA
from pathlib import Path

timeout = 20
max_workers = 20

output_file = DATA / "streaming_services.csv"


def fetch_page(url: str, lang: str):
    headers = Constants.HEADERS_BASE.copy()
    headers["Accept-Language"] = lang

    try:
        response = requests.get(
            url=url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
        print(f"[{response.status_code}] {url}")
        if response.status_code == 200 and response.text:
            return response.text
        return None
    except Exception as e:
        print(f"[ERROR] {url} -> {e}")
        return None


def scrape_spotify_region(region):
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    url = f"https://www.spotify.com/{region['spotify_path']}/premium/"
    html = fetch_page(url, region["lang"])

    results = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for plan_id in Constants.PLAN_KEYWORDS:
            plan_tag = soup.select_one(f"#plan-premium-{plan_id}")
            if plan_tag:
                text = plan_tag.get_text(" ", strip=True)
                title_tag = plan_tag.find(["h1", "h2", "h3", "h4"])
                title = title_tag.get_text().strip() if title_tag else plan_id.title()

                currency, price = extract_price(text)

                results.append(
                    make_row(
                        platform="Spotify",
                        region=region,
                        currency=currency,
                        price=price,
                        plan_type=title,
                        scraped_at=scraped_at,
                    )
                )

    return results


def scrape_apple_tv_region(region):
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    urls = [
        f"https://tv.apple.com/{region['apple_path']}",
        f"https://www.apple.com/{region['apple_path']}/apple-tv/",
        f"https://www.apple.com/{region['apple_path']}/apple-tv-plus/",
    ]

    for url in urls:
        html = fetch_page(url, region["lang"])

        if html:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ", strip=True)

            currency, price = extract_price(text)

            if price is not None:
                return [
                    make_row(
                        platform="Apple TV+",
                        region=region,
                        currency=currency,
                        price=price,
                        plan_type="Apple TV+ Monthly",
                        scraped_at=scraped_at,
                    )
                ]

    return []


def scrape_shahid_region(region):
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    urls = [
        "https://shahid.mbc.net/en/hub/promo/SHAHID_VIP",
        "https://shahid.mbc.net/en/hub/promo/SHAHID_VIP_GEA",
        "https://shahid.mbc.net/en/hub/promo",
        "https://help.shahid.mbc.net/s/article/Plans-Packages",
    ]

    combined_text = ""

    for url in urls:
        html = fetch_page(url, region["lang"])
        if html:
            soup = BeautifulSoup(html, "html.parser")
            combined_text += " " + soup.get_text(" ", strip=True)

    results = []
    labels = [
        "VIP | BigTime",
        "VIP Mobile",
        "VIP | Sports",
        "Ultimate | GoBX",
        "SPORTS | GoBX",
        "Ultimate",
        "VIP",
        "Sports",
        "Mobile",
        "Free",
    ]

    for label in labels:
        segment = extract_segment(combined_text, label, 120, 900)
        if segment:
            currency, price = extract_price(segment)
            results.append(
                make_row(
                    platform="Shahid",
                    region=region,
                    currency=currency,
                    price=price,
                    plan_type=label,
                    scraped_at=scraped_at,
                )
            )

    if not results:
        results.append(
            make_row(
                platform="Shahid",
                region=region,
                currency=None,
                price=None,
                plan_type="General",
                scraped_at=scraped_at,
            )
        )

    return results


def scrape_netflix(region):
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    url = f"https://help.netflix.com/en/node/24926/{region['netflix_path']}"
    html = fetch_page(url, region["lang"])

    results = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        plan_patterns = [
            r"(Premium)\s*[:\-]?\s*([^\d\s]{0,4}|[A-Z]{2,4})?\s*(\d+(?:[.,]\d{1,2})?)",
            r"(Standard with ads)\s*[:\-]?\s*([^\d\s]{0,4}|[A-Z]{2,4})?\s*(\d+(?:[.,]\d{1,2})?)",
            r"(Standard)\s*[:\-]?\s*([^\d\s]{0,4}|[A-Z]{2,4})?\s*(\d+(?:[.,]\d{1,2})?)",
            r"(Basic)\s*[:\-]?\s*([^\d\s]{0,4}|[A-Z]{2,4})?\s*(\d+(?:[.,]\d{1,2})?)",
        ]

        seen = set()
        for pattern in plan_patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                plan_name = match.group(1).strip()
                currency = match.group(2).strip() if match.group(2) else None
                amount = match.group(3).strip()

                key = (plan_name.lower(), currency, amount)
                if key in seen:
                    continue
                seen.add(key)

                results.append(
                    make_row(
                        platform="Netflix",
                        region=region,
                        currency=currency,
                        price=amount,
                        plan_type=plan_name,
                        scraped_at=scraped_at,
                    )
                )

    return results


def scrape_region(region):
    print(f"\nStarting: {region['name']}")
    rows = []

    for scraper in [
        scrape_spotify_region,
        scrape_apple_tv_region,
        scrape_shahid_region,
        scrape_netflix,
    ]:
        try:
            result = scraper(region)
            if result:
                rows.extend(result)
        except Exception as e:
            print(f"[SCRAPER ERROR] {region['name']} - {scraper.__name__}: {e}")

    print(f"Finished: {region['name']}")
    return rows


def append_to_csv(df: pd.DataFrame, filepath: Path):
    if df.empty:
        print("No new rows to save.")
        return

    file_exists = os.path.exists(filepath)

    if file_exists:
        try:
            existing_df = pd.read_csv(filepath)
            df = pd.concat([existing_df, df], ignore_index=True)
            df.to_csv(filepath, index=False, encoding="utf-8")
            print(f"Appended new data to existing file: {filepath}")
        except Exception as e:
            print(f"[CSV ERROR] Could not append safely: {e}")
            print("Saving current run only as fallback.")
            df.to_csv(filepath, index=False, encoding="utf-8")
    else:
        df.to_csv(filepath, index=False, encoding="utf-8")
        print(f"Created new file: {filepath}")


def main():
    start_time = time.time()
    all_rows = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(scrape_region, region) for region in Constants.regions
        ]

        for future in as_completed(futures):
            try:
                region_rows = future.result()
                all_rows.extend(region_rows)
            except Exception as e:
                print(f"[THREAD ERROR] {e}")

    df = pd.DataFrame(all_rows)

    append_to_csv(df, output_file)

    elapsed = round(time.time() - start_time, 2)

    print("\nDone.")
    print(f"Saved At: {output_file}")
    print(f"New rows this run: {len(pd.DataFrame(all_rows))}")
    print(f"Elapsed time: {elapsed} seconds")
    print(f"Countries attempted: {len(Constants.regions)}")


if __name__ == "__main__":
    main()
