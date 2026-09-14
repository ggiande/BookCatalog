import streamlit as st
import json
import os
import re
from typing import Dict, List, Any
from fetch_catalog import is_isbn, fetch_book_by_isbn, fetch_book_by_title

# Page Configuration
st.set_page_config(
    page_title="Book Catalog Explorer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Styling
st.markdown("""
<style>
    /* Main Background & Font Styling */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #38bdf8;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 0;
    }

    /* Book Card Styling */
    .book-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.25rem;
        height: 100%;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: flex;
        flex-direction: column;
    }
    .book-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -5px rgba(56, 189, 248, 0.15);
        border-color: #38bdf8;
    }

    .cover-img {
        border-radius: 8px;
        object-fit: cover;
        width: 100%;
        height: 280px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        margin-bottom: 1rem;
    }

    .book-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 0.3rem;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .book-author {
        font-size: 0.95rem;
        color: #38bdf8;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    .badge-year {
        background-color: #334155;
        color: #cbd5e1;
    }
    .badge-status-found {
        background-color: #064e3b;
        color: #34d399;
        border: 1px solid #059669;
    }
    .badge-status-fallback {
        background-color: #78350f;
        color: #fbbf24;
        border: 1px solid #d97706;
    }
    .badge-subject {
        background-color: #1e1b4b;
        color: #a78bfa;
        border: 1px solid #4338ca;
    }
    .badge-incomplete {
        background-color: #7c2d12;
        color: #fdba74;
        border: 1px solid #ea580c;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_catalog(filepath: str = "catalog.json") -> Dict[str, Any]:
    """Load catalog dataset from catalog.json."""
    if not os.path.exists(filepath):
        return {"total_count": 0, "generated_at": "", "books": []}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading catalog file: {e}")
        return {"total_count": 0, "generated_at": "", "books": []}


def save_catalog(data: Dict[str, Any], filepath: str = "catalog.json") -> bool:
    """Save updated catalog dictionary back to catalog.json."""
    try:
        data["total_count"] = len(data.get("books", []))
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save catalog file: {e}")
        return False


def clean_publish_year(raw_year: str) -> str:
    """Extract a 4-digit year (e.g. '2023' from '2023-07-25' or 'July 25, 2023') or return 'N/A'."""
    if not raw_year or str(raw_year).strip().upper() in ("N/A", "UNKNOWN", ""):
        return "N/A"
    
    match = re.search(r'\b(1[7-9]\d\d|20\d\d)\b', str(raw_year))
    if match:
        return match.group(1)
    
    clean_digits = "".join([c for c in str(raw_year) if c.isdigit()])
    if len(clean_digits) == 4:
        return clean_digits
        
    return "N/A"


def has_incomplete_info(book: Dict[str, Any]) -> bool:
    """Check if ANY field in book has empty, None, N/A, or Unknown/placeholder values."""
    check_fields = ["title", "author", "isbn", "publish_year", "cover_url", "publisher", "description"]
    placeholder_values = {"", "n/a", "unknown", "unknown author", "unknown title", "none", "no description available."}

    for field in check_fields:
        val = str(book.get(field, "")).strip().lower()
        if not val or val in placeholder_values:
            return True

    subjects = book.get("subjects")
    if not subjects or len(subjects) == 0:
        return True

    return False


def match_book(book: Dict[str, Any], query: str) -> bool:
    """Check if query string matches book's title, author, isbn, or raw query field."""
    if not query:
        return True
    q = query.strip().lower()
    return (
        q in book.get("title", "").lower()
        or q in book.get("author", "").lower()
        or q in book.get("isbn", "").lower()
        or q in book.get("query", "").lower()
    )


def main():
    # Hero Banner
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">📚 Personal Book Catalog</div>
        <div class="hero-subtitle">Interactive library metadata powered by Open Library API and automated pipeline.</div>
    </div>
    """, unsafe_allow_html=True)

    catalog_data = load_catalog("catalog.json")
    books = catalog_data.get("books", [])
    total_count = catalog_data.get("total_count", len(books))
    generated_at = catalog_data.get("generated_at", "N/A")

    # Sidebar: Add New Book Section
    st.sidebar.header("➕ Add New Book")
    with st.sidebar.expander("Expand Form", expanded=False):
        with st.form("add_book_form", clear_on_submit=True):
            new_title = st.text_input("Title *")
            new_author = st.text_input("Author", value="Unknown Author")
            new_isbn = st.text_input("ISBN", value="N/A")
            new_year = st.text_input("Publish Year", value="N/A")
            new_cover = st.text_input("Cover Image URL", value="https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&auto=format&fit=crop&q=80")
            new_publisher = st.text_input("Publisher", value="N/A")
            new_subjects_raw = st.text_input("Subjects (comma separated)", value="Custom Entry")
            new_description = st.text_area("Description", value="Added manually via Book Catalog UI.")
            
            submitted = st.form_submit_button("Add Book to Catalog")
            if submitted:
                if not new_title.strip():
                    st.error("Title is required!")
                else:
                    subjects_list = [s.strip() for s in new_subjects_raw.split(",") if s.strip()]
                    new_entry = {
                        "query": new_title.strip(),
                        "isbn": new_isbn.strip() or "N/A",
                        "title": new_title.strip(),
                        "author": new_author.strip() or "Unknown Author",
                        "publish_year": clean_publish_year(new_year.strip()),
                        "cover_url": new_cover.strip() or "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&auto=format&fit=crop&q=80",
                        "publisher": new_publisher.strip() or "N/A",
                        "subjects": subjects_list,
                        "description": new_description.strip(),
                        "status": "found"
                    }
                    catalog_data["books"].append(new_entry)
                    if save_catalog(catalog_data, "catalog.json"):
                        st.success(f"Added '{new_title.strip()}' to catalog!")
                        st.rerun()

    # Sidebar: Delete Book Section
    st.sidebar.header("🗑️ Delete Book")
    with st.sidebar.expander("Expand Delete Form", expanded=False):
        delete_query = st.text_input("Search Title, Author, or ISBN to Delete:", "").strip().lower()
        matching_books = [b for b in books if match_book(b, delete_query)]
        
        if not matching_books:
            st.info("No matching books found to delete.")
        else:
            options = {
                f"{b.get('title', 'Unknown')} by {b.get('author', 'Unknown')} (ISBN: {b.get('isbn', 'N/A')})": idx
                for idx, b in enumerate(matching_books)
            }
            selected_label = st.selectbox("Select Book to Delete:", list(options.keys()))
            selected_book_idx = options[selected_label]
            target_book = matching_books[selected_book_idx]

            if st.button("Delete Selected Book", type="primary"):
                catalog_data["books"] = [b for b in catalog_data["books"] if b != target_book]
                if save_catalog(catalog_data, "catalog.json"):
                    st.success(f"Deleted '{target_book.get('title')}' from catalog!")
                    st.rerun()

    if not books:
        st.warning("⚠️ No catalog data found! Please run `python fetch_catalog.py` to generate `catalog.json`.")
        st.stop()

    # Sidebar Controls
    st.sidebar.header("🔍 Catalog Search & Filters")
    search_query = st.sidebar.text_input("Search Title, Author, or ISBN:", "").strip().lower()

    # Extract all subjects for filtering
    all_subjects = set()
    for book in books:
        for subj in book.get("subjects", []):
            if subj:
                all_subjects.add(subj)
    
    subject_filter = st.sidebar.selectbox(
        "Filter by Subject:",
        ["All Subjects"] + sorted(list(all_subjects))
    )

    status_filter = st.sidebar.radio(
        "Metadata Status:",
        ["All Items", "Found Metadata", "Fallback Entries"]
    )

    sort_option = st.sidebar.selectbox(
        "Sort By:",
        ["Title (A-Z)", "Title (Z-A)", "Publish Year (Newest)", "Publish Year (Oldest)", "Author"]
    )

    # Filter Logic
    filtered_books = []
    for b in books:
        # Search filter
        q = search_query
        title_match = q in b.get("title", "").lower()
        author_match = q in b.get("author", "").lower()
        isbn_match = q in b.get("isbn", "").lower()
        raw_query_match = q in b.get("query", "").lower()
        
        if q and not (title_match or author_match or isbn_match or raw_query_match):
            continue

        # Subject filter
        if subject_filter != "All Subjects":
            if subject_filter not in b.get("subjects", []):
                continue

        # Status filter
        status = b.get("status", "found")
        if status_filter == "Found Metadata" and status != "found":
            continue
        elif status_filter == "Fallback Entries" and status != "fallback":
            continue

        filtered_books.append(b)

    # Sorting Logic
    if sort_option == "Title (A-Z)":
        filtered_books.sort(key=lambda x: x.get("title", "").lower())
    elif sort_option == "Title (Z-A)":
        filtered_books.sort(key=lambda x: x.get("title", "").lower(), reverse=True)
    elif sort_option == "Author":
        filtered_books.sort(key=lambda x: x.get("author", "").lower())
    elif sort_option == "Publish Year (Newest)":
        def get_year(item):
            y = str(item.get("publish_year", "0"))
            digits = "".join([c for c in y if c.isdigit()])
            return int(digits) if digits else 0
        filtered_books.sort(key=get_year, reverse=True)
    elif sort_option == "Publish Year (Oldest)":
        def get_year(item):
            y = str(item.get("publish_year", "9999"))
            digits = "".join([c for c in y if c.isdigit()])
            return int(digits) if digits else 9999
        filtered_books.sort(key=get_year)

    tab_browse, tab_edit = st.tabs(["📚 Browse Catalog", "✏️ Edit Metadata"])

    with tab_browse:
        if not books:
            st.warning("⚠️ No catalog data found! Please run `python fetch_catalog.py` to generate `catalog.json`.")
        elif not filtered_books:
            st.info("ℹ️ No books match your current filter criteria. Try adjusting the search query or sidebar filters.")
        else:
            # Key Performance / Summary Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Catalog Items", total_count)
            with col2:
                st.metric("Filtered Display", len(filtered_books))
            with col3:
                found_cnt = sum(1 for b in books if b.get("status") == "found")
                st.metric("Found via API", found_cnt)
            with col4:
                fallback_cnt = sum(1 for b in books if b.get("status") == "fallback")
                st.metric("Graceful Fallbacks", fallback_cnt)

            st.markdown("---")

            # Render Book Grid (3 columns)
            cols_per_row = 3
            for i in range(0, len(filtered_books), cols_per_row):
                row_books = filtered_books[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                
                for idx, book in enumerate(row_books):
                    with cols[idx]:
                        with st.container(border=True):
                            # Image thumbnail
                            cover = book.get("cover_url") or "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&auto=format&fit=crop&q=80"
                            st.image(cover, use_container_width=True)
                            
                            # Badges
                            status_class = "badge-status-found" if book.get("status") == "found" else "badge-status-fallback"
                            status_label = "API VERIFIED" if book.get("status") == "found" else "FALLBACK"
                            pub_yr = book.get("publish_year", "N/A")
                            incomplete_badge = '<span class="badge badge-incomplete">⚠️ INCOMPLETE INFO</span>' if has_incomplete_info(book) else ''
                            
                            st.markdown(
                                f'<div><span class="badge {status_class}">{status_label}</span>{incomplete_badge}<span class="badge badge-year">📅 {pub_yr}</span></div>',
                                unsafe_allow_html=True
                            )
                            
                            # Title and Author
                            st.markdown(f'<div class="book-title">{book.get("title", "Unknown Title")}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="book-author">✍️ {book.get("author", "Unknown Author")}</div>', unsafe_allow_html=True)
                            
                            # Expandable details
                            with st.expander("📖 View Full Metadata"):
                                st.write(f"**ISBN:** `{book.get('isbn', 'N/A')}`")
                                st.write(f"**Publisher:** {book.get('publisher', 'N/A')}")
                                st.write(f"**Query Source:** `{book.get('query', '')}`")
                                st.write(f"**Description:** {book.get('description', 'No description available.')}")
                                
                                subjects = book.get("subjects", [])
                                if subjects:
                                    st.write("**Subjects / Tags:**")
                                    tags_html = "".join([f'<span class="badge badge-subject">{s}</span>' for s in subjects[:5]])
                                    st.markdown(tags_html, unsafe_allow_html=True)
                                    
                                st.json(book)

    with tab_edit:
        st.subheader("✏️ Edit Book Metadata")
        st.markdown("Select a book from the list on the left to inspect, edit fields, or trigger an Open Library API auto-refresh.")

        col_list, col_form = st.columns([1, 2])

        with col_list:
            st.markdown("### 📖 Select Book to Edit")
            edit_search = st.text_input("Search Catalog:", "", key="edit_tab_search_input").strip().lower()
            matching_edit_books = [b for b in books if match_book(b, edit_search)]

            if "selected_book_idx" not in st.session_state:
                st.session_state.selected_book_idx = 0

            if not matching_edit_books:
                st.info("No matching books found.")
            else:
                for idx, b in enumerate(matching_edit_books):
                    btn_label = f"✏️ {b.get('title', 'Unknown')} ({b.get('author', 'Unknown')})"
                    if st.button(btn_label, key=f"select_book_btn_{idx}"):
                        st.session_state.selected_book_idx = idx
                        st.rerun()

        with col_form:
            if matching_edit_books and st.session_state.selected_book_idx < len(matching_edit_books):
                selected_book = matching_edit_books[st.session_state.selected_book_idx]
                
                # Auto-Refresh Metadata from Open Library API.
                st.markdown("### 🔄 Open Library API Auto-Refresh")
                if st.button("🔄 Refresh Metadata from Open Library API", key="top_api_refresh_btn", type="secondary"):
                    q = selected_book.get("isbn") if selected_book.get("isbn") != "N/A" else selected_book.get("title")
                    try:
                        fetched_item = fetch_book_by_isbn(q) if is_isbn(q) else fetch_book_by_title(q)
                        fetched_dict = fetched_item.model_dump()
                        
                        # Update selected book fields
                        for key, val in fetched_dict.items():
                            if val and val != "N/A":
                                selected_book[key] = val

                        if save_catalog(catalog_data, "catalog.json"):
                            st.success(f"Refreshed metadata for '{selected_book.get('title')}' from Open Library API!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"API refresh failed: {e}")

                st.markdown("---")
                st.markdown("### 📝 Edit Manual Fields")
                
                with st.form("edit_metadata_form"):
                    updated_title = st.text_input("Title", value=selected_book.get("title", ""))
                    updated_author = st.text_input("Author", value=selected_book.get("author", ""))
                    updated_isbn = st.text_input("ISBN", value=selected_book.get("isbn", ""))
                    updated_year = st.text_input("Publish Year", value=selected_book.get("publish_year", ""))
                    
                    # Cover Image URL rendered explicitly as an editable text string
                    updated_cover = st.text_input("Cover Image URL (String)", value=selected_book.get("cover_url", ""))
                    updated_publisher = st.text_input("Publisher", value=selected_book.get("publisher", ""))
                    
                    subjs_str = ", ".join(selected_book.get("subjects", [])) if isinstance(selected_book.get("subjects"), list) else str(selected_book.get("subjects", ""))
                    updated_subjects_raw = st.text_input("Subjects (comma-separated)", value=subjs_str)
                    updated_description = st.text_area("Description", value=selected_book.get("description", ""))

                    save_submitted = st.form_submit_button("💾 Save Changes", type="primary")

                    if save_submitted:
                        subjs_list = [s.strip() for s in updated_subjects_raw.split(",") if s.strip()]
                        selected_book["title"] = updated_title.strip()
                        selected_book["author"] = updated_author.strip()
                        selected_book["isbn"] = updated_isbn.strip()
                        selected_book["publish_year"] = clean_publish_year(updated_year.strip())
                        selected_book["cover_url"] = updated_cover.strip()
                        selected_book["publisher"] = updated_publisher.strip()
                        selected_book["subjects"] = subjs_list
                        selected_book["description"] = updated_description.strip()

                        if save_catalog(catalog_data, "catalog.json"):
                            st.success(f"Saved changes for '{updated_title}'! In-memory cache invalidated.")
                            st.rerun()

    # Footer
    st.markdown("---")
    st.caption(f"Catalog last refreshed: `{generated_at}` • Built with Streamlit & Open Library API")


if __name__ == "__main__":
    main()
