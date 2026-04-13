import os
import time
import threading
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Helpers import setup_driver, DATA


lock = threading.Lock()

# Steam uses the 'steamCountry' cookie to enforce currency.
# Without it, Steam may fall back to USD or another default.
COUNTRY_COOKIES = {
    "DE": {
        "name": "steamCountry",
        "value": "DE%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
    "GB": {
        "name": "steamCountry",
        "value": "GB%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
    "US": {
        "name": "steamCountry",
        "value": "US%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
    "BR": {
        "name": "steamCountry",
        "value": "BR%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
    "IN": {
        "name": "steamCountry",
        "value": "IN%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
    "TR": {
        "name": "steamCountry",
        "value": "TR%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
    "CN": {
        "name": "steamCountry",
        "value": "CN%7C7a5a7f9d8e4b3c2a1f0e9d8c7b6a5f4e",
        "domain": "store.steampowered.com",
    },
}


def scrape_tab(driver, handle, url):
    country_code = url.split("cc=")[-1].split("&")[0].upper()
    region_name = country_code
    games_list = []

    try:
        # Navigate to Steam domain first so we can set cookies, then inject currency cookie
        with lock:
            driver.switch_to.window(handle)
            driver.get("https://store.steampowered.com")
            if country_code in COUNTRY_COOKIES:
                driver.add_cookie(COUNTRY_COOKIES[country_code])
            driver.get(url)

        scroll_pause_time = 2
        target_item_count = 300
        last_count = 0
        stall_attempts = 0
        max_stall_attempts = 3

        while True:
            with lock:
                driver.switch_to.window(handle)
                current_count = len(
                    driver.find_elements(By.CLASS_NAME, "search_result_row")
                )

            if current_count >= target_item_count:
                break

            if current_count == last_count:
                stall_attempts += 1
                if stall_attempts >= max_stall_attempts:
                    print(
                        f"[{region_name}] Stalled at {current_count} results, moving on."
                    )
                    break
            else:
                stall_attempts = 0

            last_count = current_count

            with lock:
                driver.switch_to.window(handle)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)

        with lock:
            driver.switch_to.window(handle)
            rows = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "search_result_row")
                )
            )
            row_data = []
            for row in rows:
                try:
                    title = row.find_element(By.CLASS_NAME, "title").text
                    platforms_div = row.find_element(By.CLASS_NAME, "search_platforms")
                    platform_tags = platforms_div.find_elements(By.TAG_NAME, "span")
                    platforms = [
                        p.get_attribute("class").split()[-1]
                        for p in platform_tags
                        if "platform_img" in p.get_attribute("class")
                    ]
                    release_date = row.find_element(
                        By.CLASS_NAME, "search_released"
                    ).text
                    discount_pct_elements = row.find_elements(
                        By.CLASS_NAME, "discount_pct"
                    )
                    if (
                        discount_pct_elements
                        and discount_pct_elements[0].text.strip() != ""
                    ):
                        discount_pct = discount_pct_elements[0].text
                        original_price = row.find_element(
                            By.CLASS_NAME, "discount_original_price"
                        ).text
                        final_price = row.find_element(
                            By.CLASS_NAME, "discount_final_price"
                        ).text
                    else:
                        discount_pct = "0%"
                        price_elements = row.find_elements(
                            By.CLASS_NAME, "discount_final_price"
                        )
                        final_price = (
                            price_elements[0].text if price_elements else "N/A"
                        )
                        original_price = final_price
                    row_data.append(
                        (
                            title,
                            platforms,
                            release_date,
                            final_price,
                            original_price,
                            discount_pct,
                        )
                    )
                except Exception:
                    continue

        for (
            title,
            platforms,
            release_date,
            final_price,
            original_price,
            discount_pct,
        ) in row_data:
            games_list.append(
                {
                    "Region": region_name,
                    "Title": title,
                    "Platforms": ", ".join(platforms),
                    "Release Date": release_date,
                    "Current Price": final_price,
                    "Original Price": original_price,
                    "Discount": discount_pct,
                    "Scraped At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        print(f"[{region_name}] Scraped {len(games_list)} games.")

    except Exception as e:
        print(f"[{region_name}] Failed: {e}")

    return games_list


urls = [
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=de&l=english",
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=gb&l=english",
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=us&l=english",
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=br&l=english",
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=in&l=english",
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=tr&l=english",
    "https://store.steampowered.com/search/?category1=998&hidef2p=1&cc=cn&l=english",
]


def main() -> None:

    driver: WebDriver = setup_driver()

    try:
        handles = []
        for i, url in enumerate(urls):
            if i == 0:
                handles.append(driver.current_window_handle)
            else:
                driver.execute_script("window.open('');")
                handles.append(driver.window_handles[-1])

        print(f"Opened {len(handles)} tabs. Starting scrape...")

        all_games = []
        with ThreadPoolExecutor(max_workers=len(urls)) as executor:
            futures = {
                executor.submit(scrape_tab, driver, handle, url): url
                for handle, url in zip(handles, urls)
            }
            for future in as_completed(futures):
                all_games.extend(future.result())

    finally:
        driver.quit()

    df = pd.DataFrame(all_games)
    filename = DATA / "steam_games.csv"
    df.to_csv(filename, mode="a", index=False, encoding="utf-8-sig")
    print(f"\nDone. {len(all_games)} total records saved/appended to {filename}")


if __name__ == "__main__":
    main()
