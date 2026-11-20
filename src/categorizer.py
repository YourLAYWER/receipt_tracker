CATEGORY_RULES = {
    "Dairy": ["MILK", "UHT", "AMASI", "CHEESE", "YOGHURT", "BUTTER", "CREAM", "FCHOIC"],
    "Pantry & Staples": ["WHTSTAR", "WHT STAR", "M MEAL", "PORRIDGE", "SELATI", "SUGAR", "NOODLES", "RICE", "PASTA", "FLOUR", "OIL", "PNUTB", "PEANUT"],
    "Bakery": ["BREAD", "BROWN", "WHITE", "ROLLS", "BUNS", "CAKE"],
    "Snacks & Treats": ["P/CORN", "CHIPS", "CHOC", "SWEETS", "BISCUIT", "AER", "SODA", "COKE"],
    "Household & Cleaning": ["DISHWASH", "KITCHEN", "TOILET", "SOAP", "BLEACH", "WASH", "CLEAN"],
    "Bags & Fees": ["BAG", "CARR"],
    "Meat & Poultry": ["CHICKEN", "BEEF", "MINCE", "PORK", "WORS", "SAUSAGE", "FISH"],
    "Fresh Produce": ["APPLE", "BANANA", "POTATO", "ONION", "TOMATO", "VEG", "FRUIT"],
}


def categorize_item(name: str, is_discount: bool = False) -> str:
  """Assigns a category based on receipt item keywords."""
  if is_discount:
    return "Discount"

  upper_name = name.upper()
  for category, keywords in CATEGORY_RULES.items():
    if any(kw in upper_name for kw in keywords):
      return category

  return "Uncategorized"