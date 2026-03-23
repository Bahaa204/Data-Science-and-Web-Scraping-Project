import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


BEARER_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjOGVhNTJiMjdlZjhkYjhkOWZmMzA4MjEyNzBhMjRjOCIsIm5iZiI6MTc3NDI2OTMxNi4wNiwic3ViIjoiNjljMTMzODRlNTExMGFmODAyYjMzZjUxIiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.YlzXU1uLoeBfJwlGRhepq5KeCPDUcjnuHCHWm-OC9oY"

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "accept": "application/json"
}


REGIONS = ["US", "LB"]


PRICE_MODEL = {
    "flatrate": 10,   
    "rent": 4,
    "buy": 12
}

def get_movies():
    url = "https://api.themoviedb.org/3/movie/popular?language=en-US&page=1"
    res = requests.get(url, headers=HEADERS)

    print("Movies status:", res.status_code)

    if res.status_code != 200:
        print(res.text)
        return []

    return res.json().get("results", [])


def get_providers(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return {}

    return res.json().get("results", {})



def extract(movie, providers):
    data = []

    title = movie.get("title")
    release_date = movie.get("release_date")

    for region in REGIONS:
        region_data = providers.get(region, {})

        for t in ["flatrate", "rent", "buy"]:
            offers = region_data.get(t, [])

            for offer in offers:
                data.append({
                    "title": title,
                    "release_date": release_date,
                    "platform": offer.get("provider_name"),
                    "type": t,
                    "price_estimated": PRICE_MODEL[t],
                    "currency": "USD" if region == "US" else "LBP",
                    "region": region
                })

    return data



def main():
    movies = get_movies()

    if not movies:
        print("❌ API problem — check your token")
        return

    all_data = []

    for movie in movies:
        providers = get_providers(movie["id"])
        extracted = extract(movie, providers)
        all_data.extend(extracted)

    df = pd.DataFrame(all_data)

    if df.empty:
        print("❌ No streaming data found")
        return

 
    comparison = df.groupby(["title", "region"])["price_estimated"].mean().unstack()

    if "US" in comparison and "LB" in comparison:
        comparison["difference"] = comparison["US"] - comparison["LB"]

   
    plt.figure()
    df.groupby("region")["price_estimated"].mean().plot(kind="bar")
    plt.title("Average Price by Region")
    plt.ylabel("USD")
    plt.savefig("region_prices.png")

    plt.figure()
    df.groupby("platform")["price_estimated"].mean().sort_values().plot(kind="barh")
    plt.title("Platform Price Comparison")
    plt.xlabel("USD")
    plt.savefig("platform_prices.png")

 
    filename = f"streaming_data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    with pd.ExcelWriter(filename) as writer:
        df.to_excel(writer, sheet_name="Raw Data", index=False)
        comparison.to_excel(writer, sheet_name="Comparison")

    print("✅ SUCCESS")
    print("📁 File saved:", filename)


if __name__ == "__main__":
    main()
