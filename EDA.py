import pandas as pd
import Constants
from scipy import stats as scipy_stats
import json
from Helpers import EDA_OUTPUT, CLEAN_DATA

from pandas import DataFrame
from typing import Any


def main():
    subs: DataFrame = pd.read_csv(CLEAN_DATA / "subscriptions_cleaned.csv")
    hourly: DataFrame = pd.read_csv(CLEAN_DATA / "hourly_wage_cleaned.csv")
    steam: DataFrame = pd.read_csv(CLEAN_DATA / "steam_games_cleaned.csv")

    subs.columns = subs.columns.str.strip()
    hourly.columns = hourly.columns.str.strip()
    steam.columns = steam.columns.str.strip()

    steam["Region Name"] = (
        steam["Region"].map(Constants.region_names).fillna(steam["Region"])
    )

    subs["plan_tier"] = (
        subs["plan_type"].map(Constants.tier_map).fillna(subs["plan_type"])
    )

    affordability: DataFrame = (
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
    affordability["hours_to_afford"] = (
        affordability["price"] / affordability["hourly_wage_usd"]
    ).round(2)

    # EDA Analysis

    print("EDA: Pearson correlation matrix …")
    corr_df: DataFrame = affordability[
        ["price", "hourly_wage_usd", "hours_to_afford"]
    ].copy()
    corr_df.columns = ["Price (USD)", "Hourly Wage (USD)", "Hours to Afford"]
    corr_matrix: DataFrame = corr_df.corr(method="pearson").round(4)
    corr_matrix.to_csv(EDA_OUTPUT / "Pearson_correlation_matrix.csv")

    print("EDA: Descriptive stats per platform …")
    desc_rows: list[dict[str, Any]] = []
    for plat, grp in affordability[affordability["price"] > 0].groupby("platform"):
        prices = grp["price"].dropna()

        desc_rows.append(
            {
                "Platform": plat,
                "Count": len(prices),
                "Mean": round(prices.mean(), 3),
                "Median": round(prices.median(), 3),
                "Std Dev": round(prices.std(), 3),
                "Min": round(prices.min(), 3),
                "Max": round(prices.max(), 3),
                "Skewness": round(scipy_stats.skew(prices), 4),
                "Kurtosis": round(scipy_stats.kurtosis(prices), 4),
            }
        )
    pd.DataFrame(desc_rows).to_csv(
        EDA_OUTPUT / "Descriptive_stats_per_platform.csv", index=False
    )

    print("EDA: IQR outlier detection …")
    iqr_data = affordability[affordability["price"] > 0].copy()
    Q1, Q3 = iqr_data["price"].quantile(0.25), iqr_data["price"].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    iqr_data["Outlier"] = iqr_data["price"].apply(
        lambda x: "Outlier" if x < lower_bound or x > upper_bound else "Normal"
    )
    iqr_data[
        ["region", "platform", "plan_tier", "price", "hourly_wage_usd", "Outlier"]
    ].to_csv(EDA_OUTPUT / "eda_iqr_outliers.csv", index=False)
    json.dump(
        {"Q1": Q1, "Q3": Q3, "IQR": IQR, "lower": lower_bound, "upper": upper_bound},
        open(EDA_OUTPUT / "eda_iqr_bounds.json", "w"),
    )

    print("EDA: Hourly wage by global quartile …")
    wage_df = affordability.drop_duplicates("region")[
        ["region", "hourly_wage_usd"]
    ].dropna()
    wage_df["Quartile"] = pd.qcut(
        wage_df["hourly_wage_usd"],
        q=4,
        labels=["Q1 (Lowest)", "Q2", "Q3", "Q4 (Highest)"],
    )
    wage_df.sort_values("hourly_wage_usd", ascending=False).to_csv(
        EDA_OUTPUT / "Hourly_wage_by_global_quartile.csv", index=False
    )
    print("\nAll outputs saved to:", EDA_OUTPUT)


if __name__ == "__main__":
    main()
