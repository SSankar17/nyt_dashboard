import streamlit as st
import pandas as pd
import altair as alt 
from datetime import datetime

#
try:
    from config import API_KEY
    import get_data
    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.nyt_bestsellers
    historical_collection = db['books_historical']

    if not callable(getattr(get_data, 'get_all_historical_books', None)):
         st.error("Error: 'get_all_historical_books' function not found in get_data module.")
         LOAD_SUCCESS = False
    else:
        LOAD_SUCCESS = True
except ImportError:
    st.error("Error: Could not import 'config.py' or 'get_data.py'. Please ensure they are in the same directory.")
    LOAD_SUCCESS = False
except Exception as e:
    st.error(f"Error connecting to MongoDB or initializing: {e}")
    LOAD_SUCCESS = False


#data loading
@st.cache_data
def load_timeseries_data():
    """Loads and calculates annual performance metrics for time series."""
    if not LOAD_SUCCESS:
        return pd.DataFrame(), pd.DataFrame()

    try:
        df = get_data.get_all_historical_books()
    except Exception as e:
        st.error(f"Error executing get_all_historical_books: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    #data transformation logic from notebook
    df['bestsellers_date'] = pd.to_datetime(df['bestsellers_date'])
    df['year'] = df['bestsellers_date'].dt.year
    df['author_type'] = 'Single-Authored'
    df.loc[df['author'].str.contains(' and ', case=False, na=False), 'author_type'] = 'Co-Authored'

    #group by Year and Author Type, calculating the mean of the metrics
    df_grouped = df.groupby(['year', 'author_type'])[['rank', 'weeks_on_list']].mean().reset_index()

    # Pivot the data
    rank_ts = df_grouped.pivot(index='year', columns='author_type', values='rank')
    weeks_ts = df_grouped.pivot(index='year', columns='author_type', values='weeks_on_list')

    return rank_ts, weeks_ts


#Plotting Function (NOW USING ALTAIR)

def plot_timeseries(rank_ts, weeks_ts, year_range):
    """Generates two side-by-side line graphs for time series analysis based on year range using Altair."""

    start_year, end_year = year_range
    rank_ts_filtered = rank_ts.loc[start_year:end_year]
    weeks_ts_filtered = weeks_ts.loc[start_year:end_year]

    # --- 1. MELT and COMBINE for Altair's Long Format ---
    
    rank_melted = rank_ts_filtered.reset_index().melt(
        id_vars='year', 
        value_vars=rank_ts_filtered.columns,
        var_name='Author_Type', 
        value_name='Average_Rank'
    )
    
    weeks_melted = weeks_ts_filtered.reset_index().melt(
        id_vars='year', 
        value_vars=weeks_ts_filtered.columns,
        var_name='Author_Type', 
        value_name='Average_Weeks_on_List'
    )
    
    combined_df = pd.merge(rank_melted, weeks_melted, on=['year', 'Author_Type'])

    # --- 2. ALTAIR CHART GENERATION ---
    
    # Use quantitative axis for dynamic spacing, and apply integer formatting ('d')
    base = alt.Chart(combined_df).encode(
        x=alt.X('year:Q', title='Year', axis=alt.Axis(format='d'))
    )
    
    # Define color scale once
    color_scale = alt.Scale(domain=['Single-Authored', 'Co-Authored'], range=['#5B5EA6', '#E36499'])

    # Plot 1: Average Rank Over Time (Lower is Better) - Suppress legend
    rank_chart = base.mark_line(point=True).encode(
        y=alt.Y('Average_Rank:Q', 
                title='Average Rank (Lower is Better)',
                scale=alt.Scale(domain=[15, 1])),
        # FIX: Removed the incorrect ** and kept legend=None
        color=alt.Color('Author_Type:N', title='Authorship', scale=color_scale, legend=None),
        tooltip=[alt.Tooltip('year:Q', format='d'), 'Author_Type:N', alt.Tooltip('Average_Rank:Q', format='.2f')]
    ).properties(
        title='Average Book Ranking (YoY)',
        width=350 
    ).interactive()


    # Plot 2: Average Weeks on List Over Time - Define legend (appears on the right)
    weeks_chart = base.mark_line(point=True).encode(
        y=alt.Y('Average_Weeks_on_List:Q', title='Average Weeks on List'),
        color=alt.Color('Author_Type:N', title='Authorship', scale=color_scale),
        tooltip=[alt.Tooltip('year:Q', format='d'), 'Author_Type:N', alt.Tooltip('Average_Weeks_on_List:Q', format='.2f')]
    ).properties(
        title='Average Weeks on List (YoY)',
        width=350 
    ).interactive()

    
    # Combine the two plots side-by-side
    final_chart = alt.hconcat(rank_chart, weeks_chart).resolve_scale(color='independent')
    
    st.altair_chart(final_chart, use_container_width=True)

#Streamlit app layout

st.title("Analyzing a Decade of NYT Bestseller Author Performance")
st.write("**Author: Abigail Neoma**")

st.markdown("In this section, we will investigate whether single-authored books or co-authored books "
"perform better on the NYT Bestseller List. We based this analysis on three measures: the average number of"
" weeks a book spent on the NYT Bestsellers list, its average rank, and total number of book entries grouped by "
"author type.")

st.markdown("**Data Scope:** We fetched data spanning from 2015 to 2025. The performance of each book "
"type (single-authored and co-authored) is quantified by the average of all its appearances on the "
"bestseller lists within the past decade.")

st.markdown("Our research on single-authored versus co-authored books offers actionable, data-driven "
"answers for the entire industry. It shows publishers how to prioritize resource allocation, helps authors "
"set realistic career goals, and tells marketers how long to keep a campaign running based on a book's "
"financial potential.")

# 1. Load Data
rank_ts, weeks_ts = load_timeseries_data()

if not rank_ts.empty:
    # Get min/max years for the slider
    min_year = int(rank_ts.index.min())
    max_year = int(rank_ts.index.max())

    # 2. Create the Slider Widget
    year_range = st.slider(
        "Select Year Range:",
        min_value=2015,
        max_value=2025,
        value=(2015, 2025),
        step=1,
        help="Drag the endpoints to select the time period to visualize."
    )

    # 3. Plot the dynamic data
    plot_timeseries(rank_ts, weeks_ts, year_range)
    st.header("Key Findings")
    st.markdown("Based on our analysis, we found that over the past decade (2015-2025), the NYT Bestseller List data suggests a clear performance difference between single-authored and co-authored books.")
    st.markdown("Co-authored titles demonstrated a slight edge in initial market reception, achieving a marginally better average rank of _7.66_ (versus _7.68_ for single-authored books). "
    "However, when we take a granular-level look at the rankings, single-authored books mostly performed better. This indicates that the overall **.02** difference in rank did not translate into "
    "sustained success for co-authored books. Moreover, the single-authored category not only accounted for the vast majority of entries (2,865 vs. 245 for co-authored), but also showed dramatically "
    "superior longevity, enduring for _33.09_ weeks on average, while co-authored books lasted only _11.81_ weeks.")
    st.header("For Authors")
    st.markdown("The analysis helps authors set realistic expectations and develop strong career strategies. Authors considering collaboration can use the data to understand the trade-offs: while "
    "co-authored books benefit from combined platforms for a strong initial push, they face much tougher odds for sustained, career-defining success on the bestseller list. The data empowers authors to ")
    st.markdown("structure their work to align with their commercial goals—whether that's a quick, high-profile splash or long-term visibility.")
    st.header("Marketing Recommendations")
    st.markdown("**Investment in Author Brand:** Since single-authored books dominate the list and exhibit high longevity, publishing houses should intensify their investment in developing the personal brand and "
    "platform of solo authors. This effort acts as a sustainable marketing asset that drives sales throughout the book's long lifecycle.")
    st.markdown("**Targeted Sales Channels:** Given their higher initial average rank but lower longevity, co-authored books should prioritize high-volume, front-list sales channels (e.g., corporate bulk deals, "
    "specialized industry events, or exclusive retailer partnerships) to capitalize on the initial market 'bursts' before the book naturally drops off the list.")

else:
    st.warning("Could not load time series data.")