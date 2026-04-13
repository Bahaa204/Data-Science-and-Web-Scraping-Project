import numpy as np, pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import sys

sys.path.insert(0, str(Path(__file__).parent))
from Helpers import load_all, NLP_OUTPUT

print("Loading shared data …")
data = load_all()
steam = data["steam"]


def top_keywords(titles, n=20):
    if len(titles) == 0:
        return pd.DataFrame({"Keyword": [], "TF-IDF Score": []})
    tv = TfidfVectorizer(
        max_features=300,
        stop_words="english",
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
    )
    mat = tv.fit_transform(titles)
    scores = np.asarray(mat.mean(axis=0)).flatten()
    v = np.array(tv.get_feature_names_out())
    idx = scores.argsort()[::-1][:n]
    return pd.DataFrame({"Keyword": v[idx], "TF-IDF Score": scores[idx].round(6)})


print("NLP: TF-IDF top 30 …")
tfidf = TfidfVectorizer(
    max_features=500,
    stop_words="english",
    ngram_range=(1, 2),
    token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
)
titles_all = steam["Title"].dropna().astype(str).tolist()
mat = tfidf.fit_transform(titles_all)
scores = np.asarray(mat.mean(axis=0)).flatten()
vocab = np.array(tfidf.get_feature_names_out())
top30_idx = scores.argsort()[::-1][:30]
pd.DataFrame(
    {"Keyword": vocab[top30_idx], "TF-IDF Score": scores[top30_idx].round(6)}
).to_csv(NLP_OUTPUT / "nlp_tfidf_top30.csv", index=False)

print("NLP: Discounted vs Full-price keywords …")
steam_nlp = steam.copy()
steam_nlp["is_discounted"] = steam_nlp["Discount"] < 0
disc_kw = top_keywords(
    steam_nlp[steam_nlp["is_discounted"]]["Title"].dropna().astype(str).tolist(), 20
)
full_kw = top_keywords(
    steam_nlp[~steam_nlp["is_discounted"]]["Title"].dropna().astype(str).tolist(), 20
)
disc_kw["Group"] = "Discounted"
full_kw["Group"] = "Full Price"
pd.concat([disc_kw, full_kw]).to_csv(
    NLP_OUTPUT / "nlp_tfidf_disc_vs_full.csv", index=False
)

print("NLP: Title features …")
sf = steam[
    ["Title", "Current Price", "Original Price", "Discount", "Region Name"]
].copy()
sf = sf[sf["Original Price"] > 0].copy()
sf["Title Length"] = sf["Title"].str.len()
sf["Word Count"] = sf["Title"].str.split().str.len()
sf["Has Number"] = sf["Title"].str.contains(r"\d", na=False).astype(int)
sf["Has Colon"] = sf["Title"].str.contains(r":", na=False).astype(int)
sf["Has Subtitle"] = sf["Has Colon"]
sf.to_csv(NLP_OUTPUT / "nlp_title_features.csv", index=False)

print("NLP: Region keywords …")
rows = []
for region, grp in steam.groupby("Region Name"):
    titles_r = grp["Title"].dropna().astype(str).tolist()
    if len(titles_r) < 5:
        continue
    kdf = top_keywords(titles_r, 15)
    kdf["Region"] = region
    rows.append(kdf)
pd.concat(rows).to_csv(NLP_OUTPUT / "nlp_region_keywords.csv", index=False)

print("NLP: Naming patterns …")
sp = steam[steam["Original Price"] > 0].copy()
sp["Has Number"] = sp["Title"].str.contains(r"\d", na=False)
sp["Has Colon"] = sp["Title"].str.contains(r":", na=False)
pattern_rows = []
for col, label in [("Has Number", "Contains Number"), ("Has Colon", "Contains Colon")]:
    for flag in [True, False]:
        g = sp[sp[col] == flag]["Original Price"].dropna()
        pattern_rows.append(
            {
                "Pattern": label,
                "Value": "Yes" if flag else "No",
                "Count": len(g),
                "Avg Price ($)": round(g.mean(), 3),
                "Median ($)": round(g.median(), 3),
                "Std Dev": round(g.std(), 3),
            }
        )
pd.DataFrame(pattern_rows).to_csv(
    NLP_OUTPUT / "nlp_naming_patterns.csv", index=False
)
print(f"\nAll NLP outputs saved to: {NLP_OUTPUT}")
