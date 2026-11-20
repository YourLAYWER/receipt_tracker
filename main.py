import argparse
import os
import sys

# Allow importing modules from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import recategorize_all, save_receipt
from ocr_engine import extract_receipt_text
from parser import parse_receipt, reconstruct_lines
from reports import generate_reports, generate_charts

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def process_single_receipt(image_path: str, save_debug: bool = False):
  print(f"\nScanning: {image_path}")
  raw_ocr = extract_receipt_text(image_path, save_debug=save_debug)
  parsed = parse_receipt(reconstruct_lines(raw_ocr))

  print(f"Store: {parsed['store']} | Date: {parsed['date']} | Items: {len(parsed['items'])}")
  print(f"Calculated: R{parsed['calculated_total']:.2f} | Receipt Total: {parsed['receipt_total']}")

  if not parsed["totals_match"]:
    choice = input("Warning: Totals do not match. Save anyway? [y/N]: ").strip().lower()
    if choice != "y":
      print("Skipped.")
      return

  new_id = save_receipt(parsed, os.path.basename(image_path))
  if new_id:
    print(f"Saved as Receipt #{new_id}.")


def handle_scan(target: str, debug: bool):
  if os.path.isfile(target):
    process_single_receipt(target, save_debug=debug)
  elif os.path.isdir(target):
    files = sorted(
        f for f in os.listdir(target) if f.lower().endswith(IMAGE_EXTENSIONS)
    )
    if not files:
      print(f"No images found in {target}")
      return
    for filename in files:
      process_single_receipt(os.path.join(target, filename), save_debug=debug)
  else:
    print(f"Path not found: {target}")


def main():
  parser = argparse.ArgumentParser(description="Local Receipt Scanner & Expense Tracker")
  subparsers = parser.add_subparsers(dest="command", required=True)

  # scan command
  scan_parser = subparsers.add_parser("scan", help="Scan a receipt image or folder of images")
  scan_parser.add_argument("path", help="Path to a receipt image or directory")
  scan_parser.add_argument("--debug", action="store_true", help="Save OCR bounding-box debug images to output/")

  # report command
  #subparsers.add_parser("report", help="Generate spending reports")
  report_parser = subparsers.add_parser("report", help="Generate spending reports")
  report_parser.add_argument("--charts", action="store_true", help="Save visual charts to output/charts/")

  # recategorize command
  subparsers.add_parser("recategorize", help="Re-apply category rules to all saved items")
  

  args = parser.parse_args()

  if args.command == "scan":
    handle_scan(args.path, args.debug)
  elif args.command == "report":
    generate_reports()
    if args.charts:
      generate_charts()
  elif args.command == "recategorize":
    recategorize_all()


if __name__ == "__main__":
  main()