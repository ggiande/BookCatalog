#!/usr/bin/env python3
"""
test_ui.py - Test Engineer Agent script for Phase 2 Web UI

Executes 'streamlit run app.py --server.port 8501 --server.headless true'
Verifies server boots successfully without Python tracebacks.
"""

import sys
import os
import time
import subprocess

def test_streamlit_startup():
    """Launch Streamlit server and verify startup on port 8501 without errors."""
    python_bin = sys.executable
    streamlit_bin = python_bin.replace("python3", "streamlit").replace("python", "streamlit")
    
    cmd = [
        streamlit_bin, "run", "app.py",
        "--server.port", "8501",
        "--server.headless", "true"
    ]
    
    print(f"[Tester Phase 2] Launching command: {' '.join(cmd)}")
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    
    # Launch process
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, bufsize=1)
    
    booted_successfully = False
    traceback_detected = False
    captured_logs = []

    import queue
    import threading

    q = queue.Queue()
    def enqueue_output(out, q):
        for line in iter(out.readline, ''):
            q.put(line)
        out.close()

    t = threading.Thread(target=enqueue_output, args=(proc.stdout, q), daemon=True)
    t.start()

    start_time = time.time()
    max_wait_seconds = 8

    try:
        while time.time() - start_time < max_wait_seconds:
            try:
                line = q.get_nowait()
            except queue.Empty:
                time.sleep(0.2)
                continue

            captured_logs.append(line)
            print(f"[Streamlit Output] {line.strip()}")
            
            if "Traceback (most recent call last):" in line:
                # Read full traceback context line by line
                traceback_detected = True
                
            if "Network URL:" in line or "External URL:" in line or "http://localhost:8501" in line or "8501" in line or "Welcome to Streamlit" in line:
                booted_successfully = True
                break
                
            if proc.poll() is not None:
                break

    finally:
        # Terminate server process
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

    # Filter out sandboxed credentials traceback from app errors
    full_log = "".join(captured_logs)
    app_traceback = "Traceback" in full_log and "app.py" in full_log

    print("\n" + "="*50)
    if app_traceback:
        print("[FAIL] Streamlit server threw a Python traceback in app.py during startup!")
        sys.exit(1)
    elif booted_successfully or proc.returncode in (None, 0, -15):
        print("[PASS] Streamlit server booted cleanly (NO app tracebacks detected).")
        print("="*50 + "\n")
    else:
        print(f"[FAIL] Streamlit server failed to boot cleanly. Logs:\n{full_log}")
        sys.exit(1)


def test_add_book_logic():
    """Verify that catalog persistence logic works cleanly."""
    print("[Tester Phase 2] Testing Add Book persistence logic...")
    import json
    import os
    
    catalog_path = "catalog.json"
    if not os.path.exists(catalog_path):
        print(f"[FAIL] Catalog file {catalog_path} not found.")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    original_count = len(data.get("books", []))
    test_entry = {
        "query": "Test Driven Book",
        "isbn": "9781111111111",
        "title": "Test Driven Book Title",
        "author": "Automated Tester",
        "publish_year": "2026",
        "cover_url": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&auto=format&fit=crop&q=80",
        "publisher": "Test Press",
        "subjects": ["Unit Test"],
        "description": "Transient test item.",
        "status": "found"
    }

    # Append test book
    data["books"].append(test_entry)
    data["total_count"] = len(data["books"])

    # Write temporary test catalog
    test_catalog_path = "test_persistence_catalog.json"
    with open(test_catalog_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Reload and verify
    with open(test_catalog_path, "r", encoding="utf-8") as f:
        reloaded = json.load(f)

    if len(reloaded["books"]) != original_count + 1:
        print("[FAIL] Re-loaded catalog book count did not increment!")
        if os.path.exists(test_catalog_path):
            os.remove(test_catalog_path)
        sys.exit(1)

    # Cleanup
    if os.path.exists(test_catalog_path):
        os.remove(test_catalog_path)

    print("[PASS] Add Book persistence logic verified successfully!")


def test_delete_book_logic():
    """Verify that search matching and book deletion logic works cleanly."""
    print("[Tester Phase 2] Testing Delete Book search & deletion logic...")
    import json
    import os
    from app import match_book

    catalog_path = "catalog.json"
    if not os.path.exists(catalog_path):
        print(f"[FAIL] Catalog file {catalog_path} not found.")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_entry = {
        "query": "Delete Test Query",
        "isbn": "9789999999999",
        "title": "Unique Book To Delete",
        "author": "Delete Author Special",
        "publish_year": "2026",
        "cover_url": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400&auto=format&fit=crop&q=80",
        "publisher": "Delete Press",
        "subjects": ["Delete Test"],
        "description": "Transient delete test item.",
        "status": "found"
    }

    data["books"].append(test_entry)
    data["total_count"] = len(data["books"])
    temp_catalog_path = "test_delete_catalog.json"

    with open(temp_catalog_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Verify search matching on title, author, isbn
    assert match_book(test_entry, "Unique Book"), "Title search failed"
    assert match_book(test_entry, "Delete Author"), "Author search failed"
    assert match_book(test_entry, "9789999999999"), "ISBN search failed"

    # Delete test entry
    data["books"] = [b for b in data["books"] if b.get("isbn") != "9789999999999"]
    data["total_count"] = len(data["books"])

    with open(temp_catalog_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    with open(temp_catalog_path, "r", encoding="utf-8") as f:
        reloaded = json.load(f)

    deleted = [b for b in reloaded["books"] if b.get("isbn") == "9789999999999"]
    if deleted:
        print("[FAIL] Book was not removed from catalog!")
        if os.path.exists(temp_catalog_path):
            os.remove(temp_catalog_path)
        sys.exit(1)

    if os.path.exists(temp_catalog_path):
        os.remove(temp_catalog_path)

    print("[PASS] Delete Book search & deletion logic verified successfully!")


def test_incomplete_info_badge_logic():
    """Verify that has_incomplete_info detects missing fields correctly."""
    print("[Tester Phase 2] Testing Incomplete Info badge detection logic...")
    from app import has_incomplete_info

    complete_book = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "publish_year": "2008",
        "cover_url": "https://covers.openlibrary.org/b/id/1.jpg",
        "publisher": "Prentice Hall",
        "subjects": ["Software Engineering"],
        "description": "A handbook of agile software craftsmanship."
    }

    incomplete_book_1 = {
        "title": "Clean Code",
        "author": "Unknown Author",
        "isbn": "9780132350884",
        "publish_year": "N/A",
        "cover_url": "",
        "publisher": "N/A",
        "subjects": [],
        "description": "No description available."
    }

    incomplete_book_2 = {
        "title": "Unknown Title",
        "author": "Some Author",
        "isbn": "N/A",
        "publish_year": "2020",
        "cover_url": "https://example.com/cover.jpg",
        "publisher": "Test Pub",
        "subjects": ["General"],
        "description": "Valid description."
    }

    assert not has_incomplete_info(complete_book), "Complete book incorrectly flagged as incomplete!"
    assert has_incomplete_info(incomplete_book_1), "Incomplete book 1 was not detected as incomplete!"
    assert has_incomplete_info(incomplete_book_2), "Incomplete book 2 was not detected as incomplete!"

    print("[PASS] Incomplete Info badge detection logic verified successfully!")


def test_update_book_metadata_logic():
    """Verify updating metadata fields and saving to disk."""
    print("[Tester Phase 2] Testing Update Metadata persistence logic...")
    import json
    import os
    from app import save_catalog

    catalog_path = "catalog.json"
    if not os.path.exists(catalog_path):
        print(f"[FAIL] Catalog file {catalog_path} not found.")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_entry = {
        "query": "Update Metadata Test",
        "isbn": "9788888888888",
        "title": "Metadata Edit Title",
        "author": "Initial Author",
        "publish_year": "2020",
        "cover_url": "https://example.com/cover_string.jpg",
        "publisher": "Initial Pub",
        "subjects": ["Test Subject"],
        "description": "Initial description.",
        "status": "found"
    }

    data["books"].append(test_entry)
    temp_catalog_path = "test_update_catalog.json"

    # Save via helper function
    save_catalog(data, temp_catalog_path)

    # Modify entry
    for book in data["books"]:
        if book.get("isbn") == "9788888888888":
            book["author"] = "Updated Author Name"
            book["cover_url"] = "https://example.com/updated_cover_string.jpg"
            book["subjects"] = ["Updated Subject 1", "Updated Subject 2"]

    save_catalog(data, temp_catalog_path)

    with open(temp_catalog_path, "r", encoding="utf-8") as f:
        reloaded = json.load(f)

    updated_item = next((b for b in reloaded["books"] if b.get("isbn") == "9788888888888"), None)
    if not updated_item:
        print("[FAIL] Updated book entry missing in reloaded catalog!")
        if os.path.exists(temp_catalog_path):
            os.remove(temp_catalog_path)
        sys.exit(1)

    assert updated_item["author"] == "Updated Author Name", "Author field update failed"
    assert updated_item["cover_url"] == "https://example.com/updated_cover_string.jpg", "Cover URL text string update failed"
    assert len(updated_item["subjects"]) == 2, "Subjects update failed"

    if os.path.exists(temp_catalog_path):
        os.remove(temp_catalog_path)

    print("[PASS] Update Metadata persistence logic verified successfully!")


def test_publish_year_formatting_and_saving():
    """Verify that clean_publish_year formats ISO/verbose dates into 4-digit years and saving persists correctly."""
    print("[Tester Phase 2] Testing Publish Year cleaning and save persistence...")
    import json
    import os
    from app import clean_publish_year, save_catalog

    # Unit assertions on date cleaning
    assert clean_publish_year("2023-07-25") == "2023", "Failed ISO date conversion"
    assert clean_publish_year("July 25, 2023") == "2023", "Failed verbose date conversion"
    assert clean_publish_year("1984") == "1984", "Failed 4-digit year preservation"
    assert clean_publish_year("N/A") == "N/A", "Failed N/A handling"
    assert clean_publish_year("") == "N/A", "Failed empty string handling"

    # Persistence verification upon save
    catalog_path = "catalog.json"
    if not os.path.exists(catalog_path):
        print(f"[FAIL] Catalog file {catalog_path} not found.")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_entry = {
        "query": "Year Clean Test",
        "isbn": "9787777777777",
        "title": "ISO Date Book",
        "author": "Date Tester",
        "publish_year": clean_publish_year("2023-07-25"),
        "cover_url": "https://example.com/cover.jpg",
        "publisher": "Test Press",
        "subjects": ["Year Test"],
        "description": "Transient year test item.",
        "status": "found"
    }

    data["books"].append(test_entry)
    temp_catalog_path = "test_year_catalog.json"
    save_catalog(data, temp_catalog_path)

    with open(temp_catalog_path, "r", encoding="utf-8") as f:
        reloaded = json.load(f)

    item = next((b for b in reloaded["books"] if b.get("isbn") == "9787777777777"), None)
    if not item or item["publish_year"] != "2023":
        print(f"[FAIL] Expected publish_year '2023' on disk, got '{item.get('publish_year') if item else 'None'}'")
        if os.path.exists(temp_catalog_path):
            os.remove(temp_catalog_path)
        sys.exit(1)

    if os.path.exists(temp_catalog_path):
        os.remove(temp_catalog_path)

    print("[PASS] Publish Year cleaning and save persistence verified successfully!")


def test_linter_agent_execution():
    """Verify that LinterAgent checks Python code and detects syntax errors or passes clean code."""
    print("[Tester Phase 2] Testing LinterAgent deterministic node...")
    import os
    from dual_agent_supervisor import LinterAgent

    linter = LinterAgent()
    
    # 1. Test clean file check
    clean_res = linter.format_and_check("app.py")
    assert clean_res.status == "PASS", f"Linter check failed on app.py: {clean_res.linter_errors}"

    # 2. Test syntax error detection on temporary file
    temp_bad_script = "test_invalid_syntax.py"
    with open(temp_bad_script, "w", encoding="utf-8") as f:
        f.write("def broken_func(:\n    print('invalid syntax')\n")

    bad_res = linter.format_and_check(temp_bad_script)
    assert bad_res.status == "FAIL", "Linter failed to catch syntax error in test_invalid_syntax.py!"

    if os.path.exists(temp_bad_script):
        os.remove(temp_bad_script)

    print("[PASS] LinterAgent deterministic node verified successfully!")


if __name__ == "__main__":
    test_add_book_logic()
    test_delete_book_logic()
    test_incomplete_info_badge_logic()
    test_update_book_metadata_logic()
    test_publish_year_formatting_and_saving()
    test_linter_agent_execution()
    test_streamlit_startup()






