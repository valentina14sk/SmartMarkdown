
import pandas as pd

# Load the results from your existing optimizer.
df = pd.read_csv("policy_comparison.csv")

print("Available columns:", df.columns.tolist())

# Keep markdown policies only.
markdown = df[
    df["policy"].astype(str).str.lower().eq("markdown")
].copy()

if markdown.empty:
    raise ValueError("No markdown policies found in the CSV.")

# If results contain individual seed runs, calculate averages
# for each discount combination.
group_cols = ["two_day_discount", "one_day_discount"]

if "seed" in markdown.columns:
    summary = markdown.groupby(group_cols, as_index=False).agg(
        avg_profit=("profit", "mean"),
        avg_waste=("units_wasted", "mean"),
        avg_revenue=("revenue", "mean"),
    )
else:
    # Your existing optimizer may already have aggregated results.
    summary = markdown.copy()

# Rank profit first, then use lower waste as a tie-breaker.
summary = summary.sort_values(
    by=["avg_profit", "avg_waste"],
    ascending=[False, True],
)

print("\nTOP 10 PROFIT-FIRST MARKDOWN POLICIES")
print(
    summary.head(10).to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}",
    )
)

best = summary.iloc[0]

print("\nRECOMMENDED PROFIT-FIRST POLICY")
print(f"Discount with 2 days left: {best['two_day_discount']:.0%}")
print(f"Discount with 1 day left: {best['one_day_discount']:.0%}")
print(f"Average profit: ₹{best['avg_profit']:,.2f}")
print(f"Average waste: {best['avg_waste']:.2f} units")
