import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import importlib.util
import os
import altair as alt 

#  CONFIGURATION (File Path Setup) 

try:
    # Set up the base directory path (assuming app.py is in 'Final Project/pages' and JSON is in 'Final Project')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)

    # Define the path to the JSON data file
    JSON_FILE_PATH = os.path.join(parent_dir, "books_historical (1).json")

    # Check if the JSON file exists
    if not os.path.exists(JSON_FILE_PATH):
        st.error(
            f"[FATAL ERROR]: Data file not found.\n\n**Please ensure 'books_historical (1).json' is in the main 'Final Project' directory** (path checked: `{JSON_FILE_PATH}`)."
        )
        st.stop()

    # Configuration module for API key is kept for completeness, though not used in analysis
    config_path = os.path.join(parent_dir, "config.py")

    spec = importlib.util.spec_from_file_location("config_downloads", config_path)
    config_downloads = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_downloads)

    API_KEY = getattr(config_downloads, 'API_KEY', 'DUMMY_KEY')
    BASE_URL = "https://api.nytimes.com/svc/books/v3"


except Exception as e:
    if 'config.py' in str(e):
        st.info("Note: Configuration file loading failed, but analysis will proceed using the local JSON data.")
    else:
        st.error(f"[FATAL ERROR]: An unexpected file path or configuration error occurred. Error: {e}")


#  PLACEHOLDER API FUNCTIONS 

def get_lists_names():
    return [{'list_name': 'Combined Print & E-Book Fiction', 'list_name_encoded': 'combined-print-and-e-book-fiction'}]


def fetch_historical_data(list_name, start_date, end_date):
    pass


def store_books_historical(data, list_name):
    pass


def count_historical_books():
    return 0


#  CORE ANALYSIS FUNCTION 

@st.cache_data(ttl=600)
def analyze_competition_dynamics(debut_threshold=5):
    """
    Analyzes the correlation between simultaneous market entries (debuts)
    and book performance (initial rank and persistence).
    Loads data from the local JSON file.
    """

    # 1. Retrieve necessary data by loading the JSON file
    # st.info(f"1. Retrieving data from local file: {os.path.basename(JSON_FILE_PATH)}...") # REMOVED

    try:
        df = pd.read_json(JSON_FILE_PATH)

    except Exception as e:
        st.error(f"FATAL: Could not read or parse local JSON file. Ensure it is a valid JSON array. Error: {e}")
        return {'initial_rank': pd.DataFrame(), 'persistence': pd.DataFrame()}

    if df.empty:
        st.warning("No data found in the DataFrame loaded from the JSON file.")
        return {'initial_rank': pd.DataFrame(), 'persistence': pd.DataFrame()}

    # Ensure date column is datetime
    if 'bestsellers_date' in df.columns:
        df['bestsellers_date'] = pd.to_datetime(df['bestsellers_date'], errors='coerce')

    # Clean and standardize rank_last_week: convert to numeric, treat debuts (NaN/0) as 0
    # st.info("2. Performing analysis and calculating metrics...") # REMOVED
    df['rank_last_week'] = pd.to_numeric(df['rank_last_week'], errors='coerce').fillna(0)
    df['is_debut'] = df['rank_last_week'].apply(lambda x: 1 if x == 0 else 0)

    # 2. Calculate the "Competition Score" for each list/week
    competition_scores = df.groupby(['list_name', 'bestsellers_date'])['is_debut'].sum().reset_index()
    competition_scores.rename(columns={'is_debut': 'debut_count'}, inplace=True)

    # 3. Classify weeks as 'Crowded' or 'Quiet' based on the threshold
    competition_scores['competition_level'] = competition_scores['debut_count'].apply(
        lambda x: 'Crowded' if x >= debut_threshold else 'Quiet'
    )
    # st.info(f"   -> Using threshold: {debut_threshold} debuts to define 'Crowded' weeks.") # REMOVED

    # 4. Merge the competition level back to the main DataFrame
    df = pd.merge(df, competition_scores, on=['list_name', 'bestsellers_date'], how='left')

    # 5. Analyze Initial Rank (Debuts Only)
    debut_books = df[df['is_debut'] == 1]
    initial_rank_analysis = debut_books.groupby('competition_level')['rank'].agg(
        ['mean', 'median', 'count']).reset_index()
    initial_rank_analysis.rename(
        columns={'mean': 'Avg_Initial_Rank', 'median': 'Median_Initial_Rank', 'count': 'Debut_Count'}, inplace=True)
    initial_rank_analysis['Metric'] = 'Initial Rank'

    # 6. Analyze Persistence (All Books)
    persistence_analysis = df.groupby('competition_level')['weeks_on_list'].agg(
        ['mean', 'median', 'count']).reset_index()
    persistence_analysis.rename(
        columns={'mean': 'Avg_Weeks_on_List', 'median': 'Median_Weeks_on_List', 'count': 'Total_Book_Entries'},
        inplace=True)
    persistence_analysis['Metric'] = 'Persistence'

    # 7. Format results
    initial_rank_analysis = initial_rank_analysis[
        ['Metric', 'competition_level', 'Avg_Initial_Rank', 'Median_Initial_Rank', 'Debut_Count']]
    persistence_analysis = persistence_analysis[
        ['Metric', 'competition_level', 'Avg_Weeks_on_List', 'Median_Weeks_on_List', 'Total_Book_Entries']]

    return {'initial_rank': initial_rank_analysis, 'persistence': persistence_analysis}


#  PLOTTING FUNCTIONS 

def plot_initial_rank_altair(rank_df, color_map):
    """Generates the Initial Rank bar chart using Altair."""

    # Convert color_map to a domain/range for Altair scale
    domain = list(color_map.keys())
    range_ = list(color_map.values())

    # Base Bar Chart
    bars = alt.Chart(rank_df).mark_bar().encode(
        # Invert Y-axis so lower rank (better) is at the top
        y=alt.Y('Avg_Initial_Rank:Q', title='Average Initial Rank (Lower = Better)', scale=alt.Scale(reverse=True)),
        x=alt.X('competition_level:N', title='Competition Level'),
        color=alt.Color('competition_level:N', scale=alt.Scale(domain=domain, range=range_), title=''),
        tooltip=[
            'competition_level',
            alt.Tooltip('Avg_Initial_Rank', format='.2f'),
            alt.Tooltip('Debut_Count', title='Debut Count')
        ]
    ).properties(
        title='Impact on Initial Rank for Debut Books'
    )

    # Text labels for the rank value
    text_labels = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-8,  # Push the text slightly above the bar
        color='black',
        fontSize=13
    ).encode(
        text=alt.Text('Avg_Initial_Rank:Q', format='.2f'),
        y=alt.Y('Avg_Initial_Rank:Q', scale=alt.Scale(reverse=True)),
        color=alt.value('black')  # Force label color to black
    )

    # Annotations for sample size (using another layer and explicit data)
    sample_size_labels = alt.Chart(rank_df).mark_text(
        align='center',
        baseline='bottom',
        dy=-200,  # Position above the bars (adjust as needed for chart size)
        color='gray',
        fontStyle='italic',
        fontSize=10
    ).encode(
        x='competition_level:N',
        y=alt.value(20),  # fixed y position near the top
        text=alt.Text('Debut_Count:Q', format='n={:}', title=''),
    )

    return (bars + text_labels + sample_size_labels).interactive()


def plot_persistence_altair(persistence_df, color_map):
    """Generates the Persistence (Avg Weeks) bar chart using Altair."""

    domain = list(color_map.keys())
    range_ = list(color_map.values())

    # Base Bar Chart
    bars = alt.Chart(persistence_df).mark_bar().encode(
        y=alt.Y('Avg_Weeks_on_List:Q', title='Average Weeks on List (Higher = Better)'),
        x=alt.X('competition_level:N', title='Competition Level'),
        color=alt.Color('competition_level:N', scale=alt.Scale(domain=domain, range=range_), title=''),
        tooltip=[
            'competition_level',
            alt.Tooltip('Avg_Weeks_on_List', format='.2f'),
            alt.Tooltip('Total_Book_Entries', title='Total Entries')
        ]
    ).properties(
        title='Impact on List Persistence (Avg Weeks)'
    )

    # Text labels for the average weeks value
    text_labels = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-4,  # Push the text slightly above the bar
        color='black',
        fontSize=13
    ).encode(
        text=alt.Text('Avg_Weeks_on_List:Q', format='.2f'),
        color=alt.value('black')  # Force label color to black
    )

    # Annotations for sample size (using another layer and explicit data)
    sample_size_labels = alt.Chart(persistence_df).mark_text(
        align='center',
        baseline='top',
        dy=-10,  # Position near the top
        color='gray',
        fontStyle='italic',
        fontSize=10
    ).encode(
        x='competition_level:N',
        y=alt.value(10),  # fixed y position near the bottom
        text=alt.Text('Total_Book_Entries:Q', format='n={:}', title=''),
    )

    return (bars + text_labels + sample_size_labels).interactive()


# STREAMLIT

def main():
    st.set_page_config(layout="wide")
    st.title("NYT Bestseller Competition Dynamics Analysis")
    st.write("**Author: Leanne Chung**")
    st.markdown("---")

    #  INPUT PARAMETERS 
    st.sidebar.header("Analysis Parameters")
    DEBUT_THRESHOLD = st.sidebar.slider(
        "Debut Count Threshold for 'Crowded' Week:",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
        help="A week is classified as 'Crowded' if the number of debut books is greater than or equal to this threshold."
    )

    color_map = {'Crowded': '#F7C6A5', 'Quiet': '#8FB9C9'}

    #  RUN THE ANALYSIS 
    st.header("Competition Analysis Results")
    try:
        analysis_results = analyze_competition_dynamics(DEBUT_THRESHOLD)

        rank_df = analysis_results['initial_rank']
        persistence_df = analysis_results['persistence']

        if rank_df.empty or persistence_df.empty:
            return

        #  Display DataFrames 
        st.subheader("Impact on Initial Rank (For Debut Books)")
        st.dataframe(rank_df.set_index('Metric').style.format({
            'Avg_Initial_Rank': "{:.2f}",
            'Median_Initial_Rank': "{:.1f}",
            'Debut_Count': "{:d}"
        }))

        st.subheader("Impact on Persistence (For ALL Books)")
        st.dataframe(persistence_df.set_index('Metric').style.format({
            'Avg_Weeks_on_List': "{:.2f}",
            'Median_Weeks_on_List': "{:.1f}",
            'Total_Book_Entries': "{:d}"
        }))

        #  Display Charts (Separated) 
        st.header("Comparative Visualization of Competition Impact")

        col_rank, col_persistence = st.columns(2)

        with col_rank:
            st.subheader("Average Initial Rank (Debuts Only)")
            chart_rank = plot_initial_rank_altair(rank_df, color_map)
            st.altair_chart(chart_rank, use_container_width=True)

        with col_persistence:
            st.subheader("Average Weeks on List (All Books)")
            chart_persistence = plot_persistence_altair(persistence_df, color_map)
            st.altair_chart(chart_persistence, use_container_width=True)

        #  Display Original Notebook Text 
        st.markdown("---")
        st.header("Key Findings & Takeaway ")

        st.subheader("Key Findings")
        st.markdown(
            """
            1. **Data Utilization:** Utilized data from January 1, 2024 to December 31, 2024 to capture the publishing industry's most recent and full annual cycle.
            2. **Ranking of Books by Crowd:** Books launched during quiet weeks debuted closer to the top/middle rank compared to books launched in crowded weeks. For instance, crowded weeks sees an average rank of 17.5 while quiet weeks see an average rank of 9.3, indicating that books debuting in a quiet market has an average starting position of 8 ranks higher than those debuting in a crowded market.
            3. **Long-Term Resilience:** Books released in quiet weeks has a longer average of staying on the Bestseller's list, compared to crowded weeks. For instance, crowded weeks has an average longevity of 18.9 weeks while quiet weeks sees an average longevity of 45.4 weeks, indicating that books debuting in a quiet market persisted on the bestseller's list for 26.5 weeks longer.
            """
        )

        st.subheader("Takeaway")
        st.markdown(
            """
            Analyzing the debut entries, the analysis shows that market crowding influences both rank and longevity. Crowded weeks, representing high competition, resulted with low rankings and longevity. Meanwhile, quiet weeks, representing, low competition, resulted with a higher ranking and longer persistence on the list. This indicates that reduced entry-point competition confers a durable competitive edge, improving a book’s visibility, driving higher sales, and extending its lifespan on the market.
            """
        )


    except Exception as e:
        st.error(f"An unexpected error occurred during analysis or visualization: {e}")


if __name__ == "__main__":
    main()
