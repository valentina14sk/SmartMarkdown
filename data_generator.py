
import pandas as pd

PRODUCTS = [
    # name, category, shelf life, unit cost, base price,
    # average daily demand, price sensitivity
    ("Milk", "Dairy", 7, 32, 48, 12, 1.8),
    ("Yogurt", "Dairy", 10, 18, 30, 8, 1.5),
    ("Cheese", "Dairy", 14, 55, 80, 4, 1.2),
    ("Butter", "Dairy", 14, 40, 60, 3, 1.0),
    ("Cream", "Dairy", 5, 25, 38, 5, 1.7),
    ("White Bread", "Bakery", 4, 18, 30, 14, 2.0),
    ("Brown Bread", "Bakery", 5, 22, 36, 8, 1.8),
    ("Croissant", "Bakery", 2, 20, 35, 6, 2.2),
    ("Muffin", "Bakery", 3, 15, 28, 7, 2.0),
    ("Bagel", "Bakery", 4, 16, 27, 5, 1.6),
    ("Tomato", "Produce", 5, 12, 22, 15, 1.5),
    ("Spinach", "Produce", 3, 10, 20, 8, 2.0),
    ("Lettuce", "Produce", 5, 14, 25, 7, 1.6),
    ("Banana", "Produce", 6, 20, 32, 12, 1.3),
    ("Strawberry", "Produce", 3, 28, 45, 6, 2.1),
    ("Sandwich", "Ready-to-eat", 2, 35, 55, 6, 2.3),
    ("Fresh Salad", "Ready-to-eat", 2, 30, 50, 5, 2.2),
    ("Fresh Juice", "Ready-to-eat", 5, 22, 38, 7, 1.7),
    ("Cut Fruit", "Ready-to-eat", 2, 25, 42, 5, 2.2),
    ("Pasta Meal", "Ready-to-eat", 4, 32, 52, 4, 1.8),
]

columns = [
    "product", "category", "shelf_life_days",
    "unit_cost", "base_price",
    "avg_daily_demand", "price_sensitivity"
]

df = pd.DataFrame(PRODUCTS, columns=columns)

assert len(df) == 20
assert (df["base_price"] > df["unit_cost"]).all()
assert (df["shelf_life_days"] > 0).all()

df.to_csv("products.csv", index=False)

print("Product catalogue created!")
print(f"Products: {len(df)}")
print("\nCategory counts:")
print(df["category"].value_counts())
print("\nPreview:")
print(df.head())
