import pandas as pd
import numpy as np
import os
import shutil
import Constants
from Helpers import DATA, CLEAN_DATA

from pandas import DataFrame
from pathlib import Path

# Defining the File Paths
SUBS_IN: Path = DATA / "streaming_services.csv"
HOURLY_IN: Path = DATA / "Hourly_Rate.csv"
STEAM_IN: Path = DATA / "steam_games.csv"
CURRENCIES_IN: Path = DATA / "currencies.csv"

SUBS_OUT: Path = CLEAN_DATA / "subscriptions_cleaned.csv"
HOURLY_OUT: Path = CLEAN_DATA / "hourly_wage_cleaned.csv"
STEAM_OUT: Path = CLEAN_DATA / "steam_games_cleaned.csv"
CURRENCIES_OUT: Path = CLEAN_DATA / "currencies_cleaned.csv"

COMBINED_FILE: Path = CLEAN_DATA / "all_clean_data_combined.xlsx"

print("Loading subscriptions...")
subs = pd.read_csv(SUBS_IN)


def clean_price_string(val: str) -> float:
    if pd.isna(val) or val == "":
        return np.nan
    s = str(val).strip()
    for sym in Constants.symbols:
        s = s.replace(sym, "")
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
    s = "".join(c for c in s if c.isdigit() or c == ".")
    try:
        return float(s)
    except:
        return np.nan


def get_currency_code(row) -> str:
    curr: str = str(row["currency"]).strip()

    return Constants.mapping.get(curr, curr)


def convert_to_usd(row):
    price = row["price_local"]
    curr = row["currency_code"]
    if pd.isna(price):
        return np.nan
    if curr == "USD":
        return price
    rate = Constants.EXCHANGE_RATES.get(curr)
    return price / rate if rate else np.nan


subs["price_local"] = subs["price"].apply(clean_price_string)
subs["currency_code"] = subs.apply(get_currency_code, axis=1)

shahid = (subs["platform"] == "Shahid") & (subs["plan_type"] == "General")
subs.loc[shahid, "price_local"] = 0.0
subs.loc[shahid, "currency_code"] = "USD"

subs["price_usd"] = subs.apply(convert_to_usd, axis=1)

overrides = {
    ("Sri Lanka", "Duo"): 969 / 300,
    ("Sri Lanka", "Family"): 1260 / 300,
    ("Indonesia", "Apple TV+ Monthly"): 99000 / 15500,
    ("Taiwan", "Apple TV+ Monthly"): 250 / 32,
    ("Hong Kong", "Duo"): 98 / 7.8,
    ("Hong Kong", "Family"): 128 / 7.8,
    ("Hong Kong", "Apple TV+ Monthly"): 68 / 7.8,
}
for (region, plan), usd_val in overrides.items():
    mask = (subs["region"] == region) & (subs["plan_type"] == plan)
    subs.loc[mask, "price_usd"] = usd_val

sweden_mask = (
    (subs["platform"] == "Apple TV+")
    & (subs["region"] == "Sweden")
    & (subs["plan_type"] == "Apple TV+ Monthly")
)
if sweden_mask.any():
    subs.loc[sweden_mask, "price_usd"] = 99 / 9.36
    print(f"Fixed {sweden_mask.sum()} row(s) for Apple TV+ Sweden.")
else:
    print("Apple TV+ Sweden row not found.")

subs["price_usd"] = subs["price_usd"].round(2)
subs_clean = subs.dropna(subset=["price_usd"]).copy()
subs_clean = subs_clean[["platform", "region", "plan_type", "price_usd", "scraped_at"]]
subs_clean.rename(columns={"price_usd": "price"}, inplace=True)
subs_clean["currency"] = "USD"
subs_clean.to_csv(SUBS_OUT, index=False)
print(f"Subscriptions saved to {SUBS_OUT}")


print("\nLoading hourly wages...")
hourly = pd.read_csv(HOURLY_IN)
hourly.columns = (
    ["country_code", "hourly_wage_usd"] + list(hourly.columns[2:])
    if hourly.shape[1] > 2
    else ["country_code", "hourly_wage_usd"]
)
hourly = hourly[["country_code", "hourly_wage_usd"]].copy()
hourly["hourly_wage_usd"] = pd.to_numeric(
    hourly["hourly_wage_usd"].astype(str).str.replace("$", "").str.strip(),
    errors="coerce",
)
hourly = hourly.dropna(subset=["country_code", "hourly_wage_usd"])
hourly = hourly[hourly["hourly_wage_usd"] > 0]
hourly["hourly_wage_usd"] = hourly["hourly_wage_usd"].round(2)

hourly["country_name"] = hourly["country_code"].map(Constants.country_names)
before = len(hourly)
hourly = hourly.dropna(subset=["country_name"])
print(f"Removed {before - len(hourly)} rows with unknown country codes.")
hourly.to_csv(HOURLY_OUT, index=False)
print(f"Hourly wages saved to {HOURLY_OUT}")


print("\nLoading Steam games...")
steam = pd.read_csv(STEAM_IN, encoding="utf-8-sig")

steam = steam.dropna(subset=["Title"])
steam = steam[steam["Title"].astype(str).str.strip() != ""]
print(f"Removed rows with missing titles. Remaining rows: {len(steam)}")

steam["Title"] = steam["Title"].astype(str).str.replace("â„¢", "", regex=False)
steam["Title"] = steam["Title"].astype(str).str.replace("Â", "", regex=False)
steam["Title"] = steam["Title"].str.strip()
steam["Title"] = (
    steam["Title"].astype(str).str.encode("ascii", "ignore").str.decode("ascii")
)


def clean_price_to_usd(price_str, region):
    if pd.isna(price_str) or price_str == "":
        return np.nan
    s = str(price_str).strip()
    currency = None
    if "€" in s:
        currency = "EUR"
    elif "£" in s:
        currency = "GBP"
    elif "¥" in s:
        currency = "CNY" if region == "CN" else "JPY"
    elif "R$" in s:
        currency = "BRL"
    elif "₹" in s:
        currency = "INR"
    elif "$" in s:
        non_usd = {
            "CA": "CAD",
            "AU": "AUD",
            "NZ": "NZD",
            "HK": "HKD",
            "SG": "SGD",
            "TW": "TWD",
            "MX": "MXN",
        }
        currency = non_usd.get(region, "USD")
    else:
        currency = Constants.region_default.get(region, "USD")
    for sym in ["€", "£", "¥", "R$", "₹", "$"]:
        s = s.replace(sym, "")
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
    s = "".join(c for c in s if c.isdigit() or c == ".")
    try:
        price_num = float(s)
    except:
        return np.nan
    if currency == "USD":
        return price_num
    rate = Constants.EXCHANGE_RATES.get(currency)
    return price_num / rate if rate else np.nan


steam["Current Price"] = steam.apply(
    lambda row: clean_price_to_usd(row["Current Price"], row["Region"]), axis=1
)
steam["Original Price"] = steam.apply(
    lambda row: clean_price_to_usd(row["Original Price"], row["Region"]), axis=1
)
steam["Current Price"] = steam["Current Price"].round(2)
steam["Original Price"] = steam["Original Price"].round(2)
steam["Discount"] = pd.to_numeric(
    steam["Discount"].astype(str).str.replace("%", "").str.strip(), errors="coerce"
).fillna(0)
steam["currency"] = "USD"
steam = steam.dropna(subset=["Current Price"])
steam.to_csv(STEAM_OUT, index=False)
print(f" Steam games saved to {STEAM_OUT}")


if os.path.exists(CURRENCIES_IN):
    df_curr = pd.read_csv(CURRENCIES_IN)
    df_long = (
        df_curr.melt(var_name="currency_code", value_name="exchange_rate")
        if df_curr.shape[0] == 1
        else df_curr.copy()
    )
    if "currency_code" not in df_long.columns:
        df_long = df_long.iloc[:, :2]
        df_long.columns = ["currency_code", "exchange_rate"]
    df_long["exchange_rate"] = pd.to_numeric(
        df_long["exchange_rate"], errors="coerce"
    ).round(2)
    df_long = df_long.dropna(subset=["exchange_rate"])
    df_long = df_long[df_long["exchange_rate"] != 0].drop_duplicates(
        subset=["currency_code"]
    )
    if "USD" not in df_long["currency_code"].values:
        df_long = pd.concat(
            [pd.DataFrame({"currency_code": ["USD"], "exchange_rate": [1.0]}), df_long],
            ignore_index=True,
        )
    df_long.to_csv(CURRENCIES_OUT, index=False)
    print(f"Currencies saved to {CURRENCIES_OUT}")
else:
    clean_df = pd.DataFrame(
        [
            {"currency_code": c, "exchange_rate": round(r, 2)}
            for c, r in Constants.EXCHANGE_RATES.items()
        ]
    )
    clean_df.to_csv(CURRENCIES_OUT, index=False)
    print(f" Currencies built from internal rates and saved to {CURRENCIES_OUT}")


print("\nCombining datasets side by side...")
subs = pd.read_csv(SUBS_OUT)
steam = pd.read_csv(STEAM_OUT)

subs.columns = subs.columns.str.strip().str.lower().str.replace(" ", "_")
steam.columns = steam.columns.str.strip().str.lower().str.replace(" ", "_")


def get_col(df, *candidates):
    for c in candidates:
        if c in df.columns:
            return df[c]
    raise KeyError(f"None of {candidates} found in columns: {df.columns.tolist()}")


subs_final = pd.DataFrame(
    {
        "sub_source": "Subscriptions",
        "sub_type": "subscription_plan",
        "sub_name": subs["plan_type"],
        "sub_region": subs["region"],
        "sub_platform": subs["platform"],
        "sub_price_usd": subs["price"],
        "sub_currency": subs["currency"] if "currency" in subs.columns else "USD",
        "sub_date": subs["scraped_at"],
    }
).reset_index(drop=True)

steam_final = pd.DataFrame(
    {
        "steam_source": "Steam",
        "steam_type": "game",
        "steam_name": get_col(steam, "title"),
        "steam_region": get_col(steam, "region"),
        "steam_platform": get_col(steam, "platform", "platforms"),
        "steam_price_usd": get_col(steam, "current_price"),
        "steam_original_price_usd": get_col(steam, "original_price"),
        "steam_discount_percent": get_col(steam, "discount"),
        "steam_currency": steam["currency"] if "currency" in steam.columns else "USD",
        "steam_date": get_col(steam, "scraped_at"),
    }
).reset_index(drop=True)

combined = pd.concat([steam_final, subs_final], axis=1)

print(f"Steam rows:        {combined['steam_source'].notna().sum()}")
print(f"Subscription rows: {combined['sub_source'].notna().sum()}")
print(f"Combined shape:    {combined.shape}")

combined.to_excel(COMBINED_FILE, index=False)
print(f" Combined dataset saved as: {COMBINED_FILE}")
print(f"Steam data:        columns A-J")
print(f"Subscription data: columns K onwards")
