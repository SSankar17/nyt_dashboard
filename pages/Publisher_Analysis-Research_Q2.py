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
    The main function that draws the Streamlit page content for Research Question 2.
    Creator: Sanjana Sankar
    """
    
    st.title("Research Question 2: NYT Bestseller Publisher Stability Analysis")
    st.markdown("This section investigates **which publishers consistently place books at the top of the NYT Bestseller lists** versus those whose top-ranked books fluctuate wildly in position.")
    st.markdown("---")

    publisher_stats_df, top_books_df = load_and_analyze_data()

    if publisher_stats_df.empty:
        # Stop rendering if data loading failed or returned empty
        return
    
    st.header("Dynamic Publisher Ranking")
    st.markdown("Select a metric to rank the top publishers. Lower **Rank Std Dev** and **Avg Rank** indicate higher stability and better performance.")

    # slider for user to select
    metric_options = {
        "Rank Stability (Standard Deviation)": "rank_std",
        "Average Rank (Performance)": "avg_rank",
        "Total Top-5 Appearances": "appearances",
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


    chart = alt.Chart(ranked_df).mark_bar().encode(
        y=alt.Y('publisher', sort=alt.EncodingSortField(field=selected_metric, op="average", order='ascending' if is_ascending else 'descending')),
        x=alt.X(selected_metric, title=selected_display_name),
        color=alt.Color(selected_metric, scale=alt.Scale(range='diverging')),
        tooltip=['publisher', 'avg_rank', 'rank_std', 'appearances', 'unique_books']
    ).properties(
        title=f"Top {top_n} Publishers Ranked by: {selected_display_name}"
    ).interactive()

    st.altair_chart(chart, use_container_width=True)



    st.header("Publisher Stability vs. Performance (Bubble Chart)")
    st.markdown("Tracks the trade-off between a publisher's average rank (performance) and consistency (stability). **Interact with the chart to zoom and pan!**")

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
            color=alt.value('white'),
            opacity=alt.condition(
                alt.datum.appearances > 30,  
                alt.value(1.0),
                alt.value(0.0)
            )
        )
        
        st.altair_chart(circle_layer + text_layer, use_container_width=True)
    else:
        st.warning("Not enough data points to plot the stability chart (requires 15+ appearances).")



    st.header("Top Publishers: Rank Performance Over Time (Scatterplot)")
    st.markdown("Tracks the weekly rank of the 5 publishers with the highest number of overall appearances. Hover over points to see the exact date and rank! **Interact with the chart to zoom and pan!**")

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


    #Summary

    st.header("4. Key Findings")
    st.markdown("Detailed look at the key metrics for the most stable and most fluctuating publishers based on rank standard deviation.")

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