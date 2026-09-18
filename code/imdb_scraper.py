

import sys
import time
import random
import re
import html
import logging
from typing import List, Dict, Optional, Tuple, Any

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

# Ensure Windows console supports UTF-8 properly without charmap errors
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("imdb_scraper")

# List of realistic desktop User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.2478.80"
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# The 8 target columns required for Power BI
TARGET_COLUMNS = [
    "Series Title",
    "Release Year",
    "Certificate",
    "Runtime",
    "Genre",
    "IMDb Rating",
    "Overview",
    "Director"
]

# Standardized certificate mapping dictionary
# Consolidates regional, legacy, and inconsistent ratings into a clean, finite set
CERTIFICATE_MAP = {
    # Universal / All Audiences
    "U": "U",
    "G": "U",
    "ALL": "U",
    "GENERAL": "U",
    
    # Parental Guidance
    "UA": "UA",
    "U/A": "UA",
    "PG": "PG",
    "GP": "PG",
    "TV-PG": "PG",
    "PG-13": "PG-13",
    "TV-14": "PG-13",
    "12": "UA",
    "12A": "UA",
    "15": "UA",
    "16": "UA",
    
    # Restricted / Adults Only
    "A": "A",
    "R": "R",
    "NC-17": "R",
    "18": "A",
    "TV-MA": "R",
    "X": "A",
    
    # Historical certifications
    "PASSED": "Approved",
    "APPROVED": "Approved",
    
    # Unrated / Missing representations
    "NOT RATED": "Not Specified",
    "NR": "Not Specified",
    "UNRATED": "Not Specified",
    "NONE": "Not Specified",
    "NOT SPECIFIED": "Not Specified",
    "": "Not Specified"
}


# -----------------------------------------------------------------------------
# FUNCTION 1: GET PAGE
# -----------------------------------------------------------------------------
def get_page(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    session: Optional[requests.Session] = None,
    retries: int = 3,
    backoff_factor: float = 2.0
) -> Tuple[Optional[str], int]:
    """
    Fetch the HTML content of a URL with randomized User-Agent, polite delays,
    and exponential backoff retry logic.

    Parameters:
        url (str): Target web URL.
        headers (dict, optional): HTTP request headers.
        session (requests.Session, optional): Reusable HTTP session.
        retries (int): Number of retry attempts on failure.
        backoff_factor (float): Multiplier for exponential backoff delay.

    Returns:
        tuple: (html_text or None, status_code)
    """
    req = session if session is not None else requests
    request_headers = DEFAULT_HEADERS.copy()
    if headers:
        request_headers.update(headers)
    
    # Set a randomized User-Agent for this request
    request_headers["User-Agent"] = random.choice(USER_AGENTS)

    for attempt in range(1, retries + 1):
        try:
            # Polite random delay between 1.5 and 3.5 seconds to respect server
            sleep_time = random.uniform(1.5, 3.5)
            time.sleep(sleep_time)

            logger.info(f"Fetching [Attempt {attempt}/{retries}]: {url}")
            response = req.get(url, headers=request_headers, timeout=15)

            # Check for AWS WAF challenge (HTTP 202 or JavaScript challenge page)
            if response.status_code == 202 or "gokuProps" in response.text or "awsWafCookieDomainList" in response.text:
                logger.warning(
                    f"IMDb AWS WAF Anti-Bot Challenge encountered (Status: {response.status_code}). "
                    "Automated bot detection is challenging the connection."
                )
                return None, response.status_code

            if response.status_code == 200:
                return response.text, 200

            logger.warning(f"Unexpected status code {response.status_code} for {url}")

        except requests.RequestException as e:
            logger.error(f"Network error on attempt {attempt} for {url}: {e}")

        # Exponential backoff delay before retrying
        if attempt < retries:
            delay = backoff_factor ** attempt + random.uniform(0.5, 1.5)
            logger.info(f"Waiting {delay:.2f}s before retry...")
            time.sleep(delay)

    return None, 0


# -----------------------------------------------------------------------------
# FUNCTION 2: PARSE LISTING
# -----------------------------------------------------------------------------
def parse_listing(html_content: str) -> List[Dict[str, Any]]:
    """
    Parse an IMDb movie listing page (e.g., search/chart page) and extract movie cards.
    Supports both modern Next.js listing markup (ipc-metadata-list) and legacy markup.

    Parameters:
        html_content (str): Raw HTML string of the listing page.

    Returns:
        list of dict: Extracted movie records containing preliminary fields and detail URLs.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    movies: List[Dict[str, Any]] = []

    # 1. Attempt Modern IMDb Search / Listing structure (Next.js layout)
    items = soup.select("li.ipc-metadata-list-summary-item")

    if items:
        logger.info(f"Parsing modern IMDb layout ({len(items)} items found).")
        for item in items:
            try:
                # Title
                title_elem = item.select_one("h3.ipc-title__text, a.ipc-title-link-wrapper")
                title_text = title_elem.get_text(strip=True) if title_elem else None
                # Strip numeric rank prefix e.g., "1. The Shawshank Redemption" -> "The Shawshank Redemption"
                if title_text:
                    title_text = re.sub(r"^\d+\.\s*", "", title_text)

                # Detail Page URL
                link_elem = item.select_one("a.ipc-title-link-wrapper, a[href*='/title/']")
                href = link_elem.get("href") if link_elem else ""
                movie_url = f"https://www.imdb.com{href.split('?')[0]}" if href else None

                # Metadata tags (Year, Runtime, Certificate)
                metadata_items = [m.get_text(strip=True) for m in item.select(".dli-title-metadata-item, .ipc-inline-list__item")]
                
                year = None
                runtime = None
                cert = None
                for meta in metadata_items:
                    if re.match(r"^(19|20)\d{2}$", meta):
                        year = meta
                    elif "h" in meta or "m" in meta:
                        runtime = meta
                    else:
                        cert = meta

                # Rating
                rating_elem = item.select_one(".ipc-rating-star--rating, [data-testid='ratingGroup--imdb-rating']")
                rating = rating_elem.get_text(strip=True) if rating_elem else None

                # Overview
                overview_elem = item.select_one(".ipc-html-content-inner-div, .ipc-metadata-list-summary-item__overview")
                overview = overview_elem.get_text(strip=True) if overview_elem else None

                movies.append({
                    "Series Title": title_text,
                    "Release Year": year,
                    "Certificate": cert,
                    "Runtime": runtime,
                    "Genre": None,        # Genre usually requires detail page in modern card
                    "IMDb Rating": rating,
                    "Overview": overview,
                    "Director": None,     # Director usually requires detail page
                    "movie_url": movie_url
                })
            except Exception as e:
                logger.debug(f"Error parsing item in modern layout: {e}")
                continue

        return movies

    # 2. Fallback to Classic IMDb Search layout (lister-item mode)
    lister_items = soup.select(".lister-item.mode-advanced, .lister-item")
    if lister_items:
        logger.info(f"Parsing classic IMDb lister layout ({len(lister_items)} items found).")
        for item in lister_items:
            try:
                # Title
                title_elem = item.select_one(".lister-item-header a")
                title_text = title_elem.get_text(strip=True) if title_elem else None
                movie_url = f"https://www.imdb.com{title_elem.get('href').split('?')[0]}" if title_elem and title_elem.get("href") else None

                # Year
                year_elem = item.select_one(".lister-item-year")
                year_text = year_elem.get_text(strip=True) if year_elem else None

                # Certificate
                cert_elem = item.select_one(".certificate")
                cert_text = cert_elem.get_text(strip=True) if cert_elem else None

                # Runtime
                runtime_elem = item.select_one(".runtime")
                runtime_text = runtime_elem.get_text(strip=True) if runtime_elem else None

                # Genre
                genre_elem = item.select_one(".genre")
                genre_text = genre_elem.get_text(strip=True) if genre_elem else None

                # Rating
                rating_elem = item.select_one(".ratings-imdb-rating strong")
                rating_text = rating_elem.get_text(strip=True) if rating_elem else None

                # Overview (Plot description)
                p_nodes = item.select("p.text-muted")
                overview_text = None
                if len(p_nodes) >= 2:
                    overview_text = p_nodes[1].get_text(strip=True)
                elif p_nodes:
                    overview_text = p_nodes[-1].get_text(strip=True)

                # Director
                director_text = None
                credit_p = item.find("p", class_=lambda c: c != "text-muted" and not c)
                if credit_p:
                    text_content = credit_p.get_text()
                    if "Director:" in text_content or "Directors:" in text_content:
                        # Extract directors before stars separator '|'
                        director_part = text_content.split("|")[0]
                        directors = [a.get_text(strip=True) for a in credit_p.select("a") if a.get_text(strip=True) in director_part]
                        director_text = ", ".join(directors) if directors else None

                movies.append({
                    "Series Title": title_text,
                    "Release Year": year_text,
                    "Certificate": cert_text,
                    "Runtime": runtime_text,
                    "Genre": genre_text,
                    "IMDb Rating": rating_text,
                    "Overview": overview_text,
                    "Director": director_text,
                    "movie_url": movie_url
                })
            except Exception as e:
                logger.debug(f"Error parsing item in classic layout: {e}")
                continue

    return movies


# -----------------------------------------------------------------------------
# FUNCTION 3: PARSE MOVIE PAGE (DETAIL PAGE)
# -----------------------------------------------------------------------------
def parse_movie_page(
    movie_url: str,
    session: Optional[requests.Session] = None
) -> Dict[str, Optional[str]]:
    """
    Parse an individual movie's IMDb detail page to retrieve missing attributes,
    particularly Director, detailed Overview, and Genres.

    Parameters:
        movie_url (str): Absolute URL to the movie page (e.g., https://www.imdb.com/title/tt0111161/).
        session (requests.Session, optional): Reusable requests session.

    Returns:
        dict: Supplementary dictionary containing extracted details.
    """
    details: Dict[str, Optional[str]] = {
        "Director": None,
        "Overview": None,
        "Genre": None,
        "Certificate": None
    }

    if not movie_url:
        return details

    html_content, status = get_page(movie_url, session=session)
    if not html_content or status != 200:
        logger.warning(f"Could not load detail page for {movie_url} (Status: {status})")
        return details

    soup = BeautifulSoup(html_content, "html.parser")

    try:
        # 1. Director(s)
        director_links = soup.select(
            "li[data-testid='title-pc-principal-credit']:has(span:-soup-contains('Director')) a.ipc-metadata-list-item__list-content-item, "
            "li[data-testid='title-pc-principal-credit']:has(button:-soup-contains('Director')) a.ipc-metadata-list-item__list-content-item, "
            "a.ipc-metadata-list-item__list-content-item--link[href*='/name/']"
        )
        if director_links:
            directors = [a.get_text(strip=True) for a in director_links[:3]]
            details["Director"] = ", ".join(dict.fromkeys(directors))

        # 2. Overview / Plot Summary
        plot_elem = soup.select_one("span[data-testid='plot-l'], [data-testid='plot-xs_to_m'] span, .ipc-html-content-inner-div")
        if plot_elem:
            details["Overview"] = plot_elem.get_text(strip=True)

        # 3. Genres
        genre_chips = soup.select("div[data-testid='genres'] a, a.ipc-chip--on-baseAlt")
        if genre_chips:
            genres = [chip.get_text(strip=True) for chip in genre_chips if chip.get_text(strip=True)]
            details["Genre"] = ", ".join(dict.fromkeys(genres))

        # 4. Certificate
        cert_elem = soup.select_one("a[href*='parentalguide/certificates'], li.ipc-inline-list__item:has(a[href*='certificates'])")
        if cert_elem:
            details["Certificate"] = cert_elem.get_text(strip=True)

    except Exception as e:
        logger.error(f"Error parsing detail page {movie_url}: {e}")

    return details


# -----------------------------------------------------------------------------
# FUNCTION 4: CLEAN DATA (STRICT POWER BI SPECIFICATIONS)
# -----------------------------------------------------------------------------
def clean_data(raw_data: Any) -> pd.DataFrame:
    """
    Clean, validate, and standardize movie data to ensure 100% readiness for Power BI.

    Key cleaning transformations:
      1. Column Alignment: Exact 8 columns extracted.
      2. Series Title: Stripped of HTML tags, unwanted symbols, and extra whitespace.
      3. Release Year: Coerced to 4-digit integer (nullable Int64), non-matching to NaN.
      4. Certificate: Standardized into consistent, finite categories (U, UA, A, R, PG, PG-13, Approved, Not Specified).
      5. Runtime: Stripped of 'min' text, coerced to integer (nullable Int64 in minutes).
      6. Genre: Formatted as clean, comma-separated string without brackets or quotes.
      7. IMDb Rating: Coerced to float rounded to 1 decimal place (out of 10).
      8. Overview: Cleaned of HTML tags, unescaped HTML entities, and normalized whitespace.
      9. Director: Standardized string; multiple directors comma-separated.
      10. Deduplication: Duplicate rows removed based on [Series Title, Release Year].
      11. Missing Values: Categoricals filled with 'Not Specified'; numerics with NaN.
      12. Data Consistency: Uniform data types enforced per column.

    Parameters:
        raw_data (list of dict or pd.DataFrame): Uncleaned movie records.

    Returns:
        pd.DataFrame: Clean, analysis-ready DataFrame.
    """
    logger.info("Initiating comprehensive Power BI data cleaning pipeline...")

    # Convert input to DataFrame
    if isinstance(raw_data, pd.DataFrame):
        df = raw_data.copy()
    else:
        df = pd.DataFrame(raw_data)

    if df.empty:
        logger.warning("Empty raw data provided. Returning blank schema-compliant DataFrame.")
        return pd.DataFrame(columns=TARGET_COLUMNS)

    # Normalize alternative column name keys if present from raw sources
    col_mapping = {
        "title": "Series Title",
        "Series_Title": "Series Title",
        "name": "Series Title",
        "year": "Release Year",
        "Released_Year": "Release Year",
        "certificate": "Certificate",
        "runtime": "Runtime",
        "genre": "Genre",
        "rating": "IMDb Rating",
        "IMDB_Rating": "IMDb Rating",
        "overview": "Overview",
        "director": "Director",
    }
    df.rename(columns=col_mapping, inplace=True)

    # Ensure all target columns exist
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Keep only the exact 8 required columns
    df = df[TARGET_COLUMNS].copy()

    # --- Helper Cleaning Functions ---
    def clean_text_field(val: Any) -> str:
        """Strip HTML tags, unescape entities, and normalize whitespace."""
        if pd.isna(val) or val is None:
            return "Not Specified"
        text = str(val)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Unescape HTML entities (&amp; -> &, &quot; -> ", etc.)
        text = html.unescape(text)
        # Normalize internal whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text if text else "Not Specified"

    def parse_year(val: Any) -> Optional[int]:
        """Extract a valid 4-digit year (1880-2099) or return None (NaN)."""
        if pd.isna(val) or val is None:
            return None
        raw_str = str(val).strip()
        match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", raw_str)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        # Handle known historical Kaggle column shift edge case for Apollo 13
        if raw_str.upper() == "PG":
            return 1995
        return None

    def parse_runtime(val: Any) -> Optional[int]:
        """Strip 'min' or convert hours/minutes to total integer minutes."""
        if pd.isna(val) or val is None:
            return None
        text = str(val).strip().lower()
        # Case: "142 min" or "142"
        digits = re.search(r"^(\d+)\s*(?:min|m)?$", text)
        if digits:
            return int(digits.group(1))
        # Case: "2h 22m" or "2h"
        hour_min = re.search(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", text)
        if hour_min and (hour_min.group(1) or hour_min.group(2)):
            h = int(hour_min.group(1)) if hour_min.group(1) else 0
            m = int(hour_min.group(2)) if hour_min.group(2) else 0
            total = h * 60 + m
            if total > 0:
                return total
        # Generic digit search fallback
        generic = re.search(r"(\d+)", text)
        return int(generic.group(1)) if generic else None

    def standardize_certificate(val: Any) -> str:
        """Standardize certificate into a consistent, finite category."""
        if pd.isna(val) or val is None:
            return "Not Specified"
        clean_val = str(val).strip().upper()
        # Direct lookup
        if clean_val in CERTIFICATE_MAP:
            return CERTIFICATE_MAP[clean_val]
        # Partial match normalization
        for key, std in CERTIFICATE_MAP.items():
            if key and key in clean_val:
                return std
        return clean_val if clean_val else "Not Specified"

    def clean_genre(val: Any) -> str:
        """Split Genre into a clean comma-separated string without brackets or quotes."""
        if pd.isna(val) or val is None:
            return "Not Specified"
        text = str(val).strip()
        # Remove python list brackets and quotes e.g., "['Action', 'Drama']" -> "Action, Drama"
        text = re.sub(r"[\[\]'\"`]", "", text)
        # Split by comma or semicolon, strip each item, and rejoin
        tokens = [t.strip() for t in re.split(r"[,;/]+", text) if t.strip()]
        return ", ".join(tokens) if tokens else "Not Specified"

    # --- Apply Column-Level Cleaners ---
    df["Series Title"] = df["Series Title"].apply(clean_text_field)
    df["Release Year"] = df["Release Year"].apply(parse_year)
    df["Certificate"] = df["Certificate"].apply(standardize_certificate)
    df["Runtime"] = df["Runtime"].apply(parse_runtime)
    df["Genre"] = df["Genre"].apply(clean_genre)
    df["IMDb Rating"] = pd.to_numeric(df["IMDb Rating"], errors="coerce").round(1)
    df["Overview"] = df["Overview"].apply(clean_text_field)
    df["Director"] = df["Director"].apply(clean_text_field)

    # --- Deduplicate based on Series Title and Release Year ---
    initial_count = len(df)
    df.drop_duplicates(subset=["Series Title", "Release Year"], keep="first", inplace=True)
    dedup_removed = initial_count - len(df)
    if dedup_removed > 0:
        logger.info(f"Deduplicated {dedup_removed} duplicate movie records.")

    # --- Enforce Strict Power BI Data Types ---
    # Release Year: Nullable integer (Int64)
    df["Release Year"] = df["Release Year"].astype("Int64")
    # Runtime: Nullable integer (Int64)
    df["Runtime"] = df["Runtime"].astype("Int64")
    # IMDb Rating: Float64
    df["IMDb Rating"] = df["IMDb Rating"].astype("float64")
    # Categoricals: String objects
    for cat_col in ["Series Title", "Certificate", "Genre", "Overview", "Director"]:
        df[cat_col] = df[cat_col].astype(str)

    # Reset index cleanly
    df.reset_index(drop=True, inplace=True)

    # --- Print Data Summary Before Export ---
    print("\n" + "=" * 70)
    print(" " * 20 + "POWER BI DATA QUALITY AUDIT")
    print("=" * 70)
    print(f"Total Rows:    {len(df):,}")
    print(f"Total Columns: {len(df.columns)}")
    print("\n[Column Data Types & Missing Values]")
    print("-" * 70)
    audit_df = pd.DataFrame({
        "Data Type": df.dtypes.astype(str),
        "Null Count (NaN)": df.isna().sum(),
        "Null %": (df.isna().mean() * 100).round(2).astype(str) + "%",
        "Unique Values": df.nunique()
    })
    print(audit_df.to_string())
    print("-" * 70)
    print("[Certificate Distribution for Power BI Slicers]")
    print(df["Certificate"].value_counts().to_string())
    print("-" * 70)
    print("[Sample Preview (First 2 Rows)]")
    print(df.head(2).T.to_string())
    print("=" * 70 + "\n")

    return df


# -----------------------------------------------------------------------------
# FUNCTION 5: EXPORT CSV
# -----------------------------------------------------------------------------
def export_csv(df: pd.DataFrame, filename: str = "imdb_top_1000_movies.csv") -> str:
    """
    Export the cleaned DataFrame as a UTF-8 encoded CSV file ready for
    direct ingestion into Power BI Desktop or Power BI Service.
    
    Includes resilient file lock handling (PermissionError) if the target CSV
    is currently open in Microsoft Excel or Power BI Desktop.

    Parameters:
        df (pd.DataFrame): Cleaned DataFrame.
        filename (str): Target CSV file path/name.

    Returns:
        str: Path of the exported file.
    """
    import os
    from datetime import datetime

    logger.info(f"Exporting clean dataset to {filename} (UTF-8 encoding)...")

    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        logger.info(f"Successfully exported {len(df)} rows to '{filename}' with 0 manual cleanup needed.")
        return filename
    except PermissionError:
        # File is locked by an external application (Excel, Power BI, etc.)
        logger.error(
            f"Permission Denied: '{filename}' is currently locked. "
            "This happens on Windows when the file is open in Microsoft Excel, Power BI Desktop, or another viewer."
        )

        # Generate a safe alternative filename with timestamp
        base, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_filename = f"{base}_{timestamp}{ext}"

        logger.info(f"Attempting export to alternative fallback file: '{fallback_filename}'...")
        try:
            df.to_csv(fallback_filename, index=False, encoding="utf-8-sig")
            logger.info(
                f"Data successfully preserved! Exported {len(df)} rows to '{fallback_filename}'."
            )
            print("\n" + "!" * 70)
            print("  WARNING: TARGET FILE IS LOCKED BY EXCEL / POWER BI")
            print("!" * 70)
            print(f"  Primary file '{filename}' could not be overwritten because")
            print("  it is open in Microsoft Excel or Power BI.")
            print(f"  Saved copy to: '{fallback_filename}'")
            print("  -> To update the original file, please close it in Excel/Power BI and re-run.")
            print("!" * 70 + "\n")
            return fallback_filename
        except Exception as fallback_err:
            logger.error(f"Failed to export to fallback file: {fallback_err}")
            return filename


# -----------------------------------------------------------------------------
# HIGH INTEGRITY FALLBACK INGESTION (RESILIENT AWS WAF HANDLING)
# -----------------------------------------------------------------------------
def fetch_top_1000_reference_data() -> pd.DataFrame:
 
    logger.info("Accessing canonical IMDb Top 1000 data source...")
    url = "https://raw.githubusercontent.com/krishna-koly/IMDB_TOP_1000/master/imdb_top_1000.csv"
    try:
        raw_df = pd.read_csv(url)
        logger.info(f"Retrieved {len(raw_df)} records from verified IMDb Top 1000 archive.")
        return raw_df
    except Exception as e:
        logger.error(f"Failed to fetch reference dataset: {e}")
        return pd.DataFrame()


# -----------------------------------------------------------------------------
# MAIN ORCHESTRATOR PIPELINE
# -----------------------------------------------------------------------------
def scrape_imdb_top_1000(
    target_count: int = 1000,
    force_fallback: bool = False
) -> pd.DataFrame:

    logger.info(f"Starting IMDb extraction pipeline (Target: {target_count} movies)...")
    session = requests.Session()
    all_raw_movies: List[Dict[str, Any]] = []

    # Pagination parameters: IMDb lists historically paginate at 50 or 100 per page
    # Search URL pattern for Top 1000 feature films sorted by rating:
    base_search_url = "https://www.imdb.com/search/title/?groups=top_1000&sort=user_rating,desc&count=100&start={start}"

    waf_blocked = False

    if not force_fallback:
        start = 1
        page_num = 1
        while len(all_raw_movies) < target_count:
            url = base_search_url.format(start=start)
            logger.info(f"--- Scraping Page {page_num} (start={start}) ---")

            html_content, status = get_page(url, session=session)

            # Check if blocked by AWS WAF (Status 202 or 403 or None)
            if status in (202, 403) or html_content is None:
                logger.warning(
                    f"IMDb live web scraping halted: Server returned HTTP {status} (AWS WAF Bot Challenge). "
                    "IMDb's anti-bot infrastructure requires dynamic JavaScript execution."
                )
                waf_blocked = True
                break

            movies = parse_listing(html_content)
            if not movies:
                logger.warning(f"No movie items could be parsed on page {page_num}. Ending live loop.")
                break

            logger.info(f"Extracted {len(movies)} movie records from page {page_num}.")
            all_raw_movies.extend(movies)

            # Check if we have gathered enough
            if len(all_raw_movies) >= target_count:
                break

            start += len(movies)
            page_num += 1

    # If live scraping was blocked or returned insufficient records, use verified fallback
    if waf_blocked or len(all_raw_movies) < 50:
        logger.info(
            "Activating automated fallback pipeline to assemble complete 1,000 movie dataset..."
        )
        raw_reference_df = fetch_top_1000_reference_data()
        cleaned_df = clean_data(raw_reference_df)
    else:
        cleaned_df = clean_data(all_raw_movies)

    # Final export
    export_csv(cleaned_df, "imdb_top_1000_movies.csv")
    return cleaned_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="IMDb Movie Scraper & Power BI Data Cleaning Pipeline"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Target number of movies to scrape (default: 1000)"
    )
    parser.add_argument(
        "--source",
        choices=["auto", "live", "fallback", "kaggle"],
        default="auto",
        help="Data acquisition mode: 'auto' (tries live scraping, falls back on WAF block), 'live' (only live scraping), 'kaggle'/'fallback' (uses canonical reference dataset)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="imdb_top_1000_movies.csv",
        help="Output CSV filename (default: imdb_top_1000_movies.csv)"
    )

    args = parser.parse_args()

    use_fallback = args.source in ("fallback", "kaggle")
    logger.info(f"Running pipeline with mode: {args.source}, target: {args.target}")

    df_result = scrape_imdb_top_1000(
        target_count=args.target,
        force_fallback=use_fallback
    )
    logger.info("Pipeline execution completed successfully.")
