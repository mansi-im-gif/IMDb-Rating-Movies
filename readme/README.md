# 🎬 IMDb Movies & Series Rating Analysis

## 📌 Project Overview

This project analyzes **1,000 IMDb movies and series** using Python and Power BI to explore ratings, genres, release trends, runtime, certificates, and directors.

The project covers the complete data analytics workflow — from **data collection and cleaning to exploratory analysis and interactive dashboard creation**.

---

## 🛠️ Tools & Technologies

* **Python** — Data collection and preprocessing
* **Pandas** — Data cleaning and transformation
* **Web Scraping** — IMDb data extraction
* **Power BI** — Interactive dashboard and visualization
* **Power Query** — Data transformation
* **DAX** — Calculated columns and analytical measures
* **Git & GitHub** — Version control and project sharing

---

## 📊 Dashboard Features

The Power BI dashboard provides interactive analysis of:

* 🎯 Total Movies / Series
* ⭐ Average & Highest IMDb Rating
* ⏱️ Average Runtime
* 📅 Oldest & Latest Release Year
* 🎭 Genre Distribution
* 🎬 Director Analysis
* 🏆 Top-Rated Movies / Series
* 📈 IMDb Rating Distribution
* 📆 Release Trends by Year & Decade
* ⏳ Runtime Category Analysis
* 🔖 Certificate Distribution

### Interactive Filters

Users can explore the dashboard using slicers for:

* Release Year
* Genre
* Certificate
* IMDb Rating
* Runtime
* Director

---

## 🔎 Key Analysis Areas

### ⭐ Rating Analysis

* Distribution of IMDb ratings
* Highest-rated titles
* Rating trends across decades

### 🎭 Genre Analysis

* Most common genres
* Genre-wise rating patterns
* Comparison of different movie/series categories

### 📅 Release Trends

* Number of releases by year
* Decade-wise release patterns
* Changes in ratings across different periods

### ⏱️ Runtime Analysis

* Average runtime
* Runtime categories
* Relationship between runtime and ratings

### 🎬 Director Analysis

* Number of titles by director
* Director-wise rating analysis
* Directors associated with highly rated titles

---

## 📂 Project Structure

```text
IMDb-Rating-Movies/
│
├── code/
│   └── imdb_scraper.py
│
├── data/
│   └── imdb_top_1000_movies_20260911_205646.csv
│
├── images/
│   ├── Screenshot (5).png
│   ├── Screenshot (6).png
│   ├── Screenshot (7).png
│   ├── Screenshot (8).png
│   ├── Screenshot (9).png
│   ├── Screenshot (10).png
│   └── Screenshot (11).png
│
├── power bi/
│   └── imdb_rating.pbix
│
├── readme/
│   └── README.md
│
├── .gitignore
└── requirements.txt
```

---

## 🧹 Data Processing

The dataset was processed using Python and Power Query to:

* Clean and structure scraped IMDb data
* Handle missing values
* Convert numerical fields into appropriate data types
* Categorize movie runtimes
* Create release-year/decade classifications
* Extract primary genres for analysis
* Prepare the dataset for Power BI visualization

---

## 📈 Dashboard Screenshots

Screenshots of the Power BI dashboard are available in the [`images`](../images/) folder.

---

## 🚀 How to Run the Project

### 1. Clone the repository

```bash
git clone https://github.com/mansi-im-gif/IMDb-Rating-Movies.git
```

### 2. Install required Python libraries

```bash
pip install -r requirements.txt
```

### 3. Run the scraper

```bash
python code/imdb_scraper.py
```

### 4. Open the Power BI Dashboard

Open:

```text
power bi/imdb_rating.pbix
```

in **Microsoft Power BI Desktop**.

---

## 🎯 Project Outcome

This project demonstrates practical skills in:

* Web Scraping
* Python & Pandas
* Data Cleaning
* Exploratory Data Analysis
* Power Query
* DAX
* Data Visualization
* Dashboard Development
* Git & GitHub

It showcases an end-to-end **Data Analytics workflow**, from raw data collection to interactive business-style insights.

---

## 👩‍💻 Author

**Mansi Mann Priya**

Aspiring Data Analyst | Python | SQL | Excel | Power BI

## 📊 Power BI Dashboard

[Download the Power BI Dashboard](./powerbi/imdb_rating.pbix)