import json, pickle
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    GradientBoostingRegressor,
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score
from Helpers import load_all, ML_OUTPUT


def main():
    print("Loading shared data …")
    data = load_all()
    subs = data["subs"]
    hourly = data["hourly"]
    steam = data["steam"]
    affordability = data["affordability"]
    steam_aff = data["steam_aff"]

    # ── Model 1: KMeans + PCA ─────────────────────────────────────
    print("\nML: KMeans region clustering …")
    region_features = (
        affordability.groupby("region")
        .agg(
            avg_price=("price", "mean"),
            median_price=("price", "median"),
            hourly_wage=("hourly_wage_usd", "first"),
            avg_hours=("hours_to_afford", "mean"),
            price_std=("price", "std"),
            n_platforms=("platform", "nunique"),
        )
        .fillna(0)
        .reset_index()
    )

    feature_cols = [
        "avg_price",
        "median_price",
        "hourly_wage",
        "avg_hours",
        "price_std",
        "n_platforms",
    ]

    X = region_features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    region_features["Cluster"] = km.fit_predict(X_scaled).astype(str)
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    region_features["PCA1"] = X_pca[:, 0]
    region_features["PCA2"] = X_pca[:, 1]
    region_features.to_csv(ML_OUTPUT / "ml_kmeans_clusters.csv", index=False)

    json.dump(
        {"explained_variance": pca.explained_variance_ratio_.tolist()},
        open(ML_OUTPUT / "ml_pca_variance.json", "w"),
    )
    cp = (
        region_features.groupby("Cluster")
        .agg(
            Regions=("region", "count"),
            Avg_Price=("avg_price", "mean"),
            Avg_Wage=("hourly_wage", "mean"),
            Avg_Hours=("avg_hours", "mean"),
            Platforms=("n_platforms", "mean"),
        )
        .round(3)
        .reset_index()
    )
    cp.columns = [
        "Cluster",
        "Regions",
        "Avg Price ($)",
        "Avg Wage ($)",
        "Avg Hours",
        "Avg Platforms",
    ]
    cp.to_csv(ML_OUTPUT / "ml_cluster_profiles.csv", index=False)
    print(f"  {len(region_features)} regions clustered.")

    # ── Model 2: RF Price Regressor (subscriptions) ───────────────
    print("\nML: RF subscription price predictor …")
    df_rf = affordability[affordability["price"] > 0].copy()
    df_rf["platform_enc"] = df_rf["platform"].astype("category").cat.codes
    df_rf["tier_enc"] = df_rf["plan_tier"].astype("category").cat.codes
    reg_features = ["hourly_wage_usd", "platform_enc", "tier_enc"]
    X_r = df_rf[reg_features].dropna()
    y_r = df_rf.loc[X_r.index, "price"]
    Xtr, Xte, ytr, yte = train_test_split(X_r, y_r, test_size=0.25, random_state=42)
    rfr = RandomForestRegressor(n_estimators=150, random_state=42)
    rfr.fit(Xtr, ytr)
    yp = rfr.predict(Xte)
    mae_r = round(mean_absolute_error(yte, yp), 4)
    r2_r = round(r2_score(yte, yp), 4)
    json.dump(
        {"MAE": mae_r, "R2": r2_r},
        open(ML_OUTPUT / "ml_rf_regressor_metrics.json", "w"),
    )
    pd.DataFrame({"Actual": yte.values, "Predicted": yp.round(3)}).to_csv(
        ML_OUTPUT / "ml_rf_regressor_results.csv", index=False
    )
    pd.DataFrame(
        {"Feature": reg_features, "Importance": rfr.feature_importances_.round(5)}
    ).sort_values("Importance", ascending=False).to_csv(
        ML_OUTPUT / "ml_rf_regressor_importances.csv", index=False
    )
    print(f"  MAE=${mae_r}  R²={r2_r}")

    # ── Model 3: RF Discount Classifier (Steam) ───────────────────
    print("\nML: RF discount classifier …")
    df_cls = steam.copy()
    df_cls["is_discounted"] = (df_cls["Discount"] < 0).astype(int)
    df_cls["region_enc"] = df_cls["Region Name"].astype("category").cat.codes
    df_cls["platform_enc"] = df_cls["Platforms"].fillna("").astype("category").cat.codes
    df_cls["orig_price"] = df_cls["Original Price"].fillna(
        df_cls["Original Price"].median()
    )
    cls_features = ["orig_price", "region_enc", "platform_enc"]
    X_c = df_cls[cls_features].dropna()
    y_c = df_cls.loc[X_c.index, "is_discounted"]
    Xtr2, Xte2, ytr2, yte2 = train_test_split(X_c, y_c, test_size=0.25, random_state=42)
    rfc = RandomForestClassifier(n_estimators=150, random_state=42)
    rfc.fit(Xtr2, ytr2)
    ypc = rfc.predict(Xte2)
    acc_c = round(accuracy_score(yte2, ypc), 5)
    json.dump(
        {"Accuracy": acc_c}, open(ML_OUTPUT / "ml_rf_classifier_metrics.json", "w")
    )
    rc = pd.DataFrame(
        {
            "Actual": yte2.values,
            "Predicted": ypc,
            "Actual_Label": pd.Series(yte2.values).map(
                {1: "Discounted", 0: "Full Price"}
            ),
            "Predicted_Label": pd.Series(ypc).map({1: "Discounted", 0: "Full Price"}),
        }
    )
    rc["Correct"] = (rc["Actual"] == rc["Predicted"]).map(
        {True: "Correct", False: "Wrong"}
    )
    rc.to_csv(ML_OUTPUT / "ml_rf_classifier_results.csv", index=False)
    pd.DataFrame(
        {"Feature": cls_features, "Importance": rfc.feature_importances_.round(5)}
    ).sort_values("Importance", ascending=False).to_csv(
        ML_OUTPUT / "ml_rf_classifier_importances.csv", index=False
    )
    print(f"  Accuracy: {acc_c*100:.1f}%")

    # ── Model 4: Game Purchase Pay-off Predictor (NEW) ────────────
    print("\nML: Game Purchase Pay-off Predictor …")
    df_po = steam_aff[steam_aff["Current Price"] > 0].copy()
    df_po["region_enc"] = df_po["Region"].astype("category").cat.codes
    df_po["platform_enc"] = df_po["Platforms"].fillna("").astype("category").cat.codes
    payoff_features = [
        "Original Price",
        "discount_pct",
        "days_since_release",
        "hourly_wage_usd",
        "region_enc",
        "platform_enc",
    ]
    X_po = df_po[payoff_features].dropna()

    # 4a: predict work_hours_to_afford
    y_wh = df_po.loc[X_po.index, "work_hours_to_afford"]
    Xtr3, Xte3, ytr3, yte3 = train_test_split(
        X_po, y_wh, test_size=0.25, random_state=42
    )
    gbr_wh = GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
    )
    gbr_wh.fit(Xtr3, ytr3)
    yp_wh = gbr_wh.predict(Xte3)
    mae_wh = round(mean_absolute_error(yte3, yp_wh), 4)
    r2_wh = round(r2_score(yte3, yp_wh), 4)
    print(f"  work_hours MAE={mae_wh}h  R²={r2_wh}")

    # 4b: predict play_hours_to_payoff
    y_ph = df_po.loc[X_po.index, "play_hours_to_payoff"]
    Xtr4, Xte4, ytr4, yte4 = train_test_split(
        X_po, y_ph, test_size=0.25, random_state=42
    )
    gbr_ph = GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
    )
    gbr_ph.fit(Xtr4, ytr4)
    yp_ph = gbr_ph.predict(Xte4)
    mae_ph = round(mean_absolute_error(yte4, yp_ph), 4)
    r2_ph = round(r2_score(yte4, yp_ph), 4)
    print(f"  play_hours MAE={mae_ph}h  R²={r2_ph}")

    # 4c: Buy Now vs Wait classifier
    df_po["buy_now"] = (
        (df_po["discount_pct"] >= 20) | (df_po["Original Price"] <= 15)
    ).astype(int)
    y_bn = df_po.loc[X_po.index, "buy_now"]
    Xtr5, Xte5, ytr5, yte5 = train_test_split(
        X_po, y_bn, test_size=0.25, random_state=42
    )
    rfc_bn = RandomForestClassifier(n_estimators=150, random_state=42)
    rfc_bn.fit(Xtr5, ytr5)
    yp_bn = rfc_bn.predict(Xte5)
    acc_bn = round(accuracy_score(yte5, yp_bn), 5)
    print(f"  buy_vs_wait accuracy={acc_bn*100:.1f}%")

    # Save models
    for fname, model in [
        ("ml_payoff_work_hours_model.pkl", gbr_wh),
        ("ml_payoff_play_hours_model.pkl", gbr_ph),
        ("ml_payoff_buynow_model.pkl", rfc_bn),
    ]:
        with open(ML_OUTPUT / fname, "wb") as f:
            pickle.dump(model, f)

    # Build region/platform encoding maps for live inference
    region_cats = df_po["Region"].astype("category").cat.categories.tolist()
    platform_cats = (
        df_po["Platforms"].fillna("").astype("category").cat.categories.tolist()
    )
    payoff_meta = {
        "features": payoff_features,
        "region_map": {cat: i for i, cat in enumerate(region_cats)},
        "platform_map": {cat: i for i, cat in enumerate(platform_cats)},
        "metrics": {
            "work_hours": {"MAE": mae_wh, "R2": r2_wh},
            "play_hours": {"MAE": mae_ph, "R2": r2_ph},
            "buy_now_acc": acc_bn,
        },
    }
    json.dump(payoff_meta, open(ML_OUTPUT / "ml_payoff_meta.json", "w"), indent=2)

    # Save per-game results table for dashboard lookup
    payoff_results = df_po[
        [
            "Region Name",
            "Title",
            "Current Price",
            "Original Price",
            "discount_pct",
            "hourly_wage_usd",
            "work_hours_to_afford",
            "play_hours_to_payoff",
            "savings_usd",
            "days_since_release",
        ]
    ].copy()
    payoff_results.columns = [
        "Region",
        "Title",
        "Current Price ($)",
        "Original Price ($)",
        "Discount (%)",
        "Hourly Wage (USD)",
        "Work Hours to Afford",
        "Play Hours to Pay Off",
        "Savings vs Original ($)",
        "Days Since Release",
    ]
    payoff_results = payoff_results.round(2)
    payoff_results.to_csv(ML_OUTPUT / "ml_payoff_results.csv", index=False)
    print(f"  Saved pay-off data for {payoff_results['Title'].nunique()} games.")
    print(f"\nAll ML outputs saved to: {ML_OUTPUT}")


if __name__ == "__main__":
    main()
