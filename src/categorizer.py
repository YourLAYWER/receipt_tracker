import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "categories.json")


def load_category_rules() -> dict[str, list[str]]:
  """Loads category keyword rules from config/categories.json."""
  if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Category config not found at {CONFIG_PATH}")

  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    return json.load(f)


def add_keyword_to_category(category: str, keyword: str):
  """Adds a new keyword to a category and saves it back to categories.json."""
  rules = load_category_rules()
  kw = keyword.strip().upper()

  if category not in rules:
    rules[category] = []

  if kw and kw not in rules[category]:
    rules[category].append(kw)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
      json.dump(rules, f, indent=2)


def categorize_item(name: str, is_discount: bool = False, rules: dict | None = None) -> str:
  """Assigns a category based on receipt item keywords."""
  if is_discount:
    return "Discount"

  if rules is None:
    rules = load_category_rules()

  upper_name = name.upper()
  for category, keywords in rules.items():
    if any(kw in upper_name for kw in keywords):
      return category

  return "Uncategorized"