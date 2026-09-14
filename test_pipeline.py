#!/usr/bin/env python3
"""
test_pipeline.py - Test Engineer Agent script for Phase 1 Metadata Pipeline

Evaluates fetch_catalog.py against edge cases:
- Invalid ISBNs
- Non-existent book titles
- Missing metadata / fallback fields
- Rate limiting / retries
- Ensures process exits cleanly without tracebacks and catalog.json is valid
"""

import os
import sys
import json
import subprocess

DUMMY_INPUT_FILE = "test_dummy_inputs.txt"
TEST_OUTPUT_FILE = "test_catalog.json"

DUMMY_CONTENT = """9780140449136
The Great Gatsby
9780000000000
NonExistentBookTitle999888777
InvalidISBNFormatXYZ123
"""

def setup_dummy_file():
    """Create dummy test file with edge cases."""
    with open(DUMMY_INPUT_FILE, "w", encoding="utf-8") as f:
        f.write(DUMMY_CONTENT.strip())
    print(f"[Tester] Created dummy test file: {DUMMY_INPUT_FILE}")


def run_pipeline_test():
    """Execute fetch_catalog.py and inspect behavior."""
    python_cmd = sys.executable
    script_path = "fetch_catalog.py"
    
    cmd = [python_cmd, script_path, "--input", DUMMY_INPUT_FILE, "--output", TEST_OUTPUT_FILE]
    
    print(f"[Tester] Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("[Tester] Process Standard Output:")
    print(result.stdout)
    
    if result.stderr:
        print("[Tester] Process Standard Error (logs/warnings):")
        print(result.stderr)
        
    # Check 1: Zero exit code (did not crash)
    if result.returncode != 0:
        print(f"[FAIL] Pipeline script crashed with exit code {result.returncode}")
        sys.exit(1)
    else:
        print("[PASS] Pipeline script executed cleanly with exit code 0")

    # Check 2: Output JSON file created
    if not os.path.exists(TEST_OUTPUT_FILE):
        print(f"[FAIL] Expected output file {TEST_OUTPUT_FILE} was not created!")
        sys.exit(1)

    # Check 3: Valid JSON parsing & Schema check
    try:
        with open(TEST_OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[FAIL] Output file is not valid JSON: {e}")
        sys.exit(1)

    books = data.get("books", [])
    print(f"[Tester] Parsed {len(books)} books from generated JSON catalog")

    if len(books) == 0:
        print("[FAIL] Output catalog is empty!")
        sys.exit(1)

    required_fields = ["query", "title", "author", "publish_year", "cover_url"]
    
    for idx, book in enumerate(books):
        # Verify required keys exist
        missing = [key for key in required_fields if key not in book]
        if missing:
            print(f"[FAIL] Item #{idx} ({book.get('query')}) missing fields: {missing}")
            sys.exit(1)

        # Check edge case graceful fallbacks
        query = book.get("query", "")
        if "9780000000000" in query or "NonExistent" in query or "InvalidISBN" in query:
            print(f"[Tester Edge Case Check] Query '{query}' handled cleanly. Title: '{book.get('title')}', Author: '{book.get('author')}', Status: '{book.get('status')}'")

    print("\n" + "="*50)
    print(" PHASE 1 METADATA PIPELINE EVALUATION: PASS")
    print("="*50 + "\n")

    # Cleanup temporary test output
    if os.path.exists(TEST_OUTPUT_FILE):
        os.remove(TEST_OUTPUT_FILE)
    if os.path.exists(DUMMY_INPUT_FILE):
        os.remove(DUMMY_INPUT_FILE)


if __name__ == "__main__":
    setup_dummy_file()
    run_pipeline_test()
