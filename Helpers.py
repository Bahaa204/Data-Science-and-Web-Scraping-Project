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

currencies: list[str] = [
    "ARS",
    "AUD",
    "BHD",
    "BBD",
    "BRL",
    "GBP",
    "CAD",
    "XAF",
    "CLP",
    "CNY",
    "CZK",
    "DKK",
    "XCD",
    "EGP",
    "EEK",
    "EUR",
    "HKD",
    "HUF",
    "ISK",
    "INR",
    "IDR",
    "ILS",
    "JMD",
    "JPY",
    "JOD",
    "KES",
    "LVL",
    "LBP",
    "LTL",
    "MYR",
    "MXN",
    "MAD",
    "NAD",
    "NPR",
    "NZD",
    "NOK",
    "OMR",
    "PKR",
    "PAB",
    "PHP",
    "PLN",
    "QAR",
    "RON",
    "RUB",
    "SAR",
    "SGD",
    "ZAR",
    "KRW",
    "LKR",
    "SEK",
    "CHF",
    "THB",
    "TRY",
    "AED",
    "USD",
    "XOF",
]


def setup_driver() -> WebDriver:
    print("Setting up the web driver")
    options = Options()
    # options.add_argument("--headless")  # Run browser in headless mode (no GUI)
    # print("Opening in headless mode")
    options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1920,1080")
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

    response = requests.get(url)
    data = response.json()

    for country in data[1]:  # data[1] contains all countries
        countries.append(country["id"])  # Country ISO Alpha 3 Code

    return countries
