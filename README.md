# Receipt Tracker

An offline, CPU-friendly receipt scanner and personal expense analytics pipeline built with **OpenCV**, **PaddleOCR**, **SQLite**, and **Pandas**.

## Features
* **Offline OCR:** Extracts text from angled or imperfect phone photos of grocery slips using PaddleOCR (CPU-only).
* **Mathematical Deskewing:** Automatically levels tilted receipt photos using bounding-box geometry before reconstructing rows.
* **Store-Agnostic Parsing:** Handles multiple South African retail formats (e.g., Shoprite, SuperSpar), negative/positive discount lines, VAT markers, and multi-buy sub-lines with built-in total reconciliation.
* **Auto-Categorization & Reporting:** Categorizes line items via keyword rules, stores them in SQLite with duplicate protection, and generates weekly, monthly, yearly, store, and category spending reports.

## Project Structure
```text
receipt-tracker/
├── data/
│   ├── sample_receipts/   # Receipt images to scan
│   └── expenses.db        # Auto-generated SQLite database
├── output/                # Optional OCR bounding-box debug images
├── src/
│   ├── ocr_engine.py      # OpenCV resizing + PaddleOCR extraction
│   ├── parser.py          # Deskewing, row reconstruction, and Regex parsing
│   ├── categorizer.py     # Keyword-based item categorization
│   ├── database.py        # SQLite schema, date normalization, duplicate checks
│   └── reports.py         # Pandas spending summaries
├── main.py                # CLI entry point
└── README.md

