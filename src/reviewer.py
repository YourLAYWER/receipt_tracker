from categorizer import add_keyword_to_category, categorize_item, load_category_rules


def _recalculate(parsed: dict):
  parsed["calculated_total"] = round(sum(item["price"] for item in parsed["items"]), 2)
  parsed["totals_match"] = (
      parsed["receipt_total"] is not None
      and parsed["receipt_total"] == parsed["calculated_total"]
  )


def review_totals(parsed: dict) -> bool:
  """Interactive loop to fix price/item mismatches. Returns True to save, False to skip."""
  while not parsed["totals_match"]:
    print("\n--- TOTAL MISMATCH REVIEW ---")
    for idx, item in enumerate(parsed["items"], start=1):
      print(f"  {idx:>2}. {item['name']:<30} R{item['price']:>7.2f}")

    diff = (
        round(parsed["receipt_total"] - parsed["calculated_total"], 2)
        if parsed["receipt_total"] is not None
        else 0.0
    )
    print(f"\nCalculated: R{parsed['calculated_total']:.2f} | Receipt: {parsed['receipt_total']} | Diff: R{diff:.2f}")
    action = input("[e] Edit price | [a] Add item | [d] Delete item | [c] Save anyway | [s] Skip: ").strip().lower()

    if action == "c":
      return True
    elif action == "s":
      return False
    elif action == "e":
      try:
        idx = int(input("Item number to edit: ")) - 1
        new_price = float(input(f"New price for '{parsed['items'][idx]['name']}': "))
        parsed["items"][idx]["price"] = new_price
        parsed["items"][idx]["is_discount"] = new_price < 0
        _recalculate(parsed)
      except (ValueError, IndexError):
        print("Invalid selection.")
    elif action == "a":
      try:
        name = input("Item name: ").strip()
        price = float(input("Item price (use negative for discount): "))
        if name:
          parsed["items"].append({"name": name, "price": price, "is_discount": price < 0})
          _recalculate(parsed)
      except ValueError:
        print("Invalid price.")
    elif action == "d":
      try:
        idx = int(input("Item number to delete: ")) - 1
        removed = parsed["items"].pop(idx)
        print(f"Removed '{removed['name']}'.")
        _recalculate(parsed)
      except (ValueError, IndexError):
        print("Invalid selection.")

  print("Totals now match!")
  return True


def review_categories(parsed: dict):
  """Prompts the user to categorize any 'Uncategorized' items and optionally save new keywords."""
  rules = load_category_rules()
  categories = list(rules.keys())

  for item in parsed["items"]:
    cat = categorize_item(item["name"], item["is_discount"], rules=rules)
    if cat != "Uncategorized":
      item["category"] = cat
      continue

    print(f"\nUncategorized item: '{item['name']}' (R{item['price']:.2f})")
    for idx, c in enumerate(categories, start=1):
      print(f"  {idx}. {c}")

    choice = input("Choose category number (or press Enter to leave Uncategorized): ").strip()
    if not choice:
      item["category"] = "Uncategorized"
      continue

    try:
      selected_cat = categories[int(choice) - 1]
      item["category"] = selected_cat

      kw = input(f"Save a keyword to '{selected_cat}' in categories.json? (Enter keyword or skip): ").strip()
      if kw:
        add_keyword_to_category(selected_cat, kw)
        rules = load_category_rules()  # Reload so duplicate items on the same slip auto-match
        print(f"Saved '{kw.upper()}' -> {selected_cat}")
    except (ValueError, IndexError):
      print("Invalid choice. Leaving as Uncategorized.")
      item["category"] = "Uncategorized"