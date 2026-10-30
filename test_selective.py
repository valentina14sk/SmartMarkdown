
import pandas as pd
from simulator import load_products, simulate_store

products = load_products("products.csv")
seeds = range(42, 52)

results = []

for seed in seeds:
    for policy in ["fixed", "markdown", "selective"]:
        summary, daily, events = simulate_store(
            products=products,
            policy=policy,
            seed=seed,
            days=30,
            two_day_discount=0.05,
            one_day_discount=0.10,
        )

        results.append({
            "seed": seed,
            "policy": policy,
            "profit": summary["profit"],
            "waste": summary["units_wasted"],
            "revenue": summary["revenue"],
        })

df = pd.DataFrame(results)

print("\nAVERAGE RESULTS ACROSS 10 MATCHED SEEDS")
print(
    df.groupby("policy")[["profit", "waste", "revenue"]]
    .mean()
    .round(2)
    .sort_values("profit", ascending=False)
)

print("\nPROFIT-FIRST RANKING")
print(
    df.groupby("policy")["profit"]
    .mean()
    .sort_values(ascending=False)
)
