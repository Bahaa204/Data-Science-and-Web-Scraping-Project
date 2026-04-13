import requests
from Helpers import GetCountries, DATA
import pandas as pd


# Estimated work hours per year
HOURS_PER_YEAR = 2080


def get_hourly_wage(country_code: str, indicator: str):

    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&per_page=20"

    try:
        response: requests.Response = requests.get(url)
        data = response.json()

        # data[1] contains yearly records
        for entry in data[1]:
            gdp = entry["value"]
            year = entry["date"]

            if gdp == "Aggregates":
                continue

            if gdp is not None:
                hourly_wage = gdp / HOURS_PER_YEAR
                return round(hourly_wage, 2), year

        return None, None

    except Exception as e:
        print(f"Error for {country_code}: {e}")
        return None, None


def main() -> None:

    countries = GetCountries()
    indicator = "NY.GDP.PCAP.CD"
    file_path: str = DATA / "Hourly_Rate.csv"

    data = []

    for country in countries:
        wage, year = get_hourly_wage(country, indicator)

        if wage:
            print(f"{country}: {wage}/hour")
            data.append({"country": country, "Hourly Wage in $": wage, "year": year})
        else:
            print(f"{country}: No Data is available")
            data.append({"country": country, "wage": None, "year": None})

    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    print(f"Successfully saved to {file_path}")


if __name__ == "__main__":
    main()
