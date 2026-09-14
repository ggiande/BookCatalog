#!/usr/bin/env python3
"""
fetch_catalog.py - Phase 1 Metadata Pipeline

Queries Open Library API for book titles/ISBNs, validates response schema,
and writes structured catalog data into catalog.json.
Uses lenient fallbacks so bad ISBNs or incomplete API data do not break the pipeline.
"""

import sys
import os
import re
import json
import time
import argparse
import logging
from typing import Optional, List, Dict, Any
import requests
from pydantic import BaseModel, Field, ConfigDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MetadataPipeline")

# Default fallback cover URL (placeholder image with SVG or clean placeholder)
DEFAULT_COVER_URL = "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&auto=format&fit=crop&q=80"


class BookItem(BaseModel):
    """Schema representing a single book item in the catalog."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    query: str
    isbn: str = "N/A"
    title: str = "Unknown Title"
    author: str = "Unknown Author"
    publish_year: str = "N/A"
    cover_url: str = DEFAULT_COVER_URL
    publisher: str = "N/A"
    subjects: List[str] = Field(default_factory=list)
    description: str = "No description available."
    status: str = "found"  # "found" or "fallback"



class BookCatalog(BaseModel):
    """Schema representing the collection of books."""
    total_count: int = 0
    generated_at: str = ""
    books: List[BookItem] = Field(default_factory=list)


def is_isbn(query: str) -> bool:
    """Check if query string looks like an ISBN-10 or ISBN-13."""
    clean = re.sub(r'[\s\-]', '', query)
    return clean.isdigit() and len(clean) in (10, 13)


def make_api_request(url: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> Optional[Dict[str, Any]]:
    """
    Make an HTTP GET request with retry backoff and rate limit (429) handling.
    """
    headers = {
        "User-Agent": "AntigravityBookCatalogFetcher/1.0 (educational_project; contact@example.com)"
    }
    
    backoff = 0.5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"API Request to {url} (Attempt {attempt}/{max_retries})")
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning(f"Rate limited (429). Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= 2.0
            elif response.status_code == 404:
                logger.warning(f"Endpoint returned 404 for {url}")
                return None
            else:
                logger.warning(f"HTTP {response.status_code} for {url}. Attempt {attempt}")
                time.sleep(backoff)
                backoff *= 1.5
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error on attempt {attempt}: {e}")
            time.sleep(backoff)
            backoff *= 1.5

    logger.error(f"Failed to fetch data from {url} after {max_retries} attempts.")
    return None


def fetch_book_by_isbn(isbn_query: str) -> BookItem:
    """Fetch book details via Open Library ISBN API or Search fallback."""
    clean_isbn = re.sub(r'[\s\-]', '', isbn_query)
    
    # Try Open Library ISBN API first
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data"
    data = make_api_request(url)
    
    book_key = f"ISBN:{clean_isbn}"
    if data and book_key in data:
        info = data[book_key]
        
        # Extract title
        title = info.get("title", f"Book (ISBN: {clean_isbn})")
        
        # Extract authors
        authors_list = info.get("authors", [])
        author_names = [a.get("name") for a in authors_list if a.get("name")]
        author_str = ", ".join(author_names) if author_names else "Unknown Author"
        
        # Extract publish date / year
        pub_date = info.get("publish_date", "N/A")
        
        # Extract cover image
        cover_info = info.get("cover", {})
        cover_url = cover_info.get("large") or cover_info.get("medium") or cover_info.get("small")
        if not cover_url:
            cover_url = f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg"
            
        # Extract publishers
        publishers = info.get("publishers", [])
        pub_names = [p.get("name") for p in publishers if p.get("name")]
        publisher_str = ", ".join(pub_names) if pub_names else "N/A"
        
        # Extract subjects
        subjects_list = info.get("subjects", [])
        subjects = [s.get("name") for s in subjects_list[:5] if isinstance(s, dict) and s.get("name")]
        
        return BookItem(
            query=isbn_query,
            isbn=clean_isbn,
            title=title,
            author=author_str,
            publish_year=str(pub_date),
            cover_url=cover_url,
            publisher=publisher_str,
            subjects=subjects,
            description=f"Published by {publisher_str} in {pub_date}.",
            status="found"
        )
    
    # Fallback to search API for ISBN if direct bibkeys returned nothing
    logger.info(f"Direct ISBN endpoint empty for {clean_isbn}. Trying Search API...")
    return fetch_book_by_title(isbn_query)


def fetch_book_by_title(title_query: str) -> BookItem:
    """Fetch book details via Open Library Search API."""
    url = "https://openlibrary.org/search.json"
    params = {"q": title_query, "limit": 1}
    
    data = make_api_request(url, params=params)
    
    if data and data.get("docs") and len(data["docs"]) > 0:
        doc = data["docs"][0]
        
        title = doc.get("title", title_query.title())
        
        # Authors
        authors = doc.get("author_name", [])
        author_str = ", ".join(authors[:3]) if authors else "Unknown Author"
        
        # Publish year
        first_pub_year = doc.get("first_publish_year")
        pub_year_str = str(first_pub_year) if first_pub_year else "N/A"
        
        # Cover image
        cover_i = doc.get("cover_i")
        if cover_i:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
        else:
            isbns = doc.get("isbn", [])
            cover_url = f"https://covers.openlibrary.org/b/isbn/{isbns[0]}-L.jpg" if isbns else DEFAULT_COVER_URL
            
        # ISBN
        isbns = doc.get("isbn", [])
        isbn_str = isbns[0] if isbns else "N/A"
        
        # Publisher
        publishers = doc.get("publisher", [])
        pub_str = publishers[0] if publishers else "N/A"
        
        # Subjects
        subjects = doc.get("subject", [])[:5] if doc.get("subject") else []
        
        return BookItem(
            query=title_query,
            isbn=isbn_str,
            title=title,
            author=author_str,
            publish_year=pub_year_str,
            cover_url=cover_url,
            publisher=pub_str,
            subjects=subjects,
            description=f"First published in {pub_year_str} by {author_str}.",
            status="found"
        )
        
    # Lenient fallback if no search results found
    logger.warning(f"No API results found for query '{title_query}'. Generating graceful fallback entry.")
    return BookItem(
        query=title_query,
        isbn=re.sub(r'[\s\-]', '', title_query) if is_isbn(title_query) else "N/A",
        title=title_query if not is_isbn(title_query) else f"Book ({title_query})",
        author="Unknown Author",
        publish_year="N/A",
        cover_url=DEFAULT_COVER_URL,
        publisher="N/A",
        subjects=["Catalog Item"],
        description=f"Metadata auto-generated fallback for: {title_query}",
        status="fallback"
    )


def process_catalog(input_path: str, output_path: str):
    """Read input queries, fetch metadata with fallbacks, and write catalog.json."""
    if not os.path.exists(input_path):
        logger.error(f"Input file {input_path} does not exist.")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    logger.info(f"Loaded {len(lines)} queries from {input_path}")
    
    books: List[BookItem] = []
    for idx, query in enumerate(lines, 1):
        logger.info(f"[{idx}/{len(lines)}] Processing: '{query}'")
        
        # Polite delay to prevent aggressive rate limits
        if idx > 1:
            time.sleep(0.5)

        try:
            if is_isbn(query):
                item = fetch_book_by_isbn(query)
            else:
                item = fetch_book_by_title(query)
        except Exception as e:
            logger.error(f"Unexpected error processing '{query}': {e}. Using fallback.")
            item = BookItem(
                query=query,
                title=query,
                author="Unknown Author",
                publish_year="N/A",
                cover_url=DEFAULT_COVER_URL,
                status="fallback"
            )
            
        books.append(item)

    catalog = BookCatalog(
        total_count=len(books),
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        books=books
    )

    # Write output JSON with schema validation
    output_data = catalog.model_dump()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully saved {len(books)} books to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch book metadata and build catalog.json")
    parser.add_argument("--input", default="books_sample.txt", help="Path to input text file")
    parser.add_argument("--output", default="catalog.json", help="Path to output catalog.json")
    args = parser.parse_args()

    process_catalog(args.input, args.output)


if __name__ == "__main__":
    main()
