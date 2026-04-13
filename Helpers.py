import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
import requests
import Constants
from pathlib import Path
from pandas import DataFrame
import json

# File Paths
BASE: Path = Path(__file__).parent
DATA: Path = BASE / "data"
CLEAN_DATA: Path = BASE / "clean_data"
ANALYZED_DATA: Path = BASE / "analyzed_data"
EDA_OUTPUT: Path = BASE / "eda_outputs"
ML_OUTPUT: Path = BASE / "ml_outputs"
NLP_OUTPUT: Path = BASE / "nlp_outputs"

EDA_OUTPUT.mkdir(exist_ok=True)
ML_OUTPUT.mkdir(exist_ok=True)
NLP_OUTPUT.mkdir(exist_ok=True)


def setup_driver() -> WebDriver:
    print("Setting up the web driver")
    options = Options()
    options.add_argument("--headless")  # Run browser in headless mode (no GUI)
    print("Opening in headless mode")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    ua = UserAgent()
    options.add_argument(f"user-agent={ua.random}")  # Random User-Agent
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def selectFromDropdown(
    driver: WebDriver,
    wait: WebDriverWait[WebDriver],
    dropdown_locator: tuple[ByType, str],
    dropdown_container_locator: tuple[ByType, str],
    data_value: str,
) -> None:

    # 1. Click the dropdown
    dropdown: WebElement = wait.until(EC.element_to_be_clickable(dropdown_locator))
    # print(f"Dropdown: {dropdown}")
    dropdown.click()

    container: WebElement = wait.until(
        EC.presence_of_element_located(dropdown_container_locator)
    )

    while True:
        try:
            option: WebElement = container.find_element(
                By.CSS_SELECTOR, f"[data-value='{data_value}']"
            )
            # print(option.get_attribute("outerHTML"))
            sleep(0.5)
            option.click()
            break  # break when found
        except NoSuchElementException:
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight;",
                container,
            )
        sleep(0.2)


def GetCountries():
    countries: list[str] = []
    url = "https://api.worldbank.org/v2/country?format=json&per_page=300"

    response = requests.get(url, headers=Constants.HEADERS_BASE)
    data = response.json()

    for country in data[1]:  # data[1] contains all countries
        countries.append(country["id"])  # Country ISO Alpha 3 Code

    return countries


def extract_segment(
    text: str, keyword: str, window_before: int = 120, window_after: int = 900
):
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None
    start = max(0, idx - window_before)
    end = min(len(text), idx + len(keyword) + window_after)
    return text[start:end]


def extract_all_currency_price_pairs(text: str):
    pairs = []

    for regex in (Constants.PRICE_REGEX_BEFORE, Constants.PRICE_REGEX_AFTER):
        for match in regex.finditer(text):
            raw_currency = match.group("currency").strip()
            raw_amount = match.group("amount").strip()

            currency = raw_currency.strip()
            amount = raw_amount.strip()

            if amount is not None:
                pairs.append((currency, amount))

    unique_pairs = []
    seen = set()
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            unique_pairs.append(pair)

    return unique_pairs


def extract_price(text: str):
    pairs = extract_all_currency_price_pairs(text)

    if not pairs:
        return None, None

    currency, amount = pairs[0]  # just take first match
    return currency, amount


def make_row(
    platform,
    region,
    currency,
    price,
    plan_type,
    scraped_at,
):
    return {
        "platform": platform,
        "region": region["name"],
        "currency": currency,
        "price": price,
        "plan_type": plan_type,
        "scraped_at": scraped_at,
    }


def _read(folder: Path, name: str):
    f: Path = folder / name
    return pd.read_csv(f)


def _json(folder: Path, name: str):
    f: Path = folder / name
    return json.loads(f.read_text()) if f.exists() else {}


def load_raw() -> tuple[DataFrame, DataFrame, DataFrame]:
    """Return (subs, hourly, steam) – raw clean CSVs, columns stripped."""
    subs: DataFrame = pd.read_csv(CLEAN_DATA / "subscriptions_cleaned.csv")
    hourly: DataFrame = pd.read_csv(CLEAN_DATA / "hourly_wage_cleaned.csv")
    steam: DataFrame = pd.read_csv(CLEAN_DATA / "steam_games_cleaned.csv")

    for df in (subs, hourly, steam):
        df.columns = df.columns.str.strip()

    steam["Region Name"] = (
        steam["Region"].map(Constants.region_names).fillna(steam["Region"])
    )
    subs["plan_tier"] = (
        subs["plan_type"].map(Constants.tier_map).fillna(subs["plan_type"])
    )
    return subs, hourly, steam


def build_affordability(subs: DataFrame, hourly: DataFrame) -> DataFrame:
    """Merge subs with hourly wages and compute hours_to_afford."""
    aff: DataFrame = (
        subs[subs["price"] > 0]
        .merge(
            hourly[["country_name", "hourly_wage_usd"]],
            left_on="region",
            right_on="country_name",
            how="left",
        )
        .dropna(subset=["hourly_wage_usd"])
        .copy()
    )
    aff["hours_to_afford"] = (aff["price"] / aff["hourly_wage_usd"]).round(2)
    aff["affordability_tier"] = pd.cut(
        aff["hours_to_afford"],
        bins=[0, 1, 5, 15, 50, 9999],
        labels=[
            "<1h (Very Affordable)",
            "1-5h (Affordable)",
            "5-15h (Moderate)",
            "15-50h (Expensive)",
            ">50h (Very Expensive)",
        ],
    ).astype(str)
    return aff


def build_steam_affordability(steam: DataFrame, hourly: DataFrame) -> DataFrame:
    """Merge steam games with hourly wages by region, compute pay-off metrics."""
    steam_aff = steam.copy()
    steam_aff["country_name"] = steam_aff["Region"].map(
        Constants.STEAM_REGION_TO_COUNTRY
    )
    steam_aff = steam_aff.merge(
        hourly[["country_name", "hourly_wage_usd"]],
        on="country_name",
        how="left",
    ).dropna(subset=["hourly_wage_usd", "Current Price"])

    # work_hours_to_afford: how many hours you must work to buy the game
    steam_aff["work_hours_to_afford"] = (
        steam_aff["Current Price"] / steam_aff["hourly_wage_usd"]
    ).round(3)

    # play_hours_to_payoff: standard gaming value = $1 per hour of play
    # so payoff hours = current_price / 1 = current_price (as float)
    steam_aff["play_hours_to_payoff"] = steam_aff["Current Price"].round(2)

    # savings vs original price
    steam_aff["savings_usd"] = (
        (steam_aff["Original Price"] - steam_aff["Current Price"])
        .clip(lower=0)
        .round(2)
    )

    # discount_pct as positive number (stored as negative in raw data)
    steam_aff["discount_pct"] = steam_aff["Discount"].abs()

    # days since release (rough estimate)
    steam_aff["release_date_parsed"] = pd.to_datetime(
        steam_aff["Release Date"], format="%d %b, %Y", errors="coerce"
    )
    ref_date = pd.Timestamp("2026-04-08")
    steam_aff["days_since_release"] = (
        (ref_date - steam_aff["release_date_parsed"]).dt.days.fillna(0).astype(int)
    )

    return steam_aff


def load_all() -> dict[str, DataFrame]:
    """Convenience: load everything and return a named dict."""
    subs, hourly, steam = load_raw()
    affordability: DataFrame = build_affordability(subs, hourly)
    steam_aff = build_steam_affordability(steam, hourly)
    return {
        "subs": subs,
        "hourly": hourly,
        "steam": steam,
        "affordability": affordability,
        "steam_aff": steam_aff,
    }
