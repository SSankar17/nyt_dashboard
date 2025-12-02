# Analyzing the NYT Bestseller List: A Data Engineering Project

**Group 2:** Sanjana Sankar, Kelly Lyons, Alisha Gunadharma Hartarto, Abigail Neoma, Leanne Chung, Yoojeong Seo 

**Course:** APAN 5400 Data Engineering 

## Overview

This project focuses on building a data engineering pipeline to extract, transform, load, and analyze data from the **New York Times (NYT) Best Sellers list** using the [NYT API](https://developer.nytimes.com/docs/books-product/1/overview). Our goal is to provide valuable insights into national reading trends, bestseller success drivers, and book performance for major publishing houses and authors. The NYT Best Sellers list is published every Wednesday and ranks top-selling books in the United States, categorized by format (e.g., hardcover, e-book) and genre (e.g., Fiction, Nonfiction, Children's).

## Research Questions

The analysis aims to answer the following key questions:

1.  Which book attributes have the strongest association with placement on the NYT bestseller list?
2.  Which publishers have books that consistently remain at the top of the list versus those that fluctuate often?
3.  What is the relationship between a book's description, the overall sentiment, and its genre? 
4.  Are there identifiable seasonal trends or social events that influence list rankings?
5.  When many major publishers launch at the same time, does heavy competition on a bestseller list’s debut lead to shorter lifespans for books on that list? 
6.  How do co-authored books perform compared to single-author books on the NYT Best Sellers list? 

## Technologies Utilized

The project utilizes a unified Python-centric environment for data workflow, connecting to various storage and visualization tools.

| Tool | Purpose | Reasoning/Details |
| :--- | :--- | :--- |
| **Python**  | Data Extraction, Transformation, and Analysis (ETL) | Provides a unified environment for API extraction, ETL pipelines, and analysis, with seamless integration capabilities |
| **Neo4j** | Visualizing our Data | Provides an effective method of visualizing relationsips between attributes and entitiies in the API.  |
| **MongoDB (NoSQL)**  | Semi-Structured Data Storage | Offers flexibility to handle nested JSON objects directly from the NYT Books API without strict schemas. Ideal for large, evolving datasets. |
| **Streamlit** | Interactive User Interface / Consumption | Deploys an interactive dashboard for non-technical audiences to explore insights and visualizations without coding. |

## Data Source & Procurement

### Source Details
* **Data Source:** [New York Times Developer API (Books API)](https://developer.nytimes.com/docs/books-product/1/overview).
* **Format:** JSON via HTTP GET requests.
* **Data Coverage:** Weekly and monthly rankings across categories like Fiction, Nonfiction, and Children's Books.
* **Data Timeframe:** Varies but generally from January 2019 to October 2025, with some research questions exploring longer or shorter timeframes.
* **Approximate DataFrame Size:** 1.36 GB.

### Procurement Strategy
1.  **Access Method:** Conduct REST API calls using the NYT Developer Portal.
2.  **Challenge:** API key creation is limited (one week per call) and subject to rate limits.
3.  **Solutions:**
    * Store data locally in a NoSQL database (MongoDB).
    * Procure data by converting API information to CSV for certain investigations.

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
* **MongoDB and Neo4j:** Insert JSON files directly into MongoDB and Neo4j using the `nyt_api.ipynb` and `get_neo4j_data.ipynb` notebooks.

### 4. Consumption 
* **Deployment:** Format the data into actionable insights using **Python** and deploy a user interface using **Streamlit** in the command line to provide dynamic dashboards and interactive data display.

## Scalability and Future Work

Future plans involve scaling the product for larger publishing companies to predict or forecast upcoming book performance.

* **Cloud Providers:** Utilize **AWS** and/or **Microsoft Azure**.
* **Visualization:** Transition to **Tableau** or **PowerBI**.
* **Storage:** Use cloud data lakes (Amazon S3, Google Cloud Storage) for raw and processed datasets, and scale structured data with PostgreSQL.
* **Automation:** Implement ETL automation using serverless batch jobs via **AWS Lambda** or **Google Cloud Functions** to periodically update data.
* **Advanced Analytics:** Deploy analytical modeling on platforms like **Google Colab** or **Vertex AI**.
