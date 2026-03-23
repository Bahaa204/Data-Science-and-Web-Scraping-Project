import requests
from Helpers import GetCountries

countries = GetCountries()
indicator = "NY.GDP.PCAP.CD"

# Estimated work hours per year
HOURS_PER_YEAR = 2080


def get_hourly_wage(country_code):
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


for country in countries:
    wage, year = get_hourly_wage(country)

    if wage:
        print(f"{country}: ${wage}/hour (based on {year})")
    else:
        print(f"{country}: No data available")
