import pandas as pd
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from time import sleep
from Helpers import setup_driver, selectFromDropdown
import Constants


def main() -> None:
    driver = setup_driver()
    # 10 second waiting period for the elements to load
    wait_delay: int = 10
    sleep_delay: int = 3
    output_path: str = "./data/currencies.csv"
    try:
        url = "https://www.exchangerates.org.uk/currency-calculator.html"
        wait: WebDriverWait[WebDriver] = WebDriverWait(driver, wait_delay)
        driver.get(url)
        sleep(5)

        # Changing the amount to 1 USD
        amount: WebElement = wait.until(
            EC.presence_of_element_located((By.ID, "cc-amount"))
        )
        driver.execute_script("arguments[0].value='1' ", amount)

        sleep(sleep_delay)

        # Selects USD from the dropdown to be able to convert from USD to any currency
        selectFromDropdown(
            driver=driver,
            wait=wait,
            dropdown_locator=(
                By.XPATH,
                "//button[contains(@aria-controls, 'cc-from-list')]",
            ),
            dropdown_container_locator=(
                By.XPATH,
                "//div[contains(@id, 'cc-from-list')]",
            ),
            data_value="USD",
        )

        sleep(sleep_delay)

        data: dict[str, str] = {"USD": "1"}
        for currency in Constants.currencies:
            if currency == "USD":
                continue

            selectFromDropdown(
                driver=driver,
                wait=wait,
                dropdown_locator=(
                    By.XPATH,
                    "//button[contains(@aria-controls, 'cc-to-list')]",
                ),
                dropdown_container_locator=(
                    By.XPATH,
                    "//div[contains(@id, 'cc-to-list')]",
                ),
                data_value=currency,
            )

            # sleep(sleep_delay)

            results: str | None = wait.until(
                EC.presence_of_element_located((By.ID, "cc-out"))
            ).get_attribute("value")

            if results:
                print(f"1 USD = {results} {currency}")
                data[currency] = results

            sleep(sleep_delay)
        # print(data)
        df = pd.DataFrame([data])  # creates one row in the dataframe
        df.to_csv(output_path, index=False)

    except TimeoutException as error:
        print(f"Element was not found during {wait_delay} seconds. Error:\n{error}")
    except NoSuchElementException as error:
        print(f"Element does not exist. Error:\n{error}")
    # except Exception as error:
    #     print(f"An unexpected error has occurred!! Error:\n{error}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
