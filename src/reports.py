import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join("data", "expenses.db")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
  if not os.path.exists(DB_PATH):
    raise FileNotFoundError(f"Database not found at {DB_PATH}. Save a receipt first.")

  with sqlite3.connect(DB_PATH) as conn:
    receipts = pd.read_sql_query("SELECT * FROM receipts", conn)
    items = pd.read_sql_query(
        """
        SELECT li.*, r.store, r.receipt_date
        FROM line_items li
        JOIN receipts r ON li.receipt_id = r.id
        """,
        conn,
    )

  receipts["receipt_date"] = pd.to_datetime(receipts["receipt_date"], errors="coerce")
  items["receipt_date"] = pd.to_datetime(items["receipt_date"], errors="coerce")
  return receipts, items


def print_section(title: str):
  print(f"\n{'=' * 50}\n{title}\n{'=' * 50}")


def generate_reports():
  receipts, items = load_data()

  if receipts.empty:
    print("No receipts found in the database.")
    return

  # 1. Overall Summary
  total_spent = receipts["total_amount"].sum()
  total_saved = abs(items.loc[items["is_discount"] == 1, "price"].sum())

  print_section("OVERALL SUMMARY")
  print(f"Receipts Logged:  {len(receipts)}")
  print(f"Total Spent:      R{total_spent:,.2f}")
  print(f"Total Discounts:  R{total_saved:,.2f}")

  # 2. Spend by Store
  print_section("SPEND BY STORE")
  by_store = receipts.groupby("store")["total_amount"].agg(["count", "sum"])
  by_store.columns = ["Visits", "Total (R)"]
  print(by_store.to_string())

  # 3. Time-Based Reports (Weekly, Monthly, Yearly)
  dated = receipts.dropna(subset=["receipt_date"]).copy()
  if not dated.empty:
    dated["Year"] = dated["receipt_date"].dt.to_period("Y")
    dated["Month"] = dated["receipt_date"].dt.to_period("M")
    dated["Week"] = dated["receipt_date"].dt.to_period("W")

    for label, col in [("WEEKLY SPEND", "Week"), ("MONTHLY SPEND", "Month"), ("YEARLY SPEND", "Year")]:
      print_section(label)
      summary = dated.groupby(col)["total_amount"].agg(["count", "sum"])
      summary.columns = ["Receipts", "Total (R)"]
      print(summary.to_string())
      
      
    # 3.5 Spend by Category (excluding discounts)
  print_section("SPEND BY CATEGORY")
  purchased = items[items["is_discount"] == 0]
  by_cat = (
      purchased.groupby("category")["price"]
      .agg(["count", "sum"])
      .sort_values(by="sum", ascending=False)
  )
  by_cat.columns = ["Items", "Total (R)"]
  print(by_cat.to_string())

  # 4. Top Purchased Items (excluding discounts)
  print_section("TOP ITEMS BY SPEND")
  # purchased = items[items["is_discount"] == 0]
  top_items = (
      purchased.groupby("name")["price"]
      .agg(["count", "sum"])
      .sort_values(by="sum", ascending=False)
      .head(10)
  )
  top_items.columns = ["Times Bought", "Total (R)"]
  print(top_items.to_string())




if __name__ == "__main__":
  generate_reports()