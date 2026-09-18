# IMDb Top 1000 Movies Scraper & Power BI Pipeline

This project extracts, standardizes, and exports a clean dataset of IMDb's Top 1000 movies, engineered specifically for direct ingestion into **Power BI Desktop** and **Power BI Service**.

---

## 📁 Workspace Files

| File | Description |
| :--- | :--- |
| **`imdb_scraper.py`** | Complete Python scraping & cleaning script containing all required functions (`get_page`, `parse_listing`, `parse_movie_page`, `clean_data`, `export_csv`). |
| **`imdb_top_1000_movies.csv`** | Clean, analysis-ready CSV dataset with 1,000 rows and 8 standardized columns, exported with `UTF-8 with BOM` for Power BI. |
| **`requirements.txt`** | Python library dependencies (`requests`, `beautifulsoup4`, `pandas`, `numpy`, `lxml`). |

---

## 🚀 How to Run in VS Code

### 1. Open Terminal in VS Code
Press ``Ctrl + ` `` (or navigate to **Terminal** > **New Terminal**).

### 2. Install Dependencies (if not already installed)
```bash
pip install -r requirements.txt
```

### 3. Execute the Pipeline
You can run the script with several modes:

```bash
# Default mode: Attempts live scraping with automatic fallback on AWS WAF challenge
python imdb_scraper.py

# Force canonical Top 1000 reference dataset mode (instant execution)
python imdb_scraper.py --source kaggle

# Target a custom row count or output file
python imdb_scraper.py --target 1000 --output imdb_top_1000_movies.csv
```

---

## 📊 Dataset Schema (8 Columns for Power BI)

| Column Name | Power BI Data Type | Description |
| :--- | :--- | :--- |
| **`Series Title`** | Text (`str`) | Movie name, stripped of rank numbers, HTML tags, and redundant whitespace. |
| **`Release Year`** | Whole Number (`Int64`) | 4-digit release year (1880–2099). |
| **`Certificate`** | Text (`str`) | Standardized MPAA/CBFC categories: `U`, `UA`, `A`, `R`, `PG`, `PG-13`, `Approved`, `Not Specified`. |
| **`Runtime`** | Whole Number (`Int64`) | Duration in minutes (numeric only, "min" removed). |
| **`Genre`** | Text (`str`) | Clean comma-separated list of genres (e.g., `Action, Crime, Drama`). |
| **`IMDb Rating`** | Decimal Number (`float64`) | Rating out of 10 rounded to 1 decimal place. |
| **`Overview`** | Text (`str`) | Plot summary cleaned of HTML entities and special characters. |
| **`Director`** | Text (`str`) | Name(s) of the director(s), comma-separated if multiple. |

---

## 📈 Importing into Power BI

1. Open **Power BI Desktop**.
2. Click **Get Data** > **Text/CSV**.
3. Select `imdb_top_1000_movies.csv` from this folder.
4. Click **Load**. All 8 columns will be detected with their native data types with zero manual transformations required.

