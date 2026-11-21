import math
import re
import sys
import os
import json
from statistics import median

STORES_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "stores.json"
)


def reconstruct_lines(ocr_results: list[dict], y_tolerance_ratio: float = 0.45) -> list[str]:
  """Deskews OCR bounding boxes using their median tilt angle, groups them into
  horizontal rows, and sorts each row left-to-right.
  """
  if not ocr_results:
    return []

  # 1. Estimate the receipt's tilt angle from wide text boxes
  angles = []
  for item in ocr_results:
    pt0, pt1, pt2, pt3 = item["box"]
    dx = pt1[0] - pt0[0]
    dy = pt1[1] - pt0[1]
    width = math.hypot(dx, dy)
    height = math.hypot(pt3[0] - pt0[0], pt3[1] - pt0[1])
    if width > height * 2.5:  # Only use wide boxes for a stable angle
      angles.append(math.atan2(dy, dx))

  tilt_angle = median(angles) if angles else 0.0
  cos_a = math.cos(-tilt_angle)
  sin_a = math.sin(-tilt_angle)

  # 2. Rotate each box's center to level the receipt
  enriched = []
  for item in ocr_results:
    box = item["box"]
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2

    # Apply 2D rotation
    rot_x = cx * cos_a - cy * sin_a
    rot_y = cx * sin_a + cy * cos_a

    # Box height along its left edge
    height = math.hypot(box[3][0] - box[0][0], box[3][1] - box[0][1])

    enriched.append({
        "text": item["text"],
        "y_center": rot_y,
        "x_min": rot_x,
        "height": height,
    })

  # 3. Sort top-to-bottom and cluster into horizontal rows
  enriched.sort(key=lambda b: b["y_center"])

  rows = []
  for box in enriched:
    placed = False
    for row in rows:
      avg_y = sum(b["y_center"] for b in row) / len(row)
      avg_h = sum(b["height"] for b in row) / len(row)
      if abs(box["y_center"] - avg_y) <= avg_h * y_tolerance_ratio:
        row.append(box)
        placed = True
        break
    if not placed:
      rows.append([box])

  # 4. Sort each row left-to-right and join
  reconstructed = []
  for row in rows:
    row.sort(key=lambda b: b["x_min"])
    reconstructed.append(" ".join(b["text"] for b in row))

  return reconstructed

def normalize_store_name(lines: list[str]) -> str:
  """Matches the top lines of a receipt against config/stores.json."""
  if not lines:
    return "Unknown"

  header_text = " ".join(lines[:5]).upper()

  if os.path.exists(STORES_CONFIG_PATH):
    with open(STORES_CONFIG_PATH, "r", encoding="utf-8") as f:
      store_rules = json.load(f)

    for canonical_name, keywords in store_rules.items():
      if any(kw in header_text for kw in keywords):
        return canonical_name

  return lines[0].strip().title()

def parse_receipt(lines: list[str]) -> dict:
  """Store-agnostic parser for South African grocery receipts (Shoprite, SuperSpar, etc.)."""
  store = normalize_store_name(lines)
  date = None
  receipt_total = None
  items = []

  # Allows optional 'R', optional space, and 1-2 trailing VAT flags (e.g., 26.99 A, 15.99 *, 1.25NA)
  price_pattern = re.compile(r"(?:^|\s)(-?R?\s*\d+\.\d{2})(?:\s*[A*N]{1,2})?\s*$")
  # Two-line multi-buy WITH line total: e.g., "5@ 1.50 7.50*" or "1@ 24.99 24.99 A"
  multibuy_with_total = re.compile(
      r"^\d+\s*@\s*R?\s*\d+\.\d{2}\s+(-?R?\s*\d+\.\d{2})(?:\s*[A*N]{1,2})?\s*$"
  )
  # Unit-price-only sub-line (Shoprite style): e.g., "2 @ R37.99"
  multibuy_only = re.compile(r"^\d+\s*@\s*R?\s*\d+\.\d{2}\s*$")
  # Matches DD/MM/YY, DD.MM.YY, or DD-MM-YYYY
  date_pattern = re.compile(r"\b(\d{2}[/.-]\d{2}[/.-]\d{2,4})\b")

  stop_keywords = (
      "TENDERED",
      "ELECTRONIC PAYMENT",
      "CREDIT CARD",
      "DEBIT CARD",
      "CASH",
      "CHANGE",
      "VAT RATE",
      "RATE TAX",
  )
  skip_keywords = (
      "FOR ",
      "ITEMS",
      "SUBTOTAL",
      "TEL",
      "VAT NO",
      "TAX INVOICE",
  )
  discount_keywords = ("SAVEXTRA", "XTRASAVE", "DISCOUNT", "LESS ")

  parsing_items = True
  pending_name = None

  for line in lines:
    upper = line.upper()

    # 1. Grab date anywhere on the slip
    if not date:
      date_match = date_pattern.search(line)
      if date_match:
        date = date_match.group(1)

    if not parsing_items:
      continue

    # 2. Stop parsing items once we hit payment or VAT summary sections
    if any(kw in upper for kw in stop_keywords):
      parsing_items = False
      continue

    # 3. Capture TOTAL (updates if a receipt has both a subtotal TOTAL and final TOTAL)
    if "TOTAL" in upper and "SUBTOTAL" not in upper:
      total_match = price_pattern.search(line)
      if total_match:
        raw_total = total_match.group(1).replace("R", "").replace(" ", "")
        receipt_total = float(raw_total)
      pending_name = None
      continue

    # 4. Handle two-line multi-buy with line total (SuperSpar style)
    mb_total_match = multibuy_with_total.match(line)
    if mb_total_match:
      if pending_name:
        raw_price = mb_total_match.group(1).replace("R", "").replace(" ", "")
        price = float(raw_price)
        items.append({
            "name": pending_name,
            "price": price,
            "is_discount": price < 0,
        })
        pending_name = None
      continue

    # 5. Skip unit-price-only multi-buy breakdowns and non-item summary lines
    if multibuy_only.match(line) or any(kw in upper for kw in skip_keywords):
      pending_name = None
      continue

    # 6. Extract standard single-line item and price
    price_match = price_pattern.search(line)
    if price_match:
      raw_price = price_match.group(1).replace("R", "").replace(" ", "")
      price = float(raw_price)
      name = line[: price_match.start()].strip()
      pending_name = None

      if not name:
        continue

      is_discount = price < 0 or any(kw in name.upper() for kw in discount_keywords)
      if is_discount:
        price = -abs(price)

      items.append({
          "name": name,
          "price": price,
          "is_discount": is_discount,
      })
    else:
      # Remember this line in case the next line is a multi-buy price (e.g., "5@ 1.50 7.50*")
      pending_name = line.strip()

  calculated_total = round(sum(item["price"] for item in items), 2)

  return {
      "store": store,
      "date": date,
      "items": items,
      "receipt_total": receipt_total,
      "calculated_total": calculated_total,
      "totals_match": receipt_total is not None and receipt_total == calculated_total,
  }


if __name__ == "__main__":

  from ocr_engine import extract_receipt_text

  if len(sys.argv) < 2:
    print("Usage: python src/parser.py data/sample_receipts/Receipt3.jpg")
    sys.exit(1)

  raw_ocr = extract_receipt_text(sys.argv[1], save_debug=False)
  clean_lines = reconstruct_lines(raw_ocr)
  parsed = parse_receipt(clean_lines)

  print(f"\nStore: {parsed['store']} | Date: {parsed['date']}")
  print("-" * 45)
  for item in parsed["items"]:
    tag = " (DISCOUNT)" if item["is_discount"] else ""
    print(f"{item['name']:<30} R{item['price']:>7.2f}{tag}")
  print("-" * 45)
  print(f"Calculated Total: R{parsed['calculated_total']:.2f}")
  if parsed["receipt_total"] is not None:
    print(f"Receipt Total:    R{parsed['receipt_total']:.2f}")
  else:
    print("Receipt Total:    Not found")
  print(f"Exact Match:      {parsed['totals_match']}")