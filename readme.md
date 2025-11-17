# Analyzing the NYT Bestseller List: A Data Engineering Project

**Group 2:** Sanjana Sankar, Kelly Lyons, Alisha Gunadharma Hartarto, Abigail Neoma, Leanne Chung, Yoojeong Seo 

**Course:** APAN 5400 Data Engineering 

## Overview

This project focuses on building a data engineering pipeline to extract, transform, load, and analyze data from the **New York Times (NYT) Best Sellers list**. The goal is to provide valuable insights into national reading trends, bestseller success drivers, and book performance for publishers and authors. The NYT Best Sellers list is published every Wednesday and ranks top-selling books in the United States, categorized by format (e.g., hardcover, e-book) and genre (e.g., Fiction, Nonfiction, Children's).

## Research Questions

The analysis aims to answer the following key questions:

1.  Which book attributes have the strongest association with placement on the NYT bestseller list?
2.  Which publishers have books that consistently remain at the top of the list versus those that fluctuate often?
3.  What is the relationship between a book's description, the overall sentiment, and its genre? 
4.  How do critical reviews (online and Sunday book reviews) correlate with bestseller performance? 
5.  Are there identifiable seasonal trends or social events that influence list rankings?
6.  How do co-authored books perform compared to single-author books on the NYT Best Sellers list? 

## Technology Stack

The project utilizes a unified Python-centric environment for data workflow, connecting to various storage and visualization tools.

| Tool | Purpose | Reasoning/Details |
| :--- | :--- | :--- |
| **Python**  | Data Extraction, Transformation, and Analysis (ETL) | Provides a unified environment for API extraction, ETL pipelines, and analysis, with seamless integration capabilities |
| **PostgreSQL (SQL)** [cite: 163] | Structured Data Storage/Load Option A | Enables fast, relational queries to aggregate metrics like "average weeks on list per publisher". |
| **MongoDB (NoSQL)**  | Semi-Structured Data Storage/Load Option B | Offers flexibility to handle nested JSON objects directly from the NYT Books API without strict schemas. Ideal for large, evolving datasets. |
| **Streamlit** | Interactive User Interface / Consumption | Deploys an interactive dashboard for non-technical audiences to explore insights and visualizations without coding. |

## Data Source & Procurement

### Source Details
* **Data Source:** New York Times Developer API (Books API).
* **Format:** JSON via HTTP GET requests.
* **Data Coverage:** Weekly and monthly rankings across categories like Fiction, Nonfiction, and Children's Books.
* **Data Timeframe:** January 2019 to October 2025.
* **Approximate DataFrame Size:** 1.36 GB.

### Procurement Strategy
1.  **Access Method:** Conduct REST API calls using the NYT Developer Portal.
2.  **Challenge:** API key creation is limited (one week per call) and subject to rate limits.
3.  **Solutions:**
    * Store data locally in a SQL or NoSQL database.
    * Procure data by converting API information to CSV.
4.  **Data Validation:** Implement procedures to check for duplicates, missing timestamps, and inaccurate data types.

## ETL Pipeline

The project follows a standard Extract, Transform, Load (ETL) process:

### 1. Extract 
* **Source:** NYT Books API.
* **Method:** HTTP GET requests for JSON data (e.g., `https://api.nytimes.com/svc/books/v3/lists/overview.json?api-key=yourkey`).

### 2. Transform 
* **Tool:** Python.
* **Steps:**
    * Parse the initial JSON response.
    * Normalize nested data structures.
    * Select and rename key columns (e.g., Title, Author, Ranking).
    * Manage missing values.
    * Format data types.

### 3. Load 
* **Option A (NoSQL):** Insert JSON files directly into MongoDB.
* **Option B (SQL):** Load data as a table named "books" (with columns like Title, Author, Rank) into PostgreSQL.

### 4. Consumption 
* **Deployment:** Deploy a user interface using **Streamlit** to provide dynamic dashboards and interactive data display.

## Scalability and Future Work

Future plans involve scaling the product for larger publishing companies to predict or forecast upcoming book performance.

* **Cloud Providers:** Utilize **AWS** and/or **Microsoft Azure**.
* **Visualization:** Transition to **Tableau** or **PowerBI**.
* **Storage:** Use cloud data lakes (Amazon S3, Google Cloud Storage) for raw and processed datasets, and scale structured data with PostgreSQL.
* **Automation:** Implement ETL automation using serverless batch jobs via **AWS Lambda** or **Google Cloud Functions** to periodically update data.
* **Advanced Analytics:** Deploy analytical modeling on platforms like **Google Colab** or **Vertex AI**.