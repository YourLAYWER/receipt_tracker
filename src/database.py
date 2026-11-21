import os
import sqlite3
import sys
from datetime import datetime
from ocr_engine import extract_receipt_text
from parser import normalize_store_name,parse_receipt, reconstruct_lines
from categorizer import categorize_item

DB_PATH = os.path.join("data", "expenses.db")


def get_connection() -> sqlite3.Connection:
  os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
  conn = sqlite3.connect(DB_PATH)
  conn.execute("PRAGMA foreign_keys = ON;")
  return conn


def init_db():
  """Creates the receipts and line_items tables if they don't exist."""
  with get_connection() as conn:
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store TEXT NOT NULL,
        receipt_date TEXT,
        total_amount REAL NOT NULL,
        image_filename TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS line_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'Uncategorized',
        price REAL NOT NULL,
        is_discount INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (receipt_id) REFERENCES receipts(id) ON DELETE CASCADE
      );
    """)


def normalize_date(date_str: str | None) -> str | None:
  """Converts DD/MM/YY, DD.MM.YY, or DD-MM-YYYY into ISO YYYY-MM-DD."""
  if not date_str:
    return None
  formats = ("%d/%m/%y", "%d/%m/%Y", "%d.%m.%y", "%d.%m.%Y", "%d-%m-%y", "%d-%m-%Y")
  for fmt in formats:
    try:
      return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
    except ValueError:
      continue
  return date_str


def save_receipt(parsed: dict, image_filename: str = "") -> int | None:
  """Saves a parsed receipt and its line items. Skips if a duplicate is detected."""
  init_db()
  iso_date = normalize_date(parsed["date"])
  total = parsed["receipt_total"] if parsed["receipt_total"] is not None else parsed["calculated_total"]

  with get_connection() as conn:
    cursor = conn.cursor()

    # Duplicate check (same store, date, and total)
    cursor.execute(
        """
        SELECT id FROM receipts
        WHERE store = ? AND receipt_date IS ? AND total_amount = ?
        """,
        (parsed["store"], iso_date, total),
    )
    existing = cursor.fetchone()
    if existing:
      print(f"Skipping duplicate: Receipt already exists with ID {existing[0]}.")
      return None

    # Insert receipt header
    cursor.execute(
        """
        INSERT INTO receipts (store, receipt_date, total_amount, image_filename)
        VALUES (?, ?, ?, ?)
        """,
        (parsed["store"], iso_date, total, image_filename),
    )
    receipt_id = cursor.lastrowid

    # Insert line items
    item_rows = [
        (
            receipt_id,
            item["name"],
            item.get("category") or categorize_item(item["name"], item["is_discount"]),
            item["price"],
            int(item["is_discount"]),
        )
        for item in parsed["items"]
    ]
    cursor.executemany(
        """
        INSERT INTO line_items (receipt_id, name, category, price, is_discount)
        VALUES (?, ?, ?, ?, ?)
        """,
        item_rows,
    )

    return receipt_id

def recategorize_all():
  """Re-runs the categorizer on all existing items in the database."""
  with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, is_discount FROM line_items")
    rows = cursor.fetchall()

    updates = [
        (categorize_item(name, bool(is_discount)), item_id)
        for item_id, name, is_discount in rows
    ]
    cursor.executemany("UPDATE line_items SET category = ? WHERE id = ?", updates)
  print(f"Updated categories for {len(updates)} items.")


def normalize_existing_stores():
  """Normalizes store names for all existing receipts in the database."""
  with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id, store FROM receipts")
    rows = cursor.fetchall()

    updates = [(normalize_store_name([store]), r_id) for r_id, store in rows]
    cursor.executemany("UPDATE receipts SET store = ? WHERE id = ?", updates)
  print(f"Normalized store names for {len(updates)} receipts.")

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("Usage: python src/database.py data/sample_receipts/Receipt1.jpg")
    sys.exit(1)

  img_path = sys.argv[1]
  raw_ocr = extract_receipt_text(img_path, save_debug=False)
  parsed_data = parse_receipt(reconstruct_lines(raw_ocr))

  if not parsed_data["totals_match"]:
    print("Warning: Calculated total does not match receipt total. Review before saving.")

  new_id = save_receipt(parsed_data, os.path.basename(img_path))
  if new_id:
    print(f"Saved receipt #{new_id} ({len(parsed_data['items'])} items) to {DB_PATH}")