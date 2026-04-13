import pickle
import streamlit as st, pandas as pd, numpy as np
import plotly.express as px, plotly.graph_objects as go
from Helpers import load_all, ML_OUTPUT, NLP_OUTPUT, EDA_OUTPUT, _read, _json
import Constants

st.set_page_config(
    page_title="Streaming & Gaming Price Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .main{background-color:#0f1117}.block-container{padding-top:1.5rem}
  .metric-card{background:linear-gradient(135deg,#1e2130,#252a3d);border:1px solid #2e3555;
    border-radius:12px;padding:1.2rem 1.5rem;text-align:center}
  .metric-value{font-size:2rem;font-weight:700;color:#4da6ff}
  .metric-label{font-size:.85rem;color:#8892b0;margin-top:.2rem}
  .section-header{font-size:1.3rem;font-weight:700;color:#e0e6ff;margin:1.2rem 0 .8rem;
    border-left:4px solid #4da6ff;padding-left:.75rem}
  div[data-testid="stSidebarContent"]{background-color:#1a1d2e}
  .stTabs [data-baseweb="tab-list"]{gap:8px}
  .stTabs [data-baseweb="tab"]{background-color:#1e2130;border-radius:8px 8px 0 0;
    color:#8892b0;padding:8px 20px}
  .stTabs [aria-selected="true"]{background-color:#2e3555!important;color:#4da6ff!important}
  .info-box{background:#1a2340;border:1px solid #2e3555;border-radius:8px;
    padding:.9rem 1.2rem;margin-bottom:1rem;color:#8892b0;font-size:.88rem}
  .payoff-box{background:linear-gradient(135deg,#1a2e1a,#1e2130);
    border:1px solid #1DB954;border-radius:10px;padding:1rem 1.4rem;margin:.5rem 0}
</style>""",
    unsafe_allow_html=True,
)

COLORS = {
    "Spotify": "#1DB954",
    "Netflix": "#E50914",
    "Apple TV+": "#A2AAAD",
    "Shahid": "#8B5CF6",
}


# ── Load shared data ─────────────────────────────────────────
@st.cache_data
def load_shared():
    d = load_all()
    subs = d["subs"]
    subs["plan_tier"] = (
        subs["plan_type"].map(Constants.tier_map).fillna(subs["plan_type"])
    )
    aff = d["affordability"]
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
    return subs, d["hourly"], d["steam"], aff


subs, hourly, steam, affordability = load_shared()


@st.cache_data
def load_eda():
    if not EDA_OUTPUT.exists(): return None
    return {
        "corr": _read(EDA_OUTPUT, "Pearson_correlation_matrix.csv"),
        "desc": _read(EDA_OUTPUT, "Descriptive_stats_per_platform.csv"),
        "iqr": _read(EDA_OUTPUT, "eda_iqr_outliers.csv"),
        "iqr_bounds_json": _json(EDA_OUTPUT, "eda_iqr_bounds.json"),
        "wage_q": _read(EDA_OUTPUT, "Hourly_wage_by_global_quartile.csv"),
    }


@st.cache_data
def load_ml():
    if not ML_OUTPUT.exists() : return None
    return {
        "clusters": _read(ML_OUTPUT, "ml_kmeans_clusters.csv"),
        "pca_var_json": _json(ML_OUTPUT, "ml_pca_variance.json"),
        "clust_prof": _read(ML_OUTPUT, "ml_cluster_profiles.csv"),
        "reg_results": _read(ML_OUTPUT, "ml_rf_regressor_results.csv"),
        "reg_metrics_json": _json(ML_OUTPUT, "ml_rf_regressor_metrics.json"),
        "reg_imp": _read(ML_OUTPUT, "ml_rf_regressor_importances.csv"),
        "cls_results": _read(ML_OUTPUT, "ml_rf_classifier_results.csv"),
        "cls_metrics_json": _json(ML_OUTPUT, "ml_rf_classifier_metrics.json"),
        "cls_imp": _read(ML_OUTPUT, "ml_rf_classifier_importances.csv"),
        "payoff": _read(ML_OUTPUT, "ml_payoff_results.csv"),
        "payoff_meta": _json(ML_OUTPUT, "ml_payoff_meta.json"),
    }


@st.cache_data
def load_nlp():
    if not NLP_OUTPUT.exists(): return None
    return {
        "tfidf30": _read(NLP_OUTPUT, "nlp_tfidf_top30.csv"),
        "tfidf_dv": _read(NLP_OUTPUT, "nlp_tfidf_disc_vs_full.csv"),
        "title_feat": _read(NLP_OUTPUT, "nlp_title_features.csv"),
        "region_kw": _read(NLP_OUTPUT, "nlp_region_keywords.csv"),
        "naming": _read(NLP_OUTPUT, "nlp_naming_patterns.csv"),
    }


@st.cache_resource
def load_payoff_models():
    models = {}
    for k, fname in [
        ("wh", "ml_payoff_work_hours_model.pkl"),
        ("ph", "ml_payoff_play_hours_model.pkl"),
        ("bn", "ml_payoff_buynow_model.pkl"),
    ]:
        p = ML_OUTPUT / fname
        if p.exists():
            with open(p, "rb") as f:
                models[k] = pickle.load(f)
    return models


ML = load_ml()
EDA = load_eda()
NLP = load_nlp()
PAYOFF_MODELS = load_payoff_models()

ML_READY = ML is not None and all(
    v is not None for k, v in ML.items() if not k.endswith("_json")
)
EDA_READY = EDA is not None
NLP_READY = NLP is not None

PLATFORM_LIST = sorted(subs["platform"].unique().tolist())
REGION_LIST = sorted(subs["region"].unique().tolist())

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.header("Dashboard Filters")
    st.markdown("---")
    selected_platforms = st.multiselect(
        "Streaming Platforms", PLATFORM_LIST, default=PLATFORM_LIST
    )
    selected_regions = st.multiselect("Regions", REGION_LIST, default=REGION_LIST)
    steam_regions_all = sorted(steam["Region Name"].unique().tolist())
    selected_steam_regions = st.multiselect(
        "Steam Regions", steam_regions_all, default=steam_regions_all
    )
    st.markdown("---")
    if ML_READY and EDA_READY and NLP_READY:
        st.success("✅ ml_outputs loaded")
    else:
        st.warning(
            f"⚠️ Run ML/EDA/NLP scripts first  ML:{ML_READY} EDA:{EDA_READY} NLP:{NLP_READY}"
        )


subs_f = subs[
    subs["platform"].isin(selected_platforms) & subs["region"].isin(selected_regions)
]
aff_f = affordability[
    affordability["platform"].isin(selected_platforms)
    & affordability["region"].isin(selected_regions)
]
steam_f = steam[steam["Region Name"].isin(selected_steam_regions)]

st.title("Streaming & Gaming Price Dashboard")

# using markdown to display an h5 heading
st.markdown(
    "##### Global subscription pricing, Steam game deals, affordability & pay-off analysis"
)

k1, k2, k3, k4, k5 = st.columns(5)
for col, val, label in [
    (k1, f"{subs_f['region'].nunique()}", "Regions Covered"),
    (k2, f"{len(selected_platforms)}", "Platforms"),
    (k3, f"${subs_f['price'].median():.2f}", "Median Sub Price (USD)"),
    (k4, f"{steam_f['Title'].nunique()}", "Steam Titles"),
    (k5, f"{aff_f['hours_to_afford'].median():.1f}h", "Median Hours to Afford"),
]:
    with col:
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{val}</div><div class='metric-label'>{label}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "💰 Affordability",
        "🎮 Steam Pricing",
        "📊 Subscription Comparison",
        "🌍 Cross-Dataset",
        "📈 EDA",
        "🤖 ML Insights",
        "📝 NLP Analysis",
        "🔍 Game / Sub Lookup",
    ]
)

# ─── TAB 1: Affordability ─────────────────────────────────────
with tab1:
    st.markdown(
        "<div class='section-header'>Hours of Work to Afford a Subscription</div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([2, 1])
    with col1:
        top_aff = (
            aff_f.groupby(["region", "platform"])["hours_to_afford"]
            .median()
            .reset_index()
            .sort_values("hours_to_afford")
            .head(40)
        )
        fig = px.bar(
            top_aff,
            x="hours_to_afford",
            y="region",
            color="platform",
            orientation="h",
            color_discrete_map=COLORS,
            title="Most Affordable Regions",
            height=520,
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        tier_counts = aff_f["affordability_tier"].value_counts().reset_index()
        tier_counts.columns = ["Tier", "Count"]
        fig2 = px.pie(
            tier_counts,
            names="Tier",
            values="Count",
            title="Affordability Tier Distribution",
            color_discrete_sequence=[
                "#1DB954",
                "#4da6ff",
                "#F4B942",
                "#FF8C42",
                "#FF6B6B",
            ],
            hole=0.45,
            height=300,
        )
        fig2.update_layout(template="plotly_dark", paper_bgcolor="#1e2130")
        st.plotly_chart(fig2, use_container_width=True)
        plat_avg = aff_f.groupby("platform")["hours_to_afford"].median().reset_index()
        plat_avg.columns = ["Platform", "Median Hours"]
        fig3 = px.bar(
            plat_avg.sort_values("Median Hours"),
            x="Platform",
            y="Median Hours",
            color="Platform",
            color_discrete_map=COLORS,
            title="Median Hours to Afford by Platform",
            height=250,
        )
        fig3.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)
    scatter_data = aff_f.drop_duplicates(subset=["region", "platform"])
    fig4 = px.scatter(
        scatter_data,
        x="hourly_wage_usd",
        y="price",
        color="platform",
        size="hours_to_afford",
        hover_name="region",
        color_discrete_map=COLORS,
        log_x=True,
        height=450,
        title="Hourly Wage vs Subscription Price (bubble = hours to afford)",
    )
    fig4.update_layout(
        template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
    )
    st.plotly_chart(fig4, use_container_width=True)
    pivot = aff_f.pivot_table(
        index="region", columns="platform", values="hours_to_afford", aggfunc="median"
    ).dropna(how="all")
    pivot = pivot.loc[pivot.mean(axis=1).sort_values().index].head(50)
    fig5 = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn_r",
        title="Heatmap: Hours to Afford (top 50 regions)",
        height=900,
        aspect="auto",
    )
    fig5.update_layout(template="plotly_dark", paper_bgcolor="#1e2130")
    st.plotly_chart(fig5, use_container_width=True)

# ─── TAB 2: Steam Pricing ─────────────────────────────────────
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        region_summary = (
            steam_f.groupby("Region Name")
            .agg(Avg_Price=("Current Price", "mean"), Game_Count=("Title", "count"))
            .round(2)
            .reset_index()
        )
        fig = px.bar(
            region_summary.sort_values("Avg_Price"),
            x="Avg_Price",
            y="Region Name",
            orientation="h",
            color="Avg_Price",
            color_continuous_scale="Blues",
            text="Avg_Price",
            title="Average Current Price by Region",
            height=350,
        )
        fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        discounted = steam_f[steam_f["Discount"] < 0].copy()
        discounted["Discount Abs"] = discounted["Discount"].abs()
        fig2 = px.box(
            discounted,
            x="Region Name",
            y="Discount Abs",
            color="Region Name",
            title="Discount % Distribution by Region",
            height=350,
        )
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
    top_deals = (
        steam_f[steam_f["Discount"] < 0]
        .copy()
        .assign(DA=lambda d: d["Discount"].abs())
        .sort_values("DA", ascending=False)
        .drop_duplicates("Title")
        .head(20)
    )
    fig3 = px.bar(
        top_deals,
        x="DA",
        y="Title",
        color="Region Name",
        orientation="h",
        text="DA",
        title="Top 20 Discounted Steam Games",
        height=600,
    )
    fig3.update_traces(texttemplate="%{text}%", textposition="outside")
    fig3.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig3, use_container_width=True)

# ─── TAB 3: Subscription Comparison ───────────────────────────
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        pt = (
            subs_f[subs_f["price"] > 0]
            .groupby(["platform", "plan_tier"])["price"]
            .median()
            .reset_index()
        )
        pt.columns = ["Platform", "Plan Tier", "Median Price (USD)"]
        fig = px.bar(
            pt,
            x="Plan Tier",
            y="Median Price (USD)",
            color="Platform",
            barmode="group",
            color_discrete_map=COLORS,
            title="Median Price by Platform & Plan Tier",
            height=400,
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            xaxis_tickangle=-30,
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.violin(
            subs_f[subs_f["price"] > 0],
            x="platform",
            y="price",
            color="platform",
            box=True,
            points="outliers",
            color_discrete_map=COLORS,
            title="Price Distribution by Platform",
            height=400,
        )
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
    selected_platform = st.selectbox(
        "Select Platform for region breakdown", options=selected_platforms
    )
    pdata = subs_f[(subs_f["platform"] == selected_platform) & (subs_f["price"] > 0)]
    rm = pdata.groupby("region")["price"].median().reset_index()
    rm.columns = ["Region", "Median Price (USD)"]
    rm = rm.sort_values("Median Price (USD)")
    tc = pd.concat(
        [
            rm.head(15).assign(Category="Cheapest"),
            rm.tail(15).assign(Category="Most Expensive"),
        ]
    )
    fig4 = px.bar(
        tc,
        x="Median Price (USD)",
        y="Region",
        color="Category",
        orientation="h",
        color_discrete_map={"Cheapest": "#1DB954", "Most Expensive": "#FF6B6B"},
        title=f"{selected_platform} — 15 Cheapest & 15 Most Expensive Regions",
        height=600,
    )
    fig4.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig4, use_container_width=True)

# ─── TAB 4: Cross-Dataset Summary ─────────────────────────────
with tab4:
    cross = (
        aff_f.groupby("region")
        .agg(
            Avg_Sub_Price=("price", "mean"),
            Hourly_Wage=("hourly_wage_usd", "first"),
            Avg_Hours=("hours_to_afford", "mean"),
            Best_Platform=(
                "platform",
                lambda x: aff_f.loc[x.index]
                .groupby("platform")["hours_to_afford"]
                .mean()
                .idxmin(),
            ),
            Min_Hours=("hours_to_afford", "min"),
        )
        .round(2)
        .reset_index()
    )
    cross.columns = [
        "Region",
        "Avg Sub Price (USD)",
        "Hourly Wage (USD)",
        "Avg Hours to Afford",
        "Most Affordable Platform",
        "Min Hours to Afford",
    ]
    cross = cross.sort_values("Avg Hours to Afford")
    col1, col2 = st.columns(2)
    with col1:
        bp = cross["Most Affordable Platform"].value_counts().reset_index()
        bp.columns = ["Platform", "Regions"]
        fig = px.pie(
            bp,
            names="Platform",
            values="Regions",
            color="Platform",
            color_discrete_map=COLORS,
            title="Most Affordable Platform per Region",
            hole=0.5,
            height=340,
        )
        fig.update_layout(template="plotly_dark", paper_bgcolor="#1e2130")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.scatter(
            cross,
            x="Hourly Wage (USD)",
            y="Avg Hours to Afford",
            size="Avg Sub Price (USD)",
            hover_name="Region",
            color="Most Affordable Platform",
            color_discrete_map=COLORS,
            log_x=True,
            height=340,
            title="Hourly Wage vs Avg Hours to Afford",
        )
        fig2.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig2, use_container_width=True)
    t15 = cross.head(15).assign(Group="Most Affordable")
    b15 = cross.tail(15).assign(Group="Least Affordable")
    fig3 = px.bar(
        pd.concat([t15, b15]),
        x="Avg Hours to Afford",
        y="Region",
        color="Group",
        orientation="h",
        color_discrete_map={
            "Most Affordable": "#1DB954",
            "Least Affordable": "#FF6B6B",
        },
        hover_data=[
            "Hourly Wage (USD)",
            "Avg Sub Price (USD)",
            "Most Affordable Platform",
        ],
        title="Top 15 Most & Least Affordable Regions",
        height=650,
    )
    fig3.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(cross, use_container_width=True, height=500)

# ─── TAB 5: EDA ───────────────────────────────────────────────
with tab5:
    if not EDA or not EDA_READY:
        st.warning("⚠️ Run `EDA.ipynb` first, then restart the dashboard.")
        st.stop()
    st.markdown(
        "<div class='section-header'>Pearson Correlation Matrix</div>",
        unsafe_allow_html=True,
    )
    corr_raw = EDA["corr"].set_index(EDA["corr"].columns[0])
    fig_corr = go.Figure(
        data=go.Heatmap(
            z=corr_raw.values,
            x=corr_raw.columns.tolist(),
            y=corr_raw.index.tolist(),
            colorscale="RdBu",
            zmid=0,
            text=corr_raw.values.round(3),
            texttemplate="%{text}",
            textfont=dict(size=14, color="white"),
        )
    )
    fig_corr.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e2130",
        title="Pearson Correlation: Price / Hourly Wage / Hours to Afford",
        height=420,
    )
    st.plotly_chart(fig_corr, use_container_width=True)
    st.markdown(
        "<div class='section-header'>Descriptive Statistics per Platform</div>",
        unsafe_allow_html=True,
    )
    desc = EDA["desc"].copy()
    desc.columns = [
        "Platform",
        "Count",
        "Mean ($)",
        "Median ($)",
        "Std Dev",
        "Min ($)",
        "Max ($)",
        "Skewness",
        "Kurtosis",
    ]
    st.dataframe(desc, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_sk = px.bar(
            desc,
            x="Platform",
            y="Skewness",
            color="Skewness",
            color_continuous_scale="RdBu",
            title="Skewness per Platform",
            height=320,
        )
        fig_sk.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig_sk, use_container_width=True)
    with col2:
        fig_ku = px.bar(
            desc,
            x="Platform",
            y="Kurtosis",
            color="Kurtosis",
            color_continuous_scale="Viridis",
            title="Kurtosis per Platform",
            height=320,
        )
        fig_ku.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig_ku, use_container_width=True)
    st.markdown(
        "<div class='section-header'>IQR Outlier Detection</div>",
        unsafe_allow_html=True,
    )
    iqr_data = EDA["iqr"].copy()
    bounds = EDA["iqr_bounds_json"]
    lb, ub = bounds["lower"], bounds["upper"]
    n_out = (iqr_data["Outlier"] == "Outlier").sum()
    st.markdown(
        f"**IQR bounds:** Q1=`{bounds['Q1']:.2f}` | Q3=`{bounds['Q3']:.2f}` | Lower=`{lb:.2f}` | Upper=`{ub:.2f}` — **{n_out} outliers**"
    )
    fig_iqr = px.scatter(
        iqr_data,
        x="hourly_wage_usd",
        y="price",
        color="Outlier",
        symbol="Outlier",
        hover_name="region",
        color_discrete_map={"Normal": "#4da6ff", "Outlier": "#FF6B6B"},
        title="Price vs Hourly Wage — IQR Outlier Detection",
        height=480,
    )
    fig_iqr.add_hline(
        y=ub,
        line_dash="dash",
        line_color="#FF6B6B",
        annotation_text=f"Upper ({ub:.2f})",
    )
    fig_iqr.add_hline(
        y=lb,
        line_dash="dash",
        line_color="#1DB954",
        annotation_text=f"Lower ({lb:.2f})",
    )
    fig_iqr.update_layout(
        template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
    )
    st.plotly_chart(fig_iqr, use_container_width=True)
    st.markdown(
        "<div class='section-header'>Hourly Wage by Global Quartile</div>",
        unsafe_allow_html=True,
    )
    wage_df = EDA["wage_q"].copy()
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_wage = px.bar(
            wage_df,
            x="hourly_wage_usd",
            y="region",
            color="Quartile",
            orientation="h",
            color_discrete_sequence=["#FF6B6B", "#F4B942", "#4da6ff", "#1DB954"],
            title="Hourly Wage by Region (quartile coloured)",
            height=max(500, len(wage_df) * 18),
        )
        fig_wage.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_wage, use_container_width=True)
    with col2:
        qs = (
            wage_df.groupby("Quartile")["hourly_wage_usd"]
            .agg(["mean", "min", "max", "count"])
            .round(2)
            .reset_index()
        )
        qs.columns = ["Quartile", "Avg Wage", "Min", "Max", "Regions"]
        st.dataframe(qs, use_container_width=True)

# ─── TAB 6: ML Insights ───────────────────────────────────────
with tab6:
    if not ML or not ML_READY:
        st.warning("⚠️ Run `python Machine_Learning.py` first.")
        st.stop()
    # Clustering
    st.markdown(
        "<div class='section-header'>KMeans Region Clustering (k=4)</div>",
        unsafe_allow_html=True,
    )
    clusters = ML["clusters"].copy()
    pca_var = ML["pca_var_json"].get("explained_variance", [0, 0])
    clusters["Cluster"] = "Cluster " + clusters["Cluster"].astype(str)
    col1, col2 = st.columns([3, 2])
    with col1:
        fig_pca = px.scatter(
            clusters,
            x="PCA1",
            y="PCA2",
            color="Cluster",
            hover_name="region",
            hover_data={
                "avg_price": ":.2f",
                "hourly_wage": ":.2f",
                "avg_hours": ":.2f",
                "n_platforms": True,
            },
            color_discrete_sequence=px.colors.qualitative.Bold,
            height=480,
            title=f"KMeans Clusters (PC1={pca_var[0]:.1%}, PC2={pca_var[1]:.1%})",
        )
        fig_pca.update_traces(marker=dict(size=9))
        fig_pca.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig_pca, use_container_width=True)
    with col2:
        cp = ML["clust_prof"].copy()
        st.dataframe(cp, use_container_width=True)
        fig_cp = px.bar(
            cp.melt(
                id_vars="Cluster",
                value_vars=["Avg Price ($)", "Avg Wage ($)", "Avg Hours"],
            ),
            x="Cluster",
            y="value",
            color="variable",
            barmode="group",
            title="Cluster Feature Comparison",
            height=320,
        )
        fig_cp.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            legend_title="",
        )
        st.plotly_chart(fig_cp, use_container_width=True)
    # RF Regressor
    st.markdown(
        "<div class='section-header'>RF Price Predictor (Subscriptions)</div>",
        unsafe_allow_html=True,
    )
    rm = ML["reg_metrics_json"]
    rr = ML["reg_results"].copy()
    ri = ML["reg_imp"].copy()
    m1, m2 = st.columns(2)
    m1.metric("MAE", f"${rm.get('MAE','N/A')}")
    m2.metric("R²", f"{rm.get('R2','N/A')}")
    col1, col2 = st.columns(2)
    with col1:
        mn = rr[["Actual", "Predicted"]].min().min()
        mx = rr[["Actual", "Predicted"]].max().max()
        fig_ap = px.scatter(
            rr,
            x="Actual",
            y="Predicted",
            opacity=0.6,
            title="Actual vs Predicted Price",
            height=380,
        )
        fig_ap.add_shape(
            type="line",
            x0=mn,
            y0=mn,
            x1=mx,
            y1=mx,
            line=dict(color="#FF6B6B", dash="dash"),
        )
        fig_ap.update_traces(marker=dict(color="#4da6ff"))
        fig_ap.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig_ap, use_container_width=True)
    with col2:
        fig_ir = px.bar(
            ri,
            x="Importance",
            y="Feature",
            orientation="h",
            color="Importance",
            color_continuous_scale="Blues",
            title="Feature Importances",
            height=380,
        )
        fig_ir.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_ir, use_container_width=True)
    # Discount Classifier
    st.markdown(
        "<div class='section-header'>RF Discount Classifier (Steam)</div>",
        unsafe_allow_html=True,
    )
    cm = ML["cls_metrics_json"]
    cr = ML["cls_results"].copy()
    ci = ML["cls_imp"].copy()
    st.metric("Classifier Accuracy", f"{cm.get('Accuracy',0)*100:.1f}%")
    col1, col2 = st.columns(2)
    with col1:
        fig_ic = px.bar(
            ci,
            x="Importance",
            y="Feature",
            orientation="h",
            color="Importance",
            color_continuous_scale="Purples",
            title="Feature Importances — Classifier",
            height=320,
        )
        fig_ic.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_ic, use_container_width=True)
    with col2:
        conf = (
            cr.groupby(["Actual_Label", "Predicted_Label"])
            .size()
            .reset_index(name="Count")
        )
        lo = ["Full Price", "Discounted"]
        cp2 = (
            conf.pivot(index="Actual_Label", columns="Predicted_Label", values="Count")
            .fillna(0)
            .reindex(index=lo, columns=lo, fill_value=0)
        )
        fig_cf = px.imshow(
            cp2,
            text_auto=True,
            color_continuous_scale="Blues",
            title="Confusion Matrix",
            height=320,
        )
        fig_cf.update_layout(template="plotly_dark", paper_bgcolor="#1e2130")
        st.plotly_chart(fig_cf, use_container_width=True)
    # Pay-off Model
    st.markdown(
        "<div class='section-header'>🕹️ Game Purchase Pay-off Predictor</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class='info-box'>
    This model answers: <b>when does buying a game 'pay off'?</b><br>
    • <b>Work hours to afford</b> = current price ÷ your hourly wage (how long you must work to buy it)<br>
    • <b>Play hours to pay off</b> = the game's current price in dollars (at the standard $1/hour gaming value)<br>
    • <b>Buy Now vs Wait</b> = classifier trained on discount ≥ 20% or price ≤ $15 as the "worth buying now" signal
    </div>""",
        unsafe_allow_html=True,
    )
    if ML["payoff"] is not None:
        po = ML["payoff"].copy()
        pm = ML["payoff_meta"]
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Work Hours Model R²",
            f"{pm.get('metrics',{}).get('work_hours',{}).get('R2','N/A')}",
        )
        col2.metric(
            "Play Hours Model R²",
            f"{pm.get('metrics',{}).get('play_hours',{}).get('R2','N/A')}",
        )
        col3.metric(
            "Buy-Now Accuracy", f"{pm.get('metrics',{}).get('buy_now_acc',0)*100:.1f}%"
        )
        col1a, col2a = st.columns(2)
        with col1a:
            fig_wh = px.histogram(
                po,
                x="Work Hours to Afford",
                color="Region",
                nbins=40,
                title="Distribution of Work Hours to Afford (by region)",
                height=380,
            )
            fig_wh.update_layout(
                template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
            )
            st.plotly_chart(fig_wh, use_container_width=True)
        with col2a:
            fig_ph = px.scatter(
                po,
                x="Current Price ($)",
                y="Play Hours to Pay Off",
                color="Region",
                hover_name="Title",
                opacity=0.6,
                title="Current Price vs Play Hours to Pay Off",
                height=380,
            )
            fig_ph.update_layout(
                template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
            )
            st.plotly_chart(fig_ph, use_container_width=True)
        best_deals = po.sort_values("Work Hours to Afford").head(20)
        fig_bd = px.bar(
            best_deals,
            x="Work Hours to Afford",
            y="Title",
            color="Region",
            orientation="h",
            title="Top 20 Games Requiring Fewest Work Hours to Afford",
            height=550,
        )
        fig_bd.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_bd, use_container_width=True)

# ─── TAB 7: NLP Analysis ──────────────────────────────────────
with tab7:
    if not NLP or not NLP_READY:
        st.warning("⚠️ Run `python NLP_Processing.py` first.")
        st.stop()
    st.markdown(
        "<div class='section-header'>TF-IDF Top 30 Keywords</div>",
        unsafe_allow_html=True,
    )
    tf30 = NLP["tfidf30"].copy()
    fig_tf = px.bar(
        tf30.sort_values("TF-IDF Score"),
        x="TF-IDF Score",
        y="Keyword",
        orientation="h",
        color="TF-IDF Score",
        color_continuous_scale="Blues",
        title="Top 30 TF-IDF Keywords",
        height=700,
    )
    fig_tf.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_tf, use_container_width=True)
    st.markdown(
        "<div class='section-header'>Discounted vs Full-Price Keywords</div>",
        unsafe_allow_html=True,
    )
    dv = NLP["tfidf_dv"].copy()
    col1, col2 = st.columns(2)
    for grp, col, clr in [
        ("Discounted", col1, "#FF6B6B"),
        ("Full Price", col2, "#4da6ff"),
    ]:
        with col:
            sub = dv[dv["Group"] == grp].sort_values("TF-IDF Score")
            fig = px.bar(
                sub,
                x="TF-IDF Score",
                y="Keyword",
                orientation="h",
                color_discrete_sequence=[clr],
                title=f"Top Keywords — {grp}",
                height=480,
            )
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
            )
            st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "<div class='section-header'>Title Length vs Price</div>",
        unsafe_allow_html=True,
    )
    tf = NLP["title_feat"].copy()
    col1, col2 = st.columns(2)
    with col1:
        fig_tl = px.scatter(
            tf,
            x="Title Length",
            y="Original Price",
            color="Region Name",
            hover_name="Title",
            opacity=0.6,
            height=420,
            title="Title Length vs Original Price",
        )
        fig_tl.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig_tl, use_container_width=True)
    with col2:
        fig_wc = px.scatter(
            tf,
            x="Word Count",
            y="Original Price",
            color="Region Name",
            hover_name="Title",
            opacity=0.6,
            height=420,
            title="Word Count vs Original Price",
        )
        fig_wc.update_layout(
            template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
        )
        st.plotly_chart(fig_wc, use_container_width=True)
    st.markdown(
        "<div class='section-header'>Region Keyword Explorer</div>",
        unsafe_allow_html=True,
    )
    rk = NLP["region_kw"].copy()
    sel = st.selectbox("Steam Region", sorted(rk["Region"].unique()), key="nlp_region")
    kws = rk[rk["Region"] == sel].sort_values("TF-IDF Score")
    fig_rk = px.bar(
        kws,
        x="TF-IDF Score",
        y="Keyword",
        orientation="h",
        color="TF-IDF Score",
        color_continuous_scale="Teal",
        title=f"Keywords in {sel} Titles",
        height=440,
    )
    fig_rk.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e2130",
        plot_bgcolor="#1e2130",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_rk, use_container_width=True)
    st.markdown(
        "<div class='section-header'>Naming Pattern Analysis</div>",
        unsafe_allow_html=True,
    )
    nm = NLP["naming"].copy()
    col1, col2 = st.columns(2)
    with col1:
        fig_nm = px.bar(
            nm,
            x="Pattern",
            y="Avg Price ($)",
            color="Value",
            barmode="group",
            color_discrete_map={"Yes": "#4da6ff", "No": "#8892b0"},
            text="Avg Price ($)",
            title="Avg Price: Pattern Present vs Absent",
            height=360,
        )
        fig_nm.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig_nm.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            legend_title="Has Pattern?",
        )
        st.plotly_chart(fig_nm, use_container_width=True)
    with col2:
        fig_nm2 = px.bar(
            nm,
            x="Pattern",
            y="Median ($)",
            color="Value",
            barmode="group",
            color_discrete_map={"Yes": "#1DB954", "No": "#8892b0"},
            text="Median ($)",
            title="Median Price: Pattern Present vs Absent",
            height=360,
        )
        fig_nm2.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig_nm2.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            legend_title="Has Pattern?",
        )
        st.plotly_chart(fig_nm2, use_container_width=True)
    st.dataframe(nm, use_container_width=True)

# ─── TAB 8: Game / Subscription Lookup ────────────────────────
with tab8:
    st.markdown(
        "<div class='section-header'>🔍 Game or Subscription Lookup</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class='info-box'>Enter the name of a Steam game or a subscription platform.
    The dashboard will display all available information: prices across regions,
    discounts, ML pay-off prediction, and NLP features.</div>""",
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Search for a game or subscription (e.g. 'Elden Ring', 'Spotify', 'Netflix')"
    ).strip()

    if not query:
        st.info("👆 Type a game or subscription name above to get started.")
        st.stop()

    q_lower = query.lower()

    # ── Steam game match ──────────────────────────────────────
    steam_match = steam[steam["Title"].str.lower().str.contains(q_lower, na=False)]

    # ── Subscription match ────────────────────────────────────
    sub_match = subs[subs["platform"].str.lower().str.contains(q_lower, na=False)]

    # ── Pay-off model data match ──────────────────────────────
    payoff_match = None
    if ML and ML["payoff"] is not None:
        payoff_match = ML["payoff"][
            ML["payoff"]["Title"].str.lower().str.contains(q_lower, na=False)
        ]

    # ── NLP title features match ──────────────────────────────
    nlp_match = None
    if NLP and NLP["title_feat"] is not None:
        nlp_match = NLP["title_feat"][
            NLP["title_feat"]["Title"].str.lower().str.contains(q_lower, na=False)
        ]

    if len(steam_match) == 0 and len(sub_match) == 0:
        st.warning(
            f"No results found for **'{query}'**. Try a partial name or check the spelling."
        )
        st.stop()

    # ═════════ STEAM GAME RESULTS ═════════════════════════════
    if len(steam_match) > 0:
        exact = steam_match[steam_match["Title"].str.lower() == q_lower]
        display_steam = exact if len(exact) > 0 else steam_match

        game_name = display_steam["Title"].iloc[0]
        st.markdown(f"## 🎮 {game_name}")

        # Basic info row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regions Available", display_steam["Region Name"].nunique())
        c2.metric(
            "Platforms", ", ".join(display_steam["Platforms"].dropna().unique()[:3])
        )
        avg_price = display_steam["Current Price"].mean()
        c3.metric("Avg Price (all regions)", f"${avg_price:.2f}")
        max_disc = display_steam["Discount"].abs().max()
        c4.metric("Max Discount Seen", f"{max_disc:.0f}%")

        # Price across regions
        st.markdown(
            "<div class='section-header'>Price Across Regions</div>",
            unsafe_allow_html=True,
        )
        price_tbl = display_steam[
            ["Region Name", "Current Price", "Original Price", "Discount"]
        ].copy()
        price_tbl.columns = [
            "Region",
            "Current Price ($)",
            "Original Price ($)",
            "Discount (%)",
        ]
        price_tbl["Discount (%)"] = price_tbl["Discount (%)"].abs()
        price_tbl = price_tbl.sort_values("Current Price ($)")
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_pr = px.bar(
                price_tbl,
                x="Region",
                y=["Current Price ($)", "Original Price ($)"],
                barmode="group",
                title=f"{game_name} — Price by Region",
                color_discrete_sequence=["#4da6ff", "#8892b0"],
                height=350,
            )
            fig_pr.update_layout(
                template="plotly_dark", paper_bgcolor="#1e2130", plot_bgcolor="#1e2130"
            )
            st.plotly_chart(fig_pr, use_container_width=True)
        with col2:
            st.dataframe(price_tbl.reset_index(drop=True), use_container_width=True)

        # Pay-off prediction section
        st.markdown(
            "<div class='section-header'>💡 Pay-off Analysis</div>",
            unsafe_allow_html=True,
        )
        if payoff_match is not None and len(payoff_match) > 0:
            pm_game = payoff_match.copy().sort_values("Work Hours to Afford")
            st.markdown(
                """<div class='info-box'>
            <b>Work Hours to Afford</b> = how many hours you need to work (at your region's wage) to earn enough to buy this game.<br>
            <b>Play Hours to Pay Off</b> = hours of gameplay needed to 'get your money's worth' (standard: $1 value per hour of play).<br>
            <b>Recommendation</b> = model prediction: Buy Now or Wait for a better deal.
            </div>""",
                unsafe_allow_html=True,
            )
            cols = [
                "Region",
                "Current Price ($)",
                "Discount (%)",
                "Hourly Wage (USD)",
                "Work Hours to Afford",
                "Play Hours to Pay Off",
                "Savings vs Original ($)",
            ]
            st.dataframe(pm_game[cols].reset_index(drop=True), use_container_width=True)

            # Live prediction widget
            st.markdown("#### 🔮 Predict Your Personal Pay-off")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                user_wage = st.number_input(
                    "Your hourly wage (USD)",
                    min_value=0.1,
                    max_value=500.0,
                    value=10.0,
                    step=0.5,
                )
            with col_b:
                sel_region_po = st.selectbox(
                    "Your region",
                    options=sorted(payoff_match["Region"].unique()),
                    key="po_region",
                )
            with col_c:
                pass

            if PAYOFF_MODELS and "wh" in PAYOFF_MODELS:
                row = payoff_match[payoff_match["Region"] == sel_region_po]
                if len(row) > 0:
                    row = row.iloc[0]
                    meta = ML["payoff_meta"]
                    rmap = meta.get("region_map", {})
                    pmap = meta.get("platform_map", {})
                    # Build feature vector using display_steam row for platforms
                    plat_str = (
                        display_steam[display_steam["Region Name"] == sel_region_po][
                            "Platforms"
                        ]
                        .fillna("")
                        .iloc[0]
                        if len(
                            display_steam[display_steam["Region Name"] == sel_region_po]
                        )
                        > 0
                        else ""
                    )
                    feat = np.array(
                        [
                            [
                                float(row["Original Price ($)"]),
                                float(row["Discount (%)"]),
                                int(
                                    payoff_match[
                                        payoff_match["Region"] == sel_region_po
                                    ]["Days Since Release"].iloc[0]
                                ),
                                float(user_wage),
                                rmap.get(sel_region_po, 0),
                                pmap.get(plat_str, 0),
                            ]
                        ]
                    )
                    wh_pred = float(PAYOFF_MODELS["wh"].predict(feat)[0])
                    ph_pred = float(PAYOFF_MODELS["ph"].predict(feat)[0])
                    bn_pred = int(PAYOFF_MODELS["bn"].predict(feat)[0])

                    c1, c2, c3 = st.columns(3)
                    c1.markdown(
                        f"""<div class='payoff-box'>
                        <div class='metric-value'>{wh_pred:.2f}h</div>
                        <div class='metric-label'>Work hours to afford at ${user_wage}/h</div></div>""",
                        unsafe_allow_html=True,
                    )
                    c2.markdown(
                        f"""<div class='payoff-box'>
                        <div class='metric-value'>{ph_pred:.1f}h</div>
                        <div class='metric-label'>Play hours needed to pay off</div></div>""",
                        unsafe_allow_html=True,
                    )
                    verdict = "✅ Buy Now" if bn_pred == 1 else "⏳ Wait for Sale"
                    vcolour = "#1DB954" if bn_pred == 1 else "#F4B942"
                    c3.markdown(
                        f"""<div class='payoff-box' style='border-color:{vcolour}'>
                        <div class='metric-value' style='color:{vcolour}'>{verdict}</div>
                        <div class='metric-label'>ML recommendation</div></div>""",
                        unsafe_allow_html=True,
                    )
                    mins_work = wh_pred * 60
                    st.info(
                        f"💬 At **${user_wage}/hr** you'd need to work **{wh_pred:.1f} hours ({mins_work:.0f} minutes)** to afford this game in **{sel_region_po}**. "
                        f"To 'break even' on enjoyment you'd need **{ph_pred:.0f} hours of gameplay** (at $1/hr value standard)."
                    )

        # NLP features
        if nlp_match is not None and len(nlp_match) > 0:
            st.markdown(
                "<div class='section-header'>📝 NLP Title Features</div>",
                unsafe_allow_html=True,
            )
            row_nlp = nlp_match.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Title Length", f"{int(row_nlp['Title Length'])} chars")
            c2.metric("Word Count", f"{int(row_nlp['Word Count'])} words")
            c3.metric("Has Number in Title", "Yes" if row_nlp["Has Number"] else "No")
            c4.metric("Has Colon / Subtitle", "Yes" if row_nlp["Has Colon"] else "No")

    # ═════════ SUBSCRIPTION RESULTS ════════════════════════════
    if len(sub_match) > 0:
        platform_name = sub_match["platform"].iloc[0]
        st.markdown(f"## 📡 {platform_name}")

        # Key metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regions", sub_match["region"].nunique())
        c2.metric("Plans", sub_match["plan_type"].nunique())
        c3.metric("Min Price", f"${sub_match[sub_match['price']>0]['price'].min():.2f}")
        c4.metric("Max Price", f"${sub_match[sub_match['price']>0]['price'].max():.2f}")

        # Price across regions
        st.markdown(
            "<div class='section-header'>Price Across Regions</div>",
            unsafe_allow_html=True,
        )
        plan_options = sorted(sub_match["plan_type"].unique().tolist())
        sel_plan = st.selectbox(
            "Filter by plan", ["All"] + plan_options, key="lookup_plan"
        )
        sub_filtered = (
            sub_match
            if sel_plan == "All"
            else sub_match[sub_match["plan_type"] == sel_plan]
        )
        sub_filtered = sub_filtered[sub_filtered["price"] > 0].sort_values("price")

        col1, col2 = st.columns([3, 1])
        with col1:
            fig_sp = px.bar(
                sub_filtered.head(40),
                x="price",
                y="region",
                color="plan_type",
                orientation="h",
                title=f"{platform_name} — Price by Region (top 40)",
                labels={
                    "price": "Price (USD)",
                    "region": "Region",
                    "plan_type": "Plan",
                },
                color_discrete_sequence=px.colors.qualitative.Bold,
                height=500,
            )
            fig_sp.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1e2130",
                plot_bgcolor="#1e2130",
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig_sp, use_container_width=True)
        with col2:
            st.dataframe(
                sub_filtered[["region", "plan_type", "price"]]
                .rename(
                    columns={
                        "region": "Region",
                        "plan_type": "Plan",
                        "price": "Price ($)",
                    }
                )
                .reset_index(drop=True),
                use_container_width=True,
                height=480,
            )

        # Affordability for this platform
        aff_platform = affordability[affordability["platform"] == platform_name]
        if len(aff_platform) > 0:
            st.markdown(
                "<div class='section-header'>💡 Affordability (Hours to Afford)</div>",
                unsafe_allow_html=True,
            )
            aff_platform_sorted = aff_platform.sort_values("hours_to_afford")
            col1, col2 = st.columns(2)
            with col1:
                fig_ah = px.bar(
                    aff_platform_sorted.head(30),
                    x="hours_to_afford",
                    y="region",
                    color="plan_tier",
                    orientation="h",
                    title=f"{platform_name} — Most Affordable Regions",
                    labels={"hours_to_afford": "Hours to Afford", "region": "Region"},
                    height=450,
                )
                fig_ah.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#1e2130",
                    plot_bgcolor="#1e2130",
                    yaxis={"categoryorder": "total ascending"},
                )
                st.plotly_chart(fig_ah, use_container_width=True)
            with col2:
                c1, c2 = st.columns(2)
                c1.metric(
                    "Median Hours to Afford",
                    f"{aff_platform['hours_to_afford'].median():.2f}h",
                )
                c2.metric(
                    "Cheapest Region",
                    aff_platform.loc[aff_platform["price"].idxmin(), "region"],
                )
                tier_counts = (
                    aff_platform["affordability_tier"].value_counts().reset_index()
                )
                tier_counts.columns = ["Tier", "Count"]
                fig_tier = px.pie(
                    tier_counts,
                    names="Tier",
                    values="Count",
                    title="Affordability Tier Distribution",
                    color_discrete_sequence=[
                        "#1DB954",
                        "#4da6ff",
                        "#F4B942",
                        "#FF8C42",
                        "#FF6B6B",
                    ],
                    hole=0.45,
                    height=320,
                )
                fig_tier.update_layout(template="plotly_dark", paper_bgcolor="#1e2130")
                st.plotly_chart(fig_tier, use_container_width=True)
