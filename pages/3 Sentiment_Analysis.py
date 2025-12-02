import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
import altair as alt # Added Altair import
import seaborn as sns
from textblob import TextBlob
from scipy import stats
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from collections import Counter

from PIL import Image
from pymongo import MongoClient 

Image.MAX_IMAGE_PIXELS = None

# MONGO DB CONNECTION AND DATA RETRIEVAL 

@st.cache_resource
def init_mongo_collection():
    """Initializes and caches the MongoDB connection and returns the historical collection."""
    # NOTE: Ensure your MongoDB server is running on localhost:27017
    client = MongoClient("mongodb://localhost:27017/")
    db = client['nyt_bestsellers']
    # Returning the historical collection object
    return db['books_historical']

@st.cache_data
def get_all_historical_books():
    """
    Retrieves all book data from the MongoDB historical collection,
    and cleans it to prevent Streamlit caching errors.
    """
    historical_collection = init_mongo_collection()
    try:
        cursor = historical_collection.find().sort('bestsellers_date', -1)
        df = pd.DataFrame(list(cursor))
        
        # FIX 1: Drop the unhashable MongoDB default ID
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
            
        # FIX 2: Convert any remaining complex object columns (like lists/dicts) to strings.
        for col in df.select_dtypes(include=['object']).columns:
            if not pd.api.types.is_string_dtype(df[col]):
                 df[col] = df[col].astype(str)
                 
        return df
    except Exception as e:
        # Print error to console for debugging database issues
        print(f"MongoDB Data Retrieval Error: {e}") 
        return pd.DataFrame() # Return empty DataFrame on failure


# HELPER FUNCTIONS 

@st.cache_data
def perform_sentiment_analysis(df):
    """
    Applies the exact sentiment analysis logic from nyt_api.py
    """
    def analyze_sentiment(description):
        if pd.isna(description) or str(description).strip() == '':
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'category': 'Neutral'
            }

        blob = TextBlob(str(description))
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        # Categorize sentiment
        if polarity > 0.1:
            category = 'Positive'
        elif polarity < -0.1:
            category = 'Negative'
        else:
            category = 'Neutral'

        return {
            'polarity': round(polarity, 3),
            'subjectivity': round(subjectivity, 3),
            'category': category
        }

    sentiment_results = df['description'].apply(analyze_sentiment)
    
    df['sentiment_polarity'] = sentiment_results.apply(lambda x: x['polarity'])
    df['sentiment_subjectivity'] = sentiment_results.apply(lambda x: x['subjectivity'])
    df['sentiment_category'] = sentiment_results.apply(lambda x: x['category'])
    
    return df

# genre key mapping
def get_genre_mapping():
    """
    Returns a comprehensive mapping of NYT list names (slugs and human-readable)
    to standardized top-level genres.
    """
    return {
        # fiction categories
        'combined-print-and-e-book-fiction': 'Fiction',
        'hardcover-fiction': 'Fiction',
        'paperback-trade-fiction': 'Fiction',
        'e-book-fiction': 'Fiction',
        'mass-market-paperback-fiction': 'Fiction',
        'trade-fiction-paperback': 'Fiction',
        
        # nonfiction categories
        'combined-print-and-e-book-nonfiction': 'Nonfiction',
        'hardcover-nonfiction': 'Nonfiction',
        'paperback-nonfiction': 'Nonfiction',
        'e-book-nonfiction': 'Nonfiction',
        'science': 'Nonfiction',
        'travel': 'Nonfiction',
        'religion-spirituality-and-faith': 'Nonfiction',
        
        # advice
        'advice-how-to-and-miscellaneous': 'Advice',
        'advice-and-how-to': 'Advice',
        'food-and-fitness': 'Advice',
        'sports': 'Advice',
        'health': 'Advice',
        
        # YA
        'series-books': 'Young Adult',
        'young-adult-hardcover': 'Young Adult',
        'young-adult-paperback': 'Young Adult',
        'young-adult': 'Young Adult',
        
        # Childrens
        'picture-books': 'Children',
        'childrens-picture-books': 'Children',
        'childrens-middle-grade': 'Children',
        'childrens-chapter-books': 'Children',
        'middle-grade-paperback-series': 'Children',
        'middle-grade-hardcover': 'Children',
        
        # specific
        'business-books': 'Business',
        'hardcover-business': 'Business',
    }

def get_genre_order():
    """Restricts the application to only plot Fiction and Nonfiction."""
    return ['Fiction', 'Nonfiction']

# PAGE CONFIGURATION

st.set_page_config(
    page_title="NYT Best Sellers Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# ANALYSIS & VISUALIZATIONS

app_mode = "Analysis & Visualizations"

if app_mode == "Analysis & Visualizations":
    st.title("What is the relationship between a book’s description, the overall sentiment, and genre?")
    st.write("Author: Yoojeong Seo")
    
    # Load Data 
    with st.spinner("Loading data from MongoDB..."):
        try:
            df = get_all_historical_books()
            
            if df.empty:
                st.warning("No data found in MongoDB...")
                st.stop()
                
            df['bestsellers_date'] = pd.to_datetime(df['bestsellers_date'])
            
            # CRITICAL FIX: Ensure 'weeks_on_list' is a numeric type for plotting
            df['weeks_on_list'] = pd.to_numeric(df['weeks_on_list'], errors='coerce') 
            
        except Exception as e:
            st.error(f"Error loading data: {e}. Check your MongoDB connection string and server status.")
            st.stop()
            
    # Pre-processing (Genre & Sentiment)
    with st.spinner("Processing sentiment analysis..."):
        genre_mapping = get_genre_mapping()
        # Non-Fiction/Fiction lists get a genre, others get NaN (which is fine)
        df['genre'] = df['list_name'].map(genre_mapping)
        genre_order = get_genre_order()
        # This Categorical assignment filters the data down to only the listed genres
        df['genre'] = pd.Categorical(df['genre'], categories=genre_order, ordered=True)
        
        # Apply Sentiment (Cached function)
        df = perform_sentiment_analysis(df)

    
    # Tabs for Visualizations
    tab1, tab2, tab3, tab4 = st.tabs([
        "Donut Charts", 
        "Ridge Plot", 
        "Bar Chart", 
        "Scatter Plot & Regression"
    ])

    # VISUALIZATION 1: DONUT CHARTS (FIXED SUBPLOTS)
    with tab1:
        st.subheader("Donut Charts: Sentiment Distribution by Genre")
        
        # Data Prep
        genre_sentiment = df.groupby('genre', observed=False).agg({
            'sentiment_polarity': 'mean',
            'sentiment_subjectivity': 'mean',
            'title': 'count'
        }).round(3)
        genre_sentiment.columns = ['avg_polarity', 'avg_subjectivity', 'total_books']
        
        genre_sentiment['positive_pct'] = 0.0
        genre_sentiment['neutral_pct'] = 0.0
        genre_sentiment['negative_pct'] = 0.0

        for genre in genre_sentiment.index:
            genre_df = df[df['genre'] == genre]
            total = len(genre_df)
            if total > 0:
                genre_sentiment.loc[genre, 'positive_pct'] = round((genre_df['sentiment_category'] == 'Positive').sum() / total * 100, 1)
                genre_sentiment.loc[genre, 'neutral_pct'] = round((genre_df['sentiment_category'] == 'Neutral').sum() / total * 100, 1)
                genre_sentiment.loc[genre, 'negative_pct'] = round((genre_df['sentiment_category'] == 'Negative').sum() / total * 100, 1)

        # Plotting (Changed to 1 row, 2 columns)
        colors = ['#FC6060', '#ADB2BD', '#588EFA']
        
        def autopct_format(pct):
            return f'{pct:.1f}%' if pct > 1.0 else ''

        # Only 1 row and 2 columns needed for Fiction and Nonfiction
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes = axes.flatten()

        for idx, genre in enumerate(genre_order): # genre_order is now ['Fiction', 'Nonfiction']
            ax = axes[idx]
            if genre not in genre_sentiment.index:
                ax.axis('off'); continue

            book_count = int(genre_sentiment.loc[genre, 'total_books']) 
            
            if book_count == 0:
                ax.text(0, 0, f'{genre}\n(No data)', ha='center', va='center',
                        fontsize=13, fontweight='bold', color='gray',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='lightgray', linewidth=1, alpha=0.8))
                ax.axis('off')
                continue
            
            data = [
                genre_sentiment.loc[genre, 'positive_pct'],
                genre_sentiment.loc[genre, 'neutral_pct'],
                genre_sentiment.loc[genre, 'negative_pct']
            ]

            wedges, texts, autotexts = ax.pie(
                data, colors=colors, autopct=autopct_format, startangle=90, pctdistance=0.8,
                wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
                textprops={'fontsize': 11, 'fontweight': 'bold', 'color': 'black'}
            )
            ax.text(0, 0, f'{genre}\n({book_count} books)', ha='center', va='center',
                    fontsize=13, fontweight='bold', color='black',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='lightgray', linewidth=1, alpha=0.8))
        
        legend_elements = [
            mpatches.Patch(facecolor="#FC6060", edgecolor='black', linewidth=1, label='Positive'),
            mpatches.Patch(facecolor="#ADB2BD", edgecolor='black', linewidth=1, label='Neutral'),
            mpatches.Patch(facecolor="#588EFA", edgecolor='black', linewidth=1, label='Negative')
        ]
        fig.legend(handles=legend_elements, loc='center right', fontsize=13, title='Sentiment Categories', bbox_to_anchor=(0.98, 0.5))
        fig.suptitle('Sentiment Distribution by Genre (Fiction & Nonfiction)\nNYT Best Sellers Analysis', fontsize=16, fontweight='bold', y=1.05)
        plt.tight_layout()
        plt.subplots_adjust(right=0.88, top=0.9)
        
        st.pyplot(fig)
        
        st.markdown("---")
        st.markdown("#### Donut Charts: Sentiment Distribution by Genre")
        st.markdown("""
        The donut charts illustrate the distribution of sentiment categories (Positive, Neutral, Negative) across Fiction and Nonfiction book genres in the NYT Best Sellers list.
        
        **Key Observations:**
        - Neutral sentiment dominate for both genres. Based on the chart, bestseller descriptions maintain a balanced and informational tone.
        - For fiction, it shows a higher negative sentiment compared to Nonfiction (10.3%). And it illustrates a more balanced spread between positive and negative descriptions.
        """)
    with tab2:
        st.subheader("Ridge Plot: Weeks on List by Genre")
        
        genre_colors = {
            'Fiction': '#E74C3C', 'Nonfiction': '#3498DB', 
        }
        # Only use Fiction and Nonfiction
        plot_genres = ['Fiction', 'Nonfiction']

        fig = plt.figure(figsize=(14, 8))
        # Grid now only has 2 rows (one for each genre)
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.3) 
        axes = [fig.add_subplot(gs[i, 0]) for i in range(2)]

        def create_gradient_fill(ax, x_range, density, color):
            light_color = mcolors.to_rgba(color, alpha=0.3)
            dark_color = mcolors.to_rgba(color, alpha=0.8)
            cmap = mcolors.LinearSegmentedColormap.from_list('custom', [light_color, dark_color], N=256)
            norm = mcolors.Normalize(vmin=x_range.min(), vmax=x_range.max())
            for i in range(len(x_range)-1):
                ax.fill_between(x_range[i:i+2], density[i:i+2], color=cmap(norm(x_range[i])), linewidth=0)

        def plot_genre_ridge(ax, genre, color, show_xticks=False):
            if genre not in df['genre'].values: return 0
            data = df[df['genre'] == genre]['weeks_on_list'].dropna()
            if len(data) == 0: return 0

            if len(data) < 2 or data.std() == 0:
                ax.text(0.5, 0.5, f'Not enough data for {genre}', 
                        transform=ax.transAxes, ha='center', va='center', 
                        fontsize=12, color='gray')
                return 0

            kde = stats.gaussian_kde(data)
            x_max = max(data.max() + 10, 50)
            x_range = np.linspace(0, x_max, 500)
            density = kde(x_range)

            create_gradient_fill(ax, x_range, density, color)
            ax.plot(x_range, density, color=color, linewidth=3, zorder=3)
            
            mean_val = data.mean()
            median_val = data.median()
            
            # Vertical lines
            ax.axvline(mean_val, color='darkred', linestyle='--', linewidth=2.5, alpha=0.9, zorder=4)
            ax.axvline(median_val, color='darkblue', linestyle=':', linewidth=2.5, alpha=0.9, zorder=4)
            
            # Vertical Labels at Bottom
            y_pos = -0.15
            ax.text(mean_val, y_pos, f'{mean_val:.1f}',
                    transform=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=11, fontweight='bold',
                    color='darkred',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                             edgecolor='darkred', linewidth=2, alpha=0.95))

            ax.text(median_val, y_pos, f'{median_val:.1f}',
                    transform=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=11, fontweight='bold',
                    color='darkblue',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                             edgecolor='darkblue', linewidth=2, alpha=0.95))

            ax.set_ylabel(genre, fontsize=14, fontweight='bold', rotation=0, ha='right', va='center', labelpad=30)
            
            # Styling
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.set_ylim(0, density.max() * 1.15)
            
            ax.text(0.98, 0.90, f'Mean: {mean_val:.1f}\nMedian: {median_val:.1f}\nn={len(data)}',
                    transform=ax.transAxes, ha='right', va='top',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.95, edgecolor=color, linewidth=2.5),
                    fontsize=11, fontweight='bold')
            
            if not show_xticks:
                ax.set_xticklabels([])
            else:
                 ax.tick_params(axis='x', labelsize=11)
                 
            ax.set_xlim(0, x_max)
            return x_max

        # Logic to plot only the two main groups
        max_x = 0
        for i, genre in enumerate(plot_genres):
            # Only show x-ticks on the last plot
            x_max = plot_genre_ridge(axes[i], genre, genre_colors[genre], (i == len(plot_genres) - 1))
            if x_max: max_x = max(max_x, x_max)
        
        # Ensure all plots share the same max x-limit
        if max_x > 0:
            for ax in axes: ax.set_xlim(0, max_x)
        
        # Legend
        legend_elements = [
            Line2D([0], [0], color='darkred', linestyle='--', linewidth=2.5, label='Mean'),
            Line2D([0], [0], color='darkblue', linestyle=':', linewidth=2.5, label='Median')
        ]
        
        axes[0].legend(handles=legend_elements, 
                              loc='lower right', 
                              bbox_to_anchor=(1.0, 1.15), 
                              fontsize=10, 
                              frameon=True, shadow=True, fancybox=True, edgecolor='black')

        fig.suptitle('Weeks on List by Genre \nNYT Best Sellers Analysis', fontsize=15, fontweight='bold', y=0.995)
        plt.subplots_adjust(left=0.15, bottom=0.1) 
        
        st.pyplot(fig)
        st.markdown("---")
        st.markdown("#### Ridge Plot: Weeks on List by Genre")
        st.markdown("**Key Observations:**")
        st.markdown("The ridge plot visualizes the distribution of weeks on the bestseller list by genre.")
        st.markdown("• Nonfiction tends to stay on the bestseller list significantly longer, as both its mean and median values are much higher than those of Fiction.")
        st.markdown("• Both genres have very low median values, which means most books drop off the bestseller list quickly.")
    
    
    # VISUALIZATION 3: BAR CHART 
    with tab3:
        st.subheader("Bar Chart: Positive vs Negative by Weeks (All Genres)")
        
        # 1. Prepare Data
        # Filter for only Positive and Negative sentiment books
        df_filtered = df[df['sentiment_category'].isin(['Positive', 'Negative'])].copy()
        
        # Define bins for weeks on list
        week_bins = [
            (0, 5, '0-5 weeks'),
            (5, 10, '5-10 weeks'),
            (10, 15, '10-15 weeks'),
            (15, 30, '15-30 weeks'),
            (30, 50, '30-50 weeks'),
            (50, 100, '50-100 weeks'),
            (100, float('inf'), '100+ weeks') # Use infinity for the last bin
        ]

        # Function to categorize weeks into bins
        def assign_week_bin(weeks):
            for min_week, max_week, label in week_bins:
                if weeks >= min_week and weeks < max_week:
                    return label
            return 'Other' # Should not happen if all bins cover the range

        df_filtered['weeks_on_list_bin'] = df_filtered['weeks_on_list'].apply(assign_week_bin)
        
        # 2. Aggregate Data for Altair
        # Count the number of books in each bin/sentiment category
        bar_data = df_filtered.groupby(['weeks_on_list_bin', 'sentiment_category'], observed=True).size().reset_index(name='count')
        
        # Add the full labels to ensure correct sorting in Altair
        bin_labels_order = [label for _, _, label in week_bins]
        
        # 3. Define Colors
        sentiment_colors = {
            'Positive': '#FC6060',  # Red
            'Negative': '#588EFA',  # Blue
        }

        # 4. Create Altair Chart
        base = alt.Chart(bar_data).encode(
            # Y-axis is the week bin, sorted explicitly
            y=alt.Y('weeks_on_list_bin', 
                    sort=bin_labels_order, 
                    title='Weeks on Bestseller List (Time Range)'),
            # Tooltip for interactivity
            tooltip=['weeks_on_list_bin', 'sentiment_category', 'count']
        )
        
        # Create the stacked bar chart (stacking is default when column is removed)
        chart = base.mark_bar().encode(
            x=alt.X('count', title='Number of Books'),
            # Color based on sentiment category, which dictates the stacking layers
            color=alt.Color('sentiment_category', 
                            scale=alt.Scale(domain=list(sentiment_colors.keys()), 
                                            range=list(sentiment_colors.values())),
                            legend=alt.Legend(title="Sentiment Category")),
        ).properties(
            title='Distribution by Weeks on Bestseller List (Positive vs. Negative Sentiment)'
        ).configure_title(
            fontSize=18,
            anchor='middle',
            color='#333333'
        ).configure_axis(
            labelFontSize=11,
            titleFontSize=13,
            grid=True
        ).interactive() # Enable zooming/panning
        
        # Display the chart in Streamlit
        st.altair_chart(chart, use_container_width=True)


        st.markdown("#### Bar Chart: Positive vs Negative by Weeks")
        st.markdown("The bar chart, now visualized using Altair, illustrates the comparison between the number of books with positive and negative sentiments based on different time ranges on the bestseller list.")
        st.markdown("**Key Observations:**")
        st.markdown("• First 10 weeks: The number of books with Positive and Negative sentiments are relatively balanced")
        st.markdown("• Negative sentiment books drop off significantly after 15 weeks")
        st.markdown("• Positive sentiment books tend to have longer durations on the list compared to negative sentiment books")

    # VISUALIZATION 4: SCATTER & REGRESSION (FIXED SUBPLOTS)
    with tab4:
        st.subheader("04. Scatter Plot by Genre with Regression Analysis")
        
        genre_colors = {
            'Fiction': '#E74C3C', 'Nonfiction': '#3498DB', 
        }
        # Only iterate over Fiction and Nonfiction
        genres = ['Fiction', 'Nonfiction'] 

        # Changed to 1 row, 2 columns
        fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        axes = axes.flatten()

        for idx, genre in enumerate(genres):
            ax = axes[idx]
            if genre not in df['genre'].values:
                ax.axis('off'); continue

            genre_df = df[df['genre'] == genre].copy()
            if len(genre_df) > 300: genre_df = genre_df.sample(300)

            x = genre_df['sentiment_polarity'].values
            y = genre_df['weeks_on_list'].values

            ax.scatter(x, y, alpha=0.5, s=40, color=genre_colors[genre], edgecolors='white', linewidth=0.5, zorder=3)

            if len(x) > 1 and np.std(x) > 1e-6:
                try:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                    r_squared = r_value ** 2
                    
                    sig_text = 'sig' if p_value < 0.05 else 'non-sig'
                    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\n{sig_text}'

                    # Plot the regression line if significant
                    if p_value < 0.05:
                        x_line = np.array([x.min(), x.max()])
                        y_line = slope * x_line + intercept
                        ax.plot(x_line, y_line, color='darkred', linewidth=2.5, linestyle='--', alpha=0.8, zorder=4)
                    
                    ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor=genre_colors[genre], linewidth=2), zorder=6)
                except ValueError:
                    pass
            ax.set_title(f'{genre}', fontsize=13, fontweight='bold', color=genre_colors[genre])
            ax.set_facecolor('#F9F9F9')

        fig.suptitle('Sentiment vs Success by Genre (Fiction & Nonfiction) with Regression Analysis\nNYT Best Sellers Analysis', fontsize=16, fontweight='bold', y=1.05)
        plt.tight_layout()
        plt.subplots_adjust(top=0.9) 
        
        st.pyplot(fig)
        st.markdown("---")
        st.markdown("#### Scatter Plot by Genre with Regression Analysis")
        st.markdown("**Key Observations:**")
        st.markdown("The scatter plots illustrate the relationship between sentiment polarity of book descriptions and their longevity on the bestseller list for Fiction and Nonfiction.")
        st.markdown(" • Positive r indicates higher sentiment scores are related to More weeks on list, whereas negative r indicates the opposite.")
        st.markdown(" • You can now observe if there is any relationship between a book's description sentiment and its longevity specifically within the two largest categories.")
