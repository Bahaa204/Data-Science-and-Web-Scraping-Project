import time
from datetime import datetime
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from bs4 import BeautifulSoup
from Helpers import make_row, extract_segment, extract_price
import Constants, os, re

timeout = 20
max_workers = 20
output_dir = "./output"

os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, "all_platforms_latest.csv")


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

    html = None

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
            combined_text.join(" " + soup.get_text(" ", strip=True))

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
            results.append(
                make_row(
                    platform="Shahid",
                    region=region,
                    currency=None,
                    price=None,
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

    url = f"https://help.netflix.com/en/node/24926/{region["netflix_path"]}"

    html = fetch_page(url, region["lang"])

    results = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        pricing = soup.find(lambda tag: tag.name == "h3" and "Pricing" in tag.text)
        if pricing:
            plans = pricing.find_next("ul")
            if plans:
                for plan in plans.find_all("li"):
                    text = plan.get_text(strip=True)
                    match = re.search(r"(.+?):\s*([^\d\s]?)(\d+\.\d+)", text)

                    if match:
                        plan = match.group(1)
                        currency = match.group(2)
                        amount = match.group(3)

                        results.append(
                            make_row(
                                platform="Netflix",
                                region=region,
                                currency=currency,
                                price=amount,
                                plan_type=plan,
                                scraped_at=scraped_at,
                            )
                        )
    return results


def scrape_region(region):
    # scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nStarting: {region['name']}")

    rows = []
    spotify = scrape_spotify_region(region)
    apple = scrape_apple_tv_region(region)
    shahid = scrape_shahid_region(region)
    netflix = scrape_netflix(region)

    if spotify:
        rows.extend(spotify)
    if apple:
        rows.extend(apple)
    if shahid:
        rows.extend(shahid)
    if netflix:
        rows.extend(netflix)

    print(f"Finished: {region['name']}")
    return rows


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

    df.to_csv(output_file, index=False, encoding="utf-8")
    elapsed = round(time.time() - start_time, 2)

    print("\nDone.")
    # print(df.head(20))
    print(f"\nSaved At: {output_file}")
    # print(f"Spotify file: {Constants.SPOTIFY_FILE}")
    # print(f"Apple TV+ file: {Constants.APPLE_FILE}")
    # print(f"Shahid file: {Constants.SHAHID_FILE}")
    print(f"Latest rows this run: {len(df)}")
    print(f"Elapsed time: {elapsed} seconds")
    print(f"Countries attempted: {len(Constants.regions)}")
    # print(f"Run ID: {run_id}")


if __name__ == "__main__":
    main()
