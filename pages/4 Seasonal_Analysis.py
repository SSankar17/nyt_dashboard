import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt 
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from scipy import stats

# to run app, copy paste in terminal: streamlit run NYT_Alisha_Hartarto.py

try:
    from get_data import get_all_historical_books 
except ImportError:
    st.error("Could not import database functions from 'get_data.py'. Please ensure the file is accessible to the Streamlit app.")
    get_all_historical_books = lambda: pd.DataFrame()


@st.cache_data(show_spinner="Fetching and analyzing historical data (This runs only once)...")
def load_and_analyze_data():
    """Fetches historical books and prepares seasonal/monthly analysis."""
    
    try:
        # Load the data from your database
        df = get_all_historical_books()
    except Exception as e:
        st.error(f"Error fetching historical data. Is your MongoDB connection active? Error: {e}")
        return pd.DataFrame()

    if df.empty:
        st.warning("Historical books DataFrame is empty. Please run the data fetching script first to populate your database.")
        return pd.DataFrame()

    # Data Cleaning and Preparation
    df['bestsellers_date'] = pd.to_datetime(df['bestsellers_date'])
    df['year'] = df['bestsellers_date'].dt.year
    df['month'] = df['bestsellers_date'].dt.month
    df['month_name'] = df['bestsellers_date'].dt.month_name()
    
    # Define seasons
    def get_season(month):
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:  # 9, 10, 11
            return 'Fall'
    
    df['season'] = df['month'].apply(get_season)
    
    # Define periods/holidays
    def get_period(date):
        month = date.month
        day = date.day
        
        # Holiday periods
        if (month == 12 and day >= 20) or (month == 1 and day <= 5):
            return 'Holiday Season'
        elif month == 2 and day >= 7 and day <= 14:
            return "Valentine's Day"
        elif month == 5 and day >= 1 and day <= 14:
            return "Mother's Day"
        elif month == 6 and day >= 14 and day <= 21:
            return "Father's Day"
        elif month == 9 and day >= 1 and day <= 15:
            return 'Back to School'
        elif month == 11 and day >= 20:
            return 'Thanksgiving'
        else:
            return 'Regular Period'
    
    df['period'] = df['bestsellers_date'].apply(get_period)
    
    return df


def app_page():
    """
    The function that displays the Streamlit page content for Seasonal Analysis.
    Utilizes data from 2020 - 2025
    Creator: Alisha Hartarto
    """
    
    st.title("Are there identifiable seasonal trends or social events that influence list rankings?")
    st.write("Author: Alisha Hartarto")
    st.markdown("In this section, we will investigate **seasonal patterns and temporal trends** in the NYT Bestseller lists, " \
                "analyzing how book performance varies across different times of the year.")
    st.markdown("Understanding seasonal patterns helps us determine whether certain times of year are more favorable for book sales, " \
                "and whether publishers strategically time their releases around holidays and seasons.")
    st.markdown("*This analysis utilizes data from 2020 - 2025*")
    st.markdown("---")

    df_books = load_and_analyze_data()

    if df_books.empty:
        return
    
    # Define order for seasons and months
    season_order = ['Winter', 'Spring', 'Summer', 'Fall']
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']

    #SEASONAL PATTERNS ANALYSIS
    st.header("Seasonal Patterns Analysis")
    st.markdown("Analyzing how book performance varies across the four seasons")
    
    st.markdown("**Analysis:** Over the past five years (2020-2025), spring and winter had the highest number of unique books on the NYT Bestseller list. "
                "Summer titles also stay on the list for long periods, and Fall books show strong longevity despite fewer releases.")
    st.markdown("")

    # Calculate seasonal statistics
    books_by_season = df_books.groupby('season').agg({
        'title': 'count',
        'primary_isbn13': 'nunique',
        'weeks_on_list': 'mean',
        'rank': 'mean'
    }).rename(columns={
        'title': 'total_entries',
        'primary_isbn13': 'unique_books',
        'weeks_on_list': 'avg_weeks_on_list',
        'rank': 'avg_rank'
    }).reindex(season_order)

    # Reset index for Altair
    books_by_season_plot = books_by_season.reset_index()

    # Create two columns for side-by-side charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Unique Books by Season")
        chart1 = alt.Chart(books_by_season_plot).mark_bar().encode(
            x=alt.X('season', sort=season_order, title='Season'),
            y=alt.Y('unique_books', title='Number of Unique Books'),
            color=alt.Color('season', scale=alt.Scale(range=['#6baed6', '#74c476', '#fd8d3c', '#9e9ac8']), legend=None),
            tooltip=['season', 'unique_books', 'avg_weeks_on_list']
        ).properties(
            title='Unique Books by Season (All Years)',
            width=350,
            height=300
        ).interactive()
        st.altair_chart(chart1, use_container_width=True)

    with col2:
        st.subheader("Average Weeks on List by Season")
        chart2 = alt.Chart(books_by_season_plot).mark_bar().encode(
            x=alt.X('season', sort=season_order, title='Season'),
            y=alt.Y('avg_weeks_on_list', title='Average Weeks'),
            color=alt.Color('season', scale=alt.Scale(range=['#6baed6', '#74c476', '#fd8d3c', '#9e9ac8']), legend=None),
            tooltip=['season', 'avg_weeks_on_list', 'unique_books']
        ).properties(
            title='Average Weeks on List by Season',
            width=350,
            height=300
        ).interactive()
        st.altair_chart(chart2, use_container_width=True)

    # Season by Year Trends
    st.subheader("Seasonal Trends Over Years")
    season_by_year = df_books.groupby(['year', 'season'])['primary_isbn13'].nunique().reset_index()
    season_by_year.columns = ['year', 'season', 'unique_books']

    trend_chart = alt.Chart(season_by_year).mark_line(point=True).encode(
        x=alt.X('year:O', title='Year'),
        y=alt.Y('unique_books', title='Number of Unique Books'),
        color=alt.Color('season', scale=alt.Scale(range=['#6baed6', '#74c476', '#fd8d3c', '#9e9ac8'])),
        tooltip=['year', 'season', 'unique_books']
    ).properties(
        title='Seasonal Trends Over Years',
        height=400
    ).interactive()
    st.altair_chart(trend_chart, use_container_width=True)

    st.markdown("---")

    # MONTHLY PATTERNS ANALYSIS
    st.header("Monthly Patterns Analysis")
    st.markdown("Examining patterns across different months of the year")
    
    st.markdown("**Analysis:** From a month-by-month view, February and March contribute the largest number of new releases that appear on the NYT Bestseller list. "
                "Although Summer is less in terms of volume, books released during June and July stay especially longer on the list.")
    st.markdown("")

    # Calculate monthly statistics
    books_by_month = df_books.groupby('month_name').agg({
        'title': 'count',
        'primary_isbn13': 'nunique',
        'weeks_on_list': 'mean'
    }).rename(columns={
        'title': 'total_entries',
        'primary_isbn13': 'unique_books',
        'weeks_on_list': 'avg_weeks_on_list'
    }).reindex(month_order)

    books_by_month_plot = books_by_month.reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Unique Books by Month")
        chart3 = alt.Chart(books_by_month_plot).mark_bar(color='steelblue').encode(
            x=alt.X('month_name', sort=month_order, title='Month', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('unique_books', title='Number of Unique Books'),
            tooltip=['month_name', 'unique_books', 'avg_weeks_on_list']
        ).properties(
            title='Unique Books by Month (All Years)',
            width=400,
            height=350
        ).interactive()
        st.altair_chart(chart3, use_container_width=True)

    with col2:
        st.subheader("Average Weeks on List by Month")
        chart4 = alt.Chart(books_by_month_plot).mark_bar(color='green').encode(
            x=alt.X('month_name', sort=month_order, title='Month', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('avg_weeks_on_list', title='Average Weeks'),
            tooltip=['month_name', 'avg_weeks_on_list', 'unique_books']
        ).properties(
            title='Average Weeks on List by Month',
            width=400,
            height=350
        ).interactive()
        st.altair_chart(chart4, use_container_width=True)

    st.markdown("---")

    # SECTION 3: HOLIDAY/EVENT PATTERNS ANALYSIS
    st.header("Holiday/Event Patterns Analysis")
    st.markdown("Analyzing how different periods and holidays affect book performance")
    
    st.markdown("**Analysis:** The majority of new books enter the NYT Bestseller list during regular periods without major seasonal events. "
                "However, during periods such as Father's Day or the Holiday Season, books remain on the list longer, indicating higher and stronger reader engagement.")
    st.markdown("")

    # Calculate period statistics
    books_by_period = df_books.groupby('period').agg({
        'title': 'count',
        'primary_isbn13': 'nunique',
        'weeks_on_list': 'mean',
        'rank': 'mean'
    }).rename(columns={
        'title': 'total_entries',
        'primary_isbn13': 'unique_books',
        'weeks_on_list': 'avg_weeks_on_list',
        'rank': 'avg_rank'
    }).sort_values('unique_books', ascending=False)

    books_by_period_plot = books_by_period.reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Unique Books by Period/Event")
        chart5 = alt.Chart(books_by_period_plot).mark_bar(color='darkgreen').encode(
            y=alt.Y('period', sort='-x', title='Period'),
            x=alt.X('unique_books', title='Number of Unique Books'),
            tooltip=['period', 'unique_books', 'avg_weeks_on_list', 'avg_rank']
        ).properties(
            title='Unique Books by Period/Event (All Years)',
            height=400
        ).interactive()
        st.altair_chart(chart5, use_container_width=True)

    with col2:
        st.subheader("Average Weeks on List by Period")
        chart6 = alt.Chart(books_by_period_plot).mark_bar(color='purple').encode(
            y=alt.Y('period', sort='-x', title='Period'),
            x=alt.X('avg_weeks_on_list', title='Average Weeks'),
            tooltip=['period', 'avg_weeks_on_list', 'unique_books']
        ).properties(
            title='Average Weeks on List by Period',
            height=400
        ).interactive()
        st.altair_chart(chart6, use_container_width=True)

    # Period trends over years
    st.subheader("Period Trends Over Years")
    period_by_year = df_books.groupby(['year', 'period'])['primary_isbn13'].nunique().reset_index()
    period_by_year.columns = ['year', 'period', 'unique_books']

    period_trend_chart = alt.Chart(period_by_year).mark_line(point=True).encode(
        x=alt.X('year:O', title='Year'),
        y=alt.Y('unique_books', title='Number of Unique Books'),
        color='period:N',
        tooltip=['year', 'period', 'unique_books']
    ).properties(
        title='Period Trends Over Years',
        height=400
    ).interactive()
    st.altair_chart(period_trend_chart, use_container_width=True)

    st.markdown("---")

    # TOP BOOKS IN EACH SEASON
    st.header("4. Top Books in Each Season (All Years)")
    st.markdown("Select a season to see the top performing books.")

    selected_season = st.selectbox(
        "Select Season:",
        season_order,
        index=0
    )

    season_books = df_books[df_books['season'] == selected_season]
    
    top_books = season_books.groupby(['title', 'author']).agg({
        'rank': 'mean',
        'weeks_on_list': 'max',
        'bestsellers_date': 'count'
    }).rename(columns={
        'rank': 'avg_rank',
        'weeks_on_list': 'max_weeks',
        'bestsellers_date': 'appearances'
    }).sort_values('avg_rank').head(10).reset_index()

    st.subheader(f"Top 10 Books in {selected_season}")
    
    # Create display dataframe with better formatting
    display_top_books = top_books.copy()
    display_top_books['avg_rank'] = display_top_books['avg_rank'].round(1)
    display_top_books.columns = ['Title', 'Author', 'Avg Rank', 'Max Weeks', 'Appearances']
    display_top_books.index = range(1, len(display_top_books) + 1)
    
    # Display as table
    st.dataframe(
        display_top_books,
        use_container_width=True,
        height=400
    )

    st.markdown("---")

    # BOOKS APPEARING IN MULTIPLE SEASONS
    st.header("Books Appearing in Multiple Seasons")
    st.markdown("Several books reappeared across multiple seasons, indicating that they maintained strong, year-round popularity. " \
                "This list highlights 20 New York Times Bestsellers that appeared in more than one season.")

    # Find books that appear in multiple seasons
    books_multi_season = df_books.groupby('title').agg({
        'season': lambda x: x.nunique(),
        'weeks_on_list': 'max',
        'rank': 'mean',
        'author': 'first'
    }).rename(columns={
        'season': 'num_seasons',
        'weeks_on_list': 'max_weeks',
        'rank': 'avg_rank'
    })

    books_multi_season = books_multi_season[books_multi_season['num_seasons'] > 1].sort_values(
        ['num_seasons', 'max_weeks'], ascending=[False, False]
    ).head(20).reset_index()

    # Add seasons appeared column
    books_multi_season['seasons_appeared'] = books_multi_season['title'].apply(
        lambda x: ', '.join(sorted(df_books[df_books['title'] == x]['season'].unique()))
    )

    # Create a display dataframe with better column names
    display_df = books_multi_season[['title', 'author', 'num_seasons', 'seasons_appeared', 'max_weeks', 'avg_rank']].copy()
    display_df.columns = ['Title', 'Author', 'Number of Seasons', 'Seasons Appeared', 'Max Weeks on List', 'Avg Rank']
    display_df['Avg Rank'] = display_df['Avg Rank'].round(1)
    display_df.index = range(1, len(display_df) + 1)

    # Display as a scrollable dataframe
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400  # Makes it scrollable
    )

    st.markdown("---")

    # STATISTICAL SIGNIFICANCE TEST
    st.header("Statistical Significance Test")
    st.markdown("Testing if there are significant differences between seasons")

    # Test if there are significant differences between seasons
    seasons_data = [df_books[df_books['season'] == s]['weeks_on_list'].dropna() 
                    for s in season_order]

    f_stat, p_value = stats.f_oneway(*seasons_data)

    st.markdown("**ANOVA Test: Are there significant differences between seasons?**")
    st.markdown(f"- F-statistic: **{f_stat:.4f}**")
    st.markdown(f"- P-value: **{p_value:.4f}**")

    if p_value < 0.05:
        st.success("✓ Result: There IS a statistically significant difference between seasons (p < 0.05)")
        st.markdown("This means seasonal patterns are REAL, not just random variation.")
    else:
        st.info("✗ Result: No statistically significant difference between seasons (p >= 0.05)")
        st.markdown("Seasonal differences might be due to chance.")

    st.markdown("---")

    # KEY INSIGHTS SUMMARY
    st.header("Key Insights Summary")

    # Most active season
    max_season = books_by_season['unique_books'].idxmax()
    st.markdown(f"**1. MOST ACTIVE SEASON: {max_season}**")
    st.markdown(f"   - {books_by_season.loc[max_season, 'unique_books']:.0f} unique books")
    st.markdown(f"   - Avg {books_by_season.loc[max_season, 'avg_weeks_on_list']:.1f} weeks on list")

    # Longest staying season
    longest_season = books_by_season['avg_weeks_on_list'].idxmax()
    st.markdown(f"**2. BOOKS STAY LONGEST IN: {longest_season}**")
    st.markdown(f"   - Avg {books_by_season.loc[longest_season, 'avg_weeks_on_list']:.1f} weeks on list")

    # Most active period
    max_period = books_by_period['unique_books'].idxmax()
    st.markdown(f"**3. MOST ACTIVE PERIOD: {max_period}**")
    st.markdown(f"   - {books_by_period.loc[max_period, 'unique_books']:.0f} unique books")

    # Best performing period (lowest avg rank)
    best_period = books_by_period['avg_rank'].idxmin()
    st.markdown(f"**4. BEST PERFORMING PERIOD (lowest avg rank): {best_period}**")
    st.markdown(f"   - Avg rank: {books_by_period.loc[best_period, 'avg_rank']:.1f}")

    st.markdown("---")

    # Summary Statistics Tables
    st.header("Summary Statistics")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Seasonal Statistics")
        st.dataframe(books_by_season, use_container_width=True)

    with col2:
        st.subheader("Period Statistics")
        st.dataframe(books_by_period, use_container_width=True)

    with st.expander("Show Monthly Statistics Table"):
        st.dataframe(books_by_month, use_container_width=True)


# Run the app
app_page()