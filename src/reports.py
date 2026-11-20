import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def generate_charts(output_dir: str = os.path.join("output", "charts")):
  """Generates a 2x2 spending dashboard PNG from the SQLite database."""
  receipts, items = load_data()
  if receipts.empty:
    print("No receipts found to chart.")
    return

  os.makedirs(output_dir, exist_ok=True)
  purchased = items[items["is_discount"] == 0]

  fig, axes = plt.subplots(2, 2, figsize=(14, 10))
  fig.suptitle("Personal Grocery Spending Dashboard", fontsize=16, fontweight="bold")

  # 1. Spend by Category (Horizontal Bar)
  by_cat = purchased.groupby("category")["price"].sum().sort_values()
  axes[0, 0].barh(by_cat.index, by_cat.values, color="#4C72B0")
  axes[0, 0].set_title("Spend by Category (R)")
  axes[0, 0].set_xlabel("Amount (R)")
  for idx, val in enumerate(by_cat.values):
    axes[0, 0].text(val + 2, idx, f"R{val:.2f}", va="center", fontsize=9)

  # 2. Monthly Spend (Vertical Bar)
  dated = receipts.dropna(subset=["receipt_date"]).copy()
  if not dated.empty:
    dated["Month"] = dated["receipt_date"].dt.to_period("M").astype(str)
    by_month = dated.groupby("Month")["total_amount"].sum()
    axes[0, 1].bar(by_month.index, by_month.values, color="#55A868", width=0.5)
    axes[0, 1].set_title("Monthly Spend (R)")
    axes[0, 1].set_ylabel("Amount (R)")
    for idx, val in enumerate(by_month.values):
      axes[0, 1].text(idx, val + 5, f"R{val:.2f}", ha="center", fontsize=9)
  else:
    axes[0, 1].text(0.5, 0.5, "No dated receipts", ha="center", va="center")
    axes[0, 1].set_title("Monthly Spend (R)")

  # 3. Spend by Store (Vertical Bar)
  by_store = receipts.groupby("store")["total_amount"].sum().sort_values(ascending=False)
  axes[1, 0].bar(by_store.index, by_store.values, color="#C44E52", width=0.5)
  axes[1, 0].set_title("Spend by Store (R)")
  axes[1, 0].set_ylabel("Amount (R)")
  for idx, val in enumerate(by_store.values):
    axes[1, 0].text(idx, val + 5, f"R{val:.2f}", ha="center", fontsize=9)

  # 4. Top 5 Items by Spend (Horizontal Bar)
  top_items = purchased.groupby("name")["price"].sum().sort_values().tail(5)
  axes[1, 1].barh(top_items.index, top_items.values, color="#8172B2")
  axes[1, 1].set_title("Top 5 Items by Spend (R)")
  axes[1, 1].set_xlabel("Amount (R)")
  for idx, val in enumerate(top_items.values):
    axes[1, 1].text(val + 2, idx, f"R{val:.2f}", va="center", fontsize=9)

  plt.tight_layout(rect=[0, 0, 1, 0.96])
  out_path = os.path.join(output_dir, "spending_dashboard.png")
  plt.savefig(out_path, dpi=150)
  plt.close(fig)
  print(f"\nDashboard chart saved to: {out_path}")

if __name__ == "__main__":
  generate_reports()