import math
import os
import sys

# Allow importing from src/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from parser import parse_receipt, reconstruct_lines


def test_shoprite_receipt_parsing():
  lines = [
      "SHOPRITE",
      "SHOPRITE CHECKERS (PTY) LTD",
      "VAT No: 4420106777",
      "TAX INVOICE",
      "WHTSTAR CHOC 1KG R32.99",
      "SELATI BRW 500G R19.99",
      "RB DISHWASH REFI R21.99",
      "WHTSTAR VAN 1KG R32.99",
      "XTRASAVE PORRIDGE -R18.00",
      "WHT STAR 10KG R129.99A",
      "XTRASAVE M MEAL -R30.00",
      "FRST CHOICE 2KG R34.99A",
      "XTRASAVE AMASI -R5.00",
      "NOODLES 5X70G R75.98",
      "2 @ R37.99",
      "XTRASAVE NOODLES -R17.98",
      "AER 10G R19.99",
      "FCHOIC FC 6X1L. R119.99A",
      "XTRASAVE MILK UHT -R22.00",
      "CHECKOUT BAG SR R2.80",
      "2@ R1.40",
      "PNUTB SMTH 400G R52.99",
      "XTRASAVE BLACK CAT -R16.00",
      "TOTAL [13] R435.71",
      "Electronic Payment R435.71",
      "05/10/26 14:03",
  ]

  result = parse_receipt(lines)

  assert result["store"] == "Shoprite"
  assert result["date"] == "05/10/26"
  assert result["receipt_total"] == 435.71
  assert result["calculated_total"] == 435.71
  assert result["totals_match"] is True
  assert len(result["items"]) == 17  # Excludes the two multi-buy sub-lines


def test_superspar_receipt_parsing():
  lines = [
      "SUPERSPARO",
      "Welcome to",
      "SUMMERBREEZZ SUPERSPAR",
      "VAT NO: 4480232463",
      "WILLARDS P/CORN 80G 11.99",
      "WILLARDS P/CORN 80G 11.99",
      "F/L BROWN 700GR 14.99*",
      "SPAR H/C KITCHEN 15EA 32.99",
      "SPAR CARR VT1 1'S 1.40N",
      "FOR 5 ITEMS 73.36",
      "SAVEXTRA SPAR B/Bread70 1.00",
      "TOTAL 72.36",
      "TENDERED Credit Card 72.36",
      "24.09.26 17:33",
  ]

  result = parse_receipt(lines)

  assert result["store"] == "SuperSpar"
  assert result["date"] == "24.09.26"
  assert result["receipt_total"] == 72.36
  assert result["calculated_total"] == 72.36
  assert result["totals_match"] is True
  assert len(result["items"]) == 6

  # Verify SAVEXTRA discount was automatically negated
  discounts = [i for i in result["items"] if i["is_discount"]]
  assert len(discounts) == 1
  assert discounts[0]["price"] == -1.00


def test_deskew_reconstruct_lines():
  """Simulates a 5-degree tilted receipt where the price sits lower than the item."""
  angle = math.radians(5)
  cos_a, sin_a = math.cos(angle), math.sin(angle)

  def rotate_box(x, y, w, h):
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [[cx * cos_a - cy * sin_a, cx * sin_a + cy * cos_a] for cx, cy in corners]

  tilted_ocr = [
      {"text": "WHTSTAR CHOC 1KG", "box": rotate_box(0, 100, 200, 20)},
      {"text": "R32.99", "box": rotate_box(400, 100, 80, 20)},
      {"text": "SELATI BRW 500G", "box": rotate_box(0, 130, 200, 20)},
      {"text": "R19.99", "box": rotate_box(400, 130, 80, 20)},
  ]

  reconstructed = reconstruct_lines(tilted_ocr)
  assert reconstructed == [
      "WHTSTAR CHOC 1KG R32.99",
      "SELATI BRW 500G R19.99",
  ]