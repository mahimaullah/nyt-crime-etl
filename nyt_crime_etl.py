# Mahima Ullah
# Final project: implementing an ETL process using the NYT Article Search API

import os
import requests
import time
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt  # extra feature to visualize article frequency


# Configuration:
API_KEY = os.environ.get('NYT_API_KEY')
URL = 'https://api.nytimes.com/svc/search/v2/articlesearch.json'
KEYWORD = 'crime'
YEARS_TO_RUN = [2001]
MONTHS_TO_RUN = [9, 10, 11, 12]
PAGES_PER_MONTH = 3          # NYT returns 10 articles per page
REQUEST_PAUSE_SECONDS = 12   
OUTPUT_FILE = 'nyt_crime_articles_2001.csv'

if not API_KEY:
    raise SystemExit(
        "NYT_API_KEY is not set.\n"
        "Get a free key at https://developer.nytimes.com/ then run:\n"
        "  export NYT_API_KEY='your-key-here'"
    )


# Function: Build API URL using parameters
def build_query_params(keyword, begin_date, end_date, page=0):
    return {
        'q': keyword,
        'begin_date': begin_date,
        'end_date': end_date,
        'api-key': API_KEY,
        'page': page
    }


# Function: Extract articles for a specific year
def extract_articles(year):
    """
    Extracts crime-related articles from the NYT API for the given year and selected months.
    Returns a list of article dictionaries.
    """
    articles = []
    for month in MONTHS_TO_RUN:
        # format start and end dates for the month
        begin_date = f"{year}{month:02d}01"
        end_date = (datetime(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        end_date = end_date.strftime("%Y%m%d")

        for page in range(0, PAGES_PER_MONTH):
            print(f"Fetching {year}-{month:02d}, page {page}...")
            params = build_query_params(KEYWORD, begin_date, end_date, page)
            try:
                response = requests.get(URL, params=params)
                if response.status_code != 200:
                    print(f"[{year}-{month:02d} page {page}] Error {response.status_code}: {response.text}")
                    break

                json_data = response.json()
                docs = json_data.get("response", {}).get("docs")
                if not docs:
                    print(f"No docs returned for {begin_date} to {end_date}")
                    break

                # extract and store relevant data from each article
                for doc in docs:
                    articles.append({
                        "pub_date": doc.get("pub_date", "")[:10],
                        "headline": doc.get("headline", {}).get("main", ""),
                        "section": doc.get("section_name", ""),
                        "url": doc.get("web_url", "")
                    })

            except Exception as e:
                print(f"Exception on {begin_date} page {page}: {e}")
                continue

            time.sleep(REQUEST_PAUSE_SECONDS)  # safer rate limit pause
    return articles


# Function: Extract all articles
def extract_all_articles():
    all_articles = []
    for year in YEARS_TO_RUN:
        print(f"Extracting for {year}...")
        yearly_articles = extract_articles(year)
        all_articles.extend(yearly_articles)
    return all_articles


# Function: Transform articles
def transform_articles(raw_articles):
    df = pd.DataFrame(raw_articles)
    if df.empty:
        print("No valid data to transform.")
        return df
    before = len(df)
    df.drop_duplicates(subset=["url"], inplace=True)
    print(f"Deduplicated on url: {before} -> {len(df)} rows")
    df["pub_date"] = pd.to_datetime(df["pub_date"], errors="coerce")
    return df


# Function: Load articles to CSV
def load_to_csv(df, output_path):
    if df.empty:
        print("Nothing to save — DataFrame is empty.")
        return
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} articles to {output_path}")


# Function: Annotate key FBI/policy/crime events
def annotate_events(ax):
    events = {
        '2001-09-11': '9/11 Attacks',
        '2001-10-26': 'Patriot Act Signed',
    }

    for date_str, label in events.items():
        date = pd.to_datetime(date_str)
        ax.axvline(date, color='red', linestyle='--', alpha=0.7)
        ax.text(date, ax.get_ylim()[1] * 0.95, label, rotation=90, fontsize=8, color='red', ha='right')


# Sugar: Plot article frequency
def plot_article_frequency(df):
    """
    Generates a line plot showing the number of articles published per day.
    """
    if df.empty:
        print("No data to plot.")
        return

    # Count articles per day
    count_by_date = df['pub_date'].value_counts().sort_index()

    plt.figure(figsize=(14, 6))
    ax = plt.gca()
    ax.plot(count_by_date.index, count_by_date.values, marker='', linestyle='-', label='NYT Crime Articles')

    annotate_events(ax)

    plt.title(f"NYT Articles on '{KEYWORD}' (2001) with Major Event Overlays")
    plt.suptitle("Mahima Ullah – Final Project", fontsize=10, x=0.99, ha='right')
    plt.xlabel("Date")
    plt.ylabel("Number of Articles")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.xticks(rotation=45)

    # Save the plot as an image
    plt.savefig("nyt_crime_trends_2001.png")
    plt.show()


# ETL Pipeline Execution
def run_etl():
    """
    Runs the entire ETL process:
    - Extract articles
    - Transform into DataFrame
    - Load to CSV
    - Plot article frequency
    """
    print("Starting ETL process...")
    raw_articles = extract_all_articles()

    if not raw_articles:
        print("No articles were extracted — likely due to API issues.")
        return

    transformed_df = transform_articles(raw_articles)
    load_to_csv(transformed_df, OUTPUT_FILE)
    plot_article_frequency(transformed_df)  # show graph


if __name__ == "__main__":
    run_etl()
