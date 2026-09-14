# 📚 Personal Book Catalog & Dual-Agent Supervisor Workflow

An interactive book library management application powered by **Streamlit**, **Open Library API**, and an autonomous **Dual-Agent Supervisor Workflow**.

---

## 🌟 Features

### 1. 📚 Browse Catalog
- **Responsive Book Grid**: Displays book covers, author details, publication year badges, and metadata status badges.
- **`API VERIFIED` vs `FALLBACK` Badges**: Visual indicators showing whether book details were verified via Open Library API or generated gracefully via fallbacks.
- **`⚠️ INCOMPLETE INFO` Badges**: Automatically detects missing or placeholder fields (e.g. empty subjects, missing descriptions, `"N/A"`) and flags items requiring metadata attention.
- **Metadata Expander**: Inspect full JSON records, publisher details, and subject tags per book.
- **Search & Filters**: Filter by subject, metadata status, title, author, or ISBN, and sort by title, author, or publication year.

### 2. ✏️ Edit Metadata
- **Top-Level Navigation Tabs**: Seamlessly switch between **"📚 Browse Catalog"** and **"✏️ Edit Metadata"**.
- **Two-Column Edit Layout**: Searchable book selection list on the left with a pre-filled edit form on the right.
- **Top-Level Open Library API Auto-Refresh**: One-click button (`🔄 Refresh Metadata from Open Library API`) to automatically re-fetch and replace missing fields from Open Library.
- **Text String Cover URLs**: Edit cover image URLs directly as text input strings.
- **Automated Year Formatting**: Automatically cleans dates (e.g. converting `"2023-07-25"` or `"July 25, 2023"` into 4-digit `"2023"`) upon saving.
- **Instant In-Memory Cache Invalidation**: Calls `st.cache_data.clear()` on save so updated data and badge state changes take effect instantly.

### 3. ➕ Add & 🗑️ Delete Books
- **Add New Book**: Sidebar form to introduce new books manually into `catalog.json`.
- **Delete Book**: Sidebar form to search by Title, Author, or ISBN and remove entries cleanly.

### 4. 🤖 Dual-Agent Supervisor Workflow
- **Script Writer Specialist (`script_writer`)**: Generates and refines code logic based on specifications and error feedback logs.
- **Test Engineer Specialist (`test_engineer`)**: Validates scripts against automated test suites (`test_pipeline.py`, `test_ui.py`).
- **Supervisor Orchestrator (`dual_agent_supervisor.py`)**: Manages context handoffs and automated retry loops.

---

## 📁 Project Structure

```
BookCatalog/
├── app.py                   # Streamlit Web Application (UI, Tabs, Editing, Filters)
├── fetch_catalog.py         # Open Library API Fetcher & Metadata Pipeline
├── dual_agent_supervisor.py # Dual-Agent Supervisor Runner & Protocol Context Models
├── test_pipeline.py         # Test Engineer Suite for Metadata Fetching Pipeline
├── test_ui.py               # Test Engineer Suite for Streamlit UI & Data Persistence
├── catalog.json             # Structured JSON Catalog Storage
├── books_sample.txt         # Input sample text file containing ISBNs/Titles
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- Virtual environment (recommended)

### Installation Steps

1. **Clone or navigate to project directory**:
   ```bash
   cd BookCatalog
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

### 1. Launch the Streamlit Web Application
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 2. Run the Metadata Pipeline Fetcher
To fetch metadata for a list of ISBNs/Titles from an input file:
```bash
python fetch_catalog.py --input books_sample.txt --output catalog.json
```

### 3. Execute the Dual-Agent Supervisor Workflow
Run the supervisor runner to orchestrate code generation and automated testing:
```bash
python dual_agent_supervisor.py \
  --task-id "task-001" \
  --spec "Add new feature specification" \
  --script "app.py" \
  --test "test_ui.py" \
  --max-iterations 3
```

### 4. Run Automated Test Suites
```bash
python test_ui.py        # UI & Catalog Persistence Test Suite
python test_pipeline.py # Metadata Pipeline Test Suite
```

---

## 📄 License
Educational & Demonstrative Project powered by Open Library API and Antigravity Agent Framework.
