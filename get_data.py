# NYT Best Sellers API with MongoDB - Jupyter Notebook

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
import requests
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
from config import API_KEY #create a file named config.py and add your NYT API key there

BASE_URL = "https://api.nytimes.com/svc/books/v3"

# connecting to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['nyt_bestsellers']
books_collection = db['books']
historical_collection = db['books_historical']  


# NYT data API functions

def get_lists_names():
    """Get all available best seller list names"""
    # Get the full overview which includes all lists
    overview = get_full_overview()
    if overview and 'lists' in overview:
        return overview['lists']
    return None

def get_best_sellers_by_list(list_name, date=None):
    """Get best sellers for a specific list"""
    if date:
        url = f"{BASE_URL}/lists/{date}/{list_name}.json"
    else:
        url = f"{BASE_URL}/lists/current/{list_name}.json"
    
    params = {"api-key": API_KEY}
    response = requests.get(url, params=params)
    data = response.json()
    
    # Check if successful
    if data.get('status') == 'OK' and 'results' in data:
        return data['results']
    else:
        # Don't print error, just return None for failed requests
        return None
    
def get_full_overview(date=None):
    """Get all best sellers across all lists"""
    url = f"{BASE_URL}/lists/full-overview.json"
    params = {"api-key": API_KEY}
    if date:
        params['published_date'] = date
    
    response = requests.get(url, params=params)
    data = response.json()
    return data['results']

def fetch_historical_data(list_name, start_date, end_date):
    """Fetch historical data between two dates (weekly intervals)"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    all_data = []
    current_date = start
    
    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Fetching data for {date_str}...")
        
        data = get_best_sellers_by_list(list_name, date_str)
        if data:  # Only add if successful
            all_data.append({'date': date_str, 'data': data})
        
        current_date += timedelta(days=7)  # NYT updates weekly
    
    return all_data

def results_to_dataframe(results, list_name=None):
    """Convert API results to pandas DataFrame"""
    books = results['books']
    flattened_data = []
    
    for book in books:
        flat_book = {
            'list_name': list_name or results.get('list_name', ''),
            'bestsellers_date': results.get('bestsellers_date', ''),
            'published_date': results.get('published_date', ''),
            'rank': book.get('rank'),
            'rank_last_week': book.get('rank_last_week'),
            'weeks_on_list': book.get('weeks_on_list'),
            'title': book.get('title'),
            'author': book.get('author'),
            'publisher': book.get('publisher'),
            'description': book.get('description'),
            'price': book.get('price'),
            'primary_isbn10': book.get('primary_isbn10'),
            'primary_isbn13': book.get('primary_isbn13'),
            'amazon_product_url': book.get('amazon_product_url'),
        }
        flattened_data.append(flat_book)
    
    return pd.DataFrame(flattened_data)

# ============================================================================
# MONGODB FUNCTIONS
# ============================================================================

def store_books_in_mongo(results, list_name=None):
    """Store books data in MongoDB (prevents duplicates)"""
    books = results['books']
    documents = []
    
    for book in books:
        unique_key = {
            'list_name': list_name or results.get('list_name', ''),
            'bestsellers_date': results.get('bestsellers_date', ''),
            'primary_isbn13': book.get('primary_isbn13')
        }

        # if the book already exists in the collection, skip it
        if books_collection.find_one(unique_key):
            continue 
        
        doc = {
            'list_name': list_name or results.get('list_name', ''),
            'bestsellers_date': results.get('bestsellers_date', ''),
            'published_date': results.get('published_date', ''),
            'rank': book.get('rank'),
            'rank_last_week': book.get('rank_last_week'),
            'weeks_on_list': book.get('weeks_on_list'),
            'title': book.get('title'),
            'author': book.get('author'),
            'publisher': book.get('publisher'),
            'description': book.get('description'),
            'price': book.get('price'),
            'primary_isbn10': book.get('primary_isbn10'),
            'primary_isbn13': book.get('primary_isbn13'),
            'amazon_product_url': book.get('amazon_product_url'),
            'fetched_at': datetime.now()
        }
        documents.append(doc)
    
    if documents:
        result = books_collection.insert_many(documents)
        return len(result.inserted_ids)
    return 0

def get_books_by_list(list_name):
    """Retrieve books for a specific list from MongoDB"""
    cursor = books_collection.find({'list_name': list_name}).sort('rank', 1)
    return pd.DataFrame(list(cursor))

def get_books_by_date(date):
    """Retrieve all books for a specific date from MongoDB"""
    cursor = books_collection.find({'bestsellers_date': date})
    return pd.DataFrame(list(cursor))

def get_all_books():
    """Retrieve all books from MongoDB"""
    cursor = books_collection.find().sort('bestsellers_date', -1)
    return pd.DataFrame(list(cursor))

def get_book_history(isbn13):
    """Get historical rankings for a specific book"""
    cursor = books_collection.find({'primary_isbn13': isbn13}).sort('bestsellers_date', 1)
    return pd.DataFrame(list(cursor))

def count_books():
    """Count total books in database"""
    return books_collection.count_documents({})

def get_unique_lists():
    """Get list of all unique list names"""
    return books_collection.distinct('list_name')

def clear_all_books():
    """Clear all books from database (use with caution!)"""
    result = books_collection.delete_many({})
    return result.deleted_count

def store_books_historical(results, list_name=None):
    """Store books data in historical collection with delays"""
    import time
    
    books = results['books']
    documents = []
    
    for book in books:
        unique_key = {
            'list_name': list_name or results.get('list_name', ''),
            'bestsellers_date': results.get('bestsellers_date', ''),
            'primary_isbn13': book.get('primary_isbn13')
        }

        # Check if already exists in historical collection
        if historical_collection.find_one(unique_key):
            continue 
        
        doc = {
            'list_name': list_name or results.get('list_name', ''),
            'bestsellers_date': results.get('bestsellers_date', ''),
            'published_date': results.get('published_date', ''),
            'rank': book.get('rank'),
            'rank_last_week': book.get('rank_last_week'),
            'weeks_on_list': book.get('weeks_on_list'),
            'title': book.get('title'),
            'author': book.get('author'),
            'publisher': book.get('publisher'),
            'description': book.get('description'),
            'price': book.get('price'),
            'primary_isbn10': book.get('primary_isbn10'),
            'primary_isbn13': book.get('primary_isbn13'),
            'amazon_product_url': book.get('amazon_product_url'),
            'fetched_at': datetime.now()
        }
        documents.append(doc)
    
    if documents:
        result = historical_collection.insert_many(documents)
        time.sleep(0.5)  # 0.5 second delay between insertions
        return len(result.inserted_ids)
    return 0

def clear_historical_books():
    """Clear historical collection"""
    result = historical_collection.delete_many({})
    return result.deleted_count

def get_all_historical_books():
    """Retrieve all books from historical collection"""
    cursor = historical_collection.find().sort('bestsellers_date', -1)
    return pd.DataFrame(list(cursor))

def count_historical_books():
    """Count books in historical collection"""
    return historical_collection.count_documents({})