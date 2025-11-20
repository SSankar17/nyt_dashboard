import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt 
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
# to run app, copy paste in terminal: streamlit run Main_Page-Streamlit_App.py

try:
    from get_data import get_all_historical_books 
except ImportError:
    st.error("Could not import database functions from 'get_data.py'. Please ensure the file is accessible to the Streamlit app.")
    get_all_historical_books = lambda: pd.DataFrame()



@st.cache_data(show_spinner="Fetching and analyzing historical data (This runs only once)...")
def load_and_analyze_data():
    """Fetches historical books and calculates the publisher statistics."""
    
    try:
        # Load the data from your database
        df = get_all_historical_books()
    except Exception as e:
        st.error(f"Error fetching historical data. Is your MongoDB connection active? Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if df.empty:
        st.warning("Historical books DataFrame is empty. Please run the data fetching script first to populate your database.")
        return pd.DataFrame(), pd.DataFrame()

    # Data Cleaning and Filtering (Focus on top 5 ranks)
    df['bestsellers_date'] = pd.to_datetime(df['bestsellers_date'])
    top_books = df[df['rank'] <= 5].copy()

    # Calculate Stability Metrics
    publisher_stats = top_books.groupby('publisher').agg({
        'rank': ['mean', 'std', 'count', 'min', 'max'],
        'weeks_on_list': ['mean', 'max'],
        'title': 'nunique'
    }).round(2)

    publisher_stats.columns = [
        'avg_rank', 'rank_std', 'appearances', 'best_rank', 
        'worst_rank', 'avg_weeks', 'max_weeks', 'unique_books'
    ]

    publisher_stats = publisher_stats[publisher_stats['appearances'] >= 5]
    publisher_stats = publisher_stats.sort_values('rank_std')
    
    # Reset index to make 'publisher' a column for Altair plotting
    publisher_stats = publisher_stats.reset_index()
    
    return publisher_stats, top_books


def app_page():
    """
    The function that xdisplays the Streamlit page content for Research Question 2.
    Utilizes data from 2010 - 2025
    Creator: Sanjana Sankar
    """
    
    st.title("Publisher Stability Analysis")
    st.markdown("In this section, we will investigate **which publishers consistently place books at the top of the NYT Bestseller lists** versus those whose top-ranked books fluctuate wildly in position."\
                " We have utilized data from 2010 - 2025  to capture meaningful trends while still being recent enough to reflect the current publishing market. \n")
    st.markdown("Understanding this helps us determine whether a publisher’s success is driven by a **stable, reliable strategy** or by a few unpredictable breakout hits. It also provides us with context for " \
    "evaluating how much influence certain publishers have over the bestseller market and whether their performance reflects consistent quality, strong marketing, or simple volatility.")
    st.markdown("---")

    publisher_stats_df, top_books_df = load_and_analyze_data()

    if publisher_stats_df.empty:
        return
    
    st.header(" Publisher Rankings - Bar Charts")
    st.markdown(
    "Select a metric to rank the top publishers.  \n\n"
    "<span style='color:#1e90ff;'>A lower <b>standard deviation ranking</b> and higher <b>average ranking</b> indicate higher stability and better performance.</span>",
    unsafe_allow_html=True
)
    # slider options for user to select
    metric_options = {
        "Rank Stability (Standard Deviation)": "rank_std",
        "Average Rank (Performance)": "avg_rank",
        "Total Top Appearances": "appearances",
        "Number of Unique Bestsellers": "unique_books"
    }
    selected_display_name = st.selectbox(
        "Select Metric to Rank Publishers By:",
        list(metric_options.keys()),
        index=0
    )

    selected_metric = metric_options[selected_display_name]
    is_ascending = (selected_metric in ["rank_std", "avg_rank"]) 

    # sort based on input
    top_n = st.slider("Select number of publishers to display", 5, 20, 10, key="top_n_slider_rq2")
    ranked_df = publisher_stats_df.sort_values(
        by=selected_metric, ascending=is_ascending
    ).head(top_n)

    pastel_colors = [
    "#8FB9C9",  
    "#E79A95", 
    "#F7C6A5",  
    "#8FD1B3",  
    "#C7CEEA"   
    ]
    chart = alt.Chart(ranked_df).mark_bar().encode(
    y=alt.Y(
        'publisher',
        sort=alt.EncodingSortField(
            field=selected_metric,
            op="average",
            order='ascending' if is_ascending else 'descending'
        )
    ),
    x=alt.X(selected_metric, title=selected_display_name),
    color=alt.Color(
        selected_metric,
        scale=alt.Scale(range=pastel_colors),
        legend=None
    ),
    tooltip=['publisher', 'avg_rank', 'rank_std', 'appearances', 'unique_books']).properties(
    title=f"Top {top_n} Publishers Ranked by: {selected_display_name}").interactive()

    st.altair_chart(chart, use_container_width=True)


# next portion
    st.header("Publisher Stability vs. Performance - Bubble Chart")
    st.markdown("Tracks the trade-off between a publisher's average rank (performance) and consistency (stability)")
    st.markdown(
    "This helps us quickly identify which publishers are both strong and reliable versus those that perform well only occasionally.<br><br>"
    "<span style='color:#1e90ff;'>This gives context for whether a publisher’s success comes from **consistent hits** or from **unpredictable spikes** in ranking.</span>",
    unsafe_allow_html=True
)


    # Filter for publishers with at least 15 appearances for better visualization density
    top_publishers_for_plot = publisher_stats_df[publisher_stats_df['appearances'] >= 15]

    if not top_publishers_for_plot.empty:
        
        # Base chart for circles and text
        base = alt.Chart(top_publishers_for_plot).encode(
            # x-axis average rank (performance)
            x=alt.X('avg_rank', title='Average Rank (1=best, 5=worst)'),
            
            # y-axis  Std Dev (stability, lower is better)
            y=alt.Y('rank_std', title='Rank Std Dev (lower = more stable)'),
            
            # interactivity
            tooltip=[
                'publisher:N',
                alt.Tooltip('avg_rank', title='Avg Rank'),
                alt.Tooltip('rank_std', title='Rank Std Dev'),
                alt.Tooltip('appearances', title='Appearances')
            ]
        ).properties(
            title="Publisher Stability vs. Performance"
        ).interactive() # Make the entire chart interactive (zoom/pan)

        # circle/bubble layer
        circle_layer = base.mark_circle().encode(
            # bubble size
            size=alt.Size('appearances', scale=alt.Scale(range=[50, 1500]), title='Total Top-5 Appearances'),
            
            # color by stability (using avg_rank for color intensity)
            color=alt.Color('avg_rank', scale=alt.Scale(range='diverging', domain=[1, 5], reverse=True), legend=None),
            opacity=alt.value(0.6)
        )
        
        # Text Label Layer (only for high-impact publishers)
        text_layer = base.mark_text(
            align='left', 
            baseline='middle', 
            dx=7 #  text to the right of the bubble
        ).encode(
            text=alt.Text('publisher:N'),
            size=alt.value(10),
            color=alt.value('black'),
            opacity=alt.condition(
                alt.datum.appearances > 30,  
                alt.value(1.0),
                alt.value(0.0)
            )
        )
        
        st.altair_chart(circle_layer + text_layer, use_container_width=True)
    else:
        st.warning("Not enough data points to plot the stability chart (requires 15+ appearances).")

    st.markdown(
    "We can see from this bubble chart how <b>Random House</b> and <b>Penguin</b> stand out in having "
    "consistent high ranking with low standard deviation, indicating _stable performance_.\n "

    "In contrast, publishers like <b>Crown</b> or <b>Simon & Schuster</b> show higher variability in rank, indicating "
    "their success is _less predictable_.\n\n"

    "<span style='color:#1e90ff;'>There are also publishers like <b>Vintage</b> and <b>Grand Central</b> who are moderately stable but don't achieve "
    "top ranks as often, suggesting a more niche presence rather than blockbuster hits.</span>",
    unsafe_allow_html=True
)





    st.header("Top Publishers by Ranking Performance Over Time - Scatterplot")
    st.markdown("Tracks the weekly rank of the 5 publishers with the highest number of overall appearances.")

    if not publisher_stats_df.empty and not top_books_df.empty:
        top_5_publishers = publisher_stats_df.nlargest(5, 'appearances')['publisher'].tolist()
        
        df_filtered = top_books_df[top_books_df['publisher'].isin(top_5_publishers)].copy()
        
        time_series_chart = alt.Chart(df_filtered).mark_circle(size=60).encode(
            # xaxis date
            x=alt.X('bestsellers_date:T', title='Bestsellers Date'),
            
            # yaxis start with rank 1
            y=alt.Y('rank:Q', title='Rank (1 = Best)', scale=alt.Scale(domain=[5.5, 0.5])),
            
            color=alt.Color('publisher:N', title='Publisher'),
            
            tooltip=[
                alt.Tooltip('bestsellers_date:T', title='Date'),
                alt.Tooltip('rank:Q', title='Rank'),
                'publisher:N'
            ]
        ).properties(
            title="Top 5 Publishers: Rank Performance Over Time (Scatterplot)"
        ).interactive() #zooming and panning

        st.altair_chart(time_series_chart, use_container_width=True)
    else:
        st.warning("Data not available to generate the time series chart.")

    st.markdown("From this scatterplot, we observe that publishers like **Penguin** and **Random House** consistently place books in top ranks over time. " \
 "In contrast, publishers such as **Crown** and **Simon & Schuster** show more variability in their rankings, " \
    "suggesting that their success may depend on occasional bestsellers rather than a consistent output of high-ranking books.\n\n" \
    "<span style='color:#1e90ff;'>This analysis highlights how certain publishers maintain a steady presence at the top of the bestseller lists, while others experience more fluctuations, reflecting different approaches to publishing and market influence.</span>",
    unsafe_allow_html=True
)


    #Summary

    st.header("Key Findings")
    st.markdown(
    "- Publishers like **Random House** and **Penguin** consistently achieve top ranks with low variability, indicating strong and stable performance.\n"
    "- Publishers such as **Crown** and **Simon & Schuster** show higher fluctuations in rank, suggesting their success depends on occasional bestsellers rather than consistent output.\n"
    "- Mid-tier publishers like **Vintage** and **Grand Central** maintain moderate stability but rarely hit the top ranks, pointing to a niche market presence.\n"
    "- Analyzing both average rank and rank standard deviation provides us insight into which publishers combine **performance** and **consistency** which helps us differentiate between reliable market leaders and unpredictable performers.\n"
    "- Analyzing rank over time shows that sustained success is often associated with publishers who consistently release high-quality or well-marketed titles, while spikes indicate the impact of specific releases or marketing campaigns."
)
    col1, col2 = st.columns(2)

    # MOST STABLE
    with col1:
        st.subheader("MOST STABLE (Top 5)")
        st.markdown("*(Lowest Standard Deviation in Rank)*")
        stable_summary = publisher_stats_df.set_index('publisher').nsmallest(5, 'rank_std')[['avg_rank', 'rank_std', 'appearances', 'unique_books']]
        st.dataframe(stable_summary, use_container_width=True)

    # MOST FLUCTUATING
    with col2:
        st.subheader("MOST FLUCTUATING (Top 5)")
        st.markdown("*(Highest Standard Deviation in Rank)*")
        fluctuating_summary = publisher_stats_df.set_index('publisher').nlargest(5, 'rank_std')[['avg_rank', 'rank_std', 'appearances', 'unique_books']]
        st.dataframe(fluctuating_summary, use_container_width=True)

    with st.expander("Show Full Publisher Statistics Table"):
        st.dataframe(publisher_stats_df, use_container_width=True)
    
    



app_page()
