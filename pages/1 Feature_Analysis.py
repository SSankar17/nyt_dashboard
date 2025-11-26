#!/usr/bin/env python
# coding: utf-8

# Which attributes of books have the strongest association with rank on the NYT bestsellers list? | Kelly Lyons
# Install dependencies inside Streamlit environment
import subprocess
import sys
import statsmodels.api as sm
import altair as alt



subprocess.run([sys.executable, "-m", "pip", "install", "textblob"], check=True)

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from textblob import TextBlob  # Requires: pip install textblob

# Attribute list (shown BEFORE analysis)
BASE_FEATURES = [
    "rank_last_week",
    "weeks_on_list",
    "days_since_publication",
    "sentiment_score",
    "subjectivity",
    "author_popularity",
    "publisher_strength",
    "holiday_release",
    "title_length",
    "description_length",
    "genre_*  (created during analysis)"
]


#load data
def load_data(uploaded_file):
    if uploaded_file is not None:
        return pd.read_json(uploaded_file)
    return pd.read_json("books_historical (1).json")  # fallback


# Feature Engineering + OLS Model

def prepare_and_model(df):
    df["description"] = df["description"].fillna("").astype(str)
    df["sentiment_score"] = df["description"].apply(lambda txt: TextBlob(txt).sentiment.polarity)

    df["bestsellers_date"] = pd.to_datetime(df["bestsellers_date"])
    df["published_date"] = pd.to_datetime(df["published_date"])
    df["days_since_publication"] = (df["bestsellers_date"] - df["published_date"]).dt.days

    df["author_popularity"] = df["author"].map(df["author"].value_counts())
    df["publisher_strength"] = df["publisher"].map(df["publisher"].value_counts())

    def extract_genre(text):
        text = str(text).lower()
        if "murder" in text or "crime" in text or "detective" in text: return "crime"
        if "love" in text or "romance" in text: return "romance"
        if "fantasy" in text or "dragon" in text or "magic" in text: return "fantasy"
        if "war" in text: return "war"
        if "histor" in text: return "historical"
        return "other"

    df["genre"] = df["description"].apply(extract_genre)
    df = pd.get_dummies(df, columns=["genre"], drop_first=True)

    df["published_month"] = df["published_date"].dt.month
    df["holiday_release"] = df["published_month"].apply(lambda m: 1 if m in [10, 11, 12] else 0)
    df["title_length"] = df["title"].apply(lambda x: len(str(x)))
    df["description_length"] = df["description"].apply(lambda x: len(str(x)))
    df["subjectivity"] = df["description"].apply(lambda x: TextBlob(x).sentiment.subjectivity)

    feature_cols = [
        "rank_last_week", "weeks_on_list", "days_since_publication",
        "sentiment_score", "subjectivity", "author_popularity",
        "publisher_strength", "holiday_release", "title_length",
        "description_length"
    ] + [col for col in df.columns if col.startswith("genre_")]

    df_model = df[["rank"] + feature_cols].dropna()
    df_model_num = df_model.apply(pd.to_numeric, errors="coerce").dropna()

    X = df_model_num[feature_cols].astype(float)
    y = df_model_num["rank"].astype(float)

    X_ols = sm.add_constant(X)
    ols_model = sm.OLS(y, X_ols).fit()

    coef_pval = pd.DataFrame({"coef": ols_model.params, "p_value": ols_model.pvalues})
    sig_df = coef_pval[(coef_pval["p_value"] < 0.05) & (coef_pval.index != "const")]

    df_model_num["predicted_rank"] = ols_model.predict(X_ols)

    return df, df_model_num, feature_cols, ols_model, sig_df


# BAR CHART OF SIGNIFICANT COEFFICIENTS 
def plot_significant_coefficients(sig_df):
    if sig_df.empty:
        st.warning("No statistically significant predictors found.")
        return

    sig_df_sorted = sig_df.sort_values("coef").reset_index().rename(columns={"index": "Feature"})
    
    chart = alt.Chart(sig_df_sorted).mark_bar().encode(
        y=alt.Y('Feature', sort='-x'),
        x=alt.X('coef', title='Coefficient (Effect on Rank)'),
        color=alt.condition(
            alt.datum.coef > 0,
            alt.value("#8FB9C9"),  # positive effect
            alt.value("#F7C6A5")   # negative effect
        ),
        tooltip=['Feature', 'coef', 'p_value']
    ).properties(
        width=600,
        height=400,
        title="Statistically Significant Predictors of Bestseller Rank"
    )

    st.altair_chart(chart, use_container_width=True)



# Line Graph — Rolling Error Trend
def plot_error_trend(df_model_num):
    df_plot = df_model_num.sort_values("rank").reset_index(drop=True)
    df_plot["abs_error"] = np.abs(df_plot["rank"] - df_plot["predicted_rank"])
    df_plot["index"] = df_plot.index + 1

    df_melt = df_plot.melt(
        id_vars=['index'],
        value_vars=['predicted_rank', 'abs_error'],  # only orange and green
        var_name='Metric',
        value_name='Value'
    )

    color_scale = alt.Scale(
        domain=['rank', 'predicted_rank', 'abs_error'],
        range=['#1e90ff', '#F7C6A5', '#8FD1B3']  # blue, orange, green
    )
    base_chart = alt.Chart(df_melt).mark_line().encode(
        x='index',
        y='Value',
        color=alt.Color('Metric:N', scale=color_scale, title='Metric'),
        tooltip=['Metric', 'Value']
    )
    # Blue line on top
    blue_line = alt.Chart(df_plot).mark_line(color='#1f77b4', strokeWidth=3).encode(
        x='index',
        y='rank',
        tooltip=['rank']
    )

    chart = alt.layer(base_chart, blue_line).properties(
        width=700,
        height=400,
        title="Model Captures Central Trend but Struggles with Top Performers"
    ).configure_title(
        fontSize=16,
        anchor='start',
        font='sans-serif'
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14,
        labelFont='sans-serif',
        titleFont='sans-serif'
    ).configure_legend(
        titleFontSize=14,
        labelFontSize=12
    )

    st.altair_chart(chart, use_container_width=True)

# STREAMLIT APP
def main():
    st.title("Which attributes of books predict NYT Bestseller ranking?")
    st.write("**Author: Kelly Lyons**")

    # view of features (BEFORE analysis runs)
    st.sidebar.header("Attributes Being Tested")
    st.sidebar.write(BASE_FEATURES)

    st.sidebar.header("Upload Data")
    uploaded_file = st.sidebar.file_uploader("Upload `books_historical (1).json`", type=["json"])

    try:
        df = load_data(uploaded_file)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    st.subheader("Preview of Dataset")
    st.dataframe(df.head())

    if st.button("Run Analysis"):
        with st.spinner("Preparing features and running regression..."):
            df, df_model_num, feature_cols, ols_model, sig_df = prepare_and_model(df)

        st.subheader("Final Attributes Used in the Model")
        st.write(feature_cols)

        st.subheader("OLS Regression Summary")
        ols_table = ols_model.summary2().tables[1].reset_index().rename(columns={"index": "Feature"})
        ols_table["P>|t|"] = ols_table["P>|t|"].apply(lambda x: f"{x:.3f}")
        ols_html = ols_table.to_html(index=False, justify='left')
        styled_html = f"""
        <div style="font-family: courier; color: black;">
        {ols_html}
        </div>
        """
        st.markdown(styled_html, unsafe_allow_html=True)

        st.subheader("Statistically Significant Attributes (p < 0.05)")
        #st.dataframe(sig_df)
        sig_df_display = sig_df.copy()
        sig_df_display["p_value"] = sig_df_display["p_value"].apply(lambda x: f"{x:.3f}")

        # Convert to HTML and style
        sig_html = sig_df_display.reset_index().rename(columns={"index": "Feature"}).to_html(index=False, justify='left')
        styled_sig_html = f"""
        <div style="font-family: courier; color: black;">
        {sig_html}
        </div>
        """

        st.markdown(styled_sig_html, unsafe_allow_html=True)


        st.subheader("Bar Chart Effect on Rank")
        plot_significant_coefficients(sig_df) #bar chart

        st.subheader("Line Graph — Error Trend")
        plot_error_trend(df_model_num)  #line graph

        
        st.subheader("Interpretation")
        st.markdown(
    """
Only a small subset of attributes significantly influence bestseller rank, 
suggesting that bestseller success depends on additional external factors 
not captured in the dataset (e.g., marketing, media coverage, author fame).

The regression analysis revealed that the strongest predictors included:

- **Recency** (`days_since_publication`)
- **Previous ranking performance** (`weeks_on_list` and `rank_last_week`)
- **Author popularity** (`author_popularity`)
- **Description length** (`description_length`)
- **Holiday-season releases** (`holiday_release`)

These attributes tend to improve a book’s rank (closer to #1), suggesting that
books benefit from momentum effects, established author recognition, and seasonal timing.

<span style='color:#1e90ff;'>
However, <b>sentiment</b>, <b>subjectivity</b>, and coarse <b>genre</b> categories did not show strong predictive power, indicating that consumer behavior may be influenced more by external factors such as marketing campaigns, media visibility, or pre-existing author reputation—variables not present in the dataset.
</span>
""",
    unsafe_allow_html=True
)

        st.subheader("Rolling Error Interpretation")
        st.markdown(
            """
A rolling error analysis shows that errors remain low and stable for mid-ranked
books (around ranks 10-20), meaning the model captures central ranking behavior well.  
However, prediction error rises for top-ranked books (ranks 1-5), suggesting that 
**true bestseller success** depends on additional non-textual drivers not captured 
in the dataset.
            """
        )


if __name__ == "__main__":
    main()


