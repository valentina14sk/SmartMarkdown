
from collections import deque

import numpy as np
import pandas as pd


def load_products(path="products.csv"):
    products = pd.read_csv(path)
    required = {
        "product", "category", "shelf_life_days",
        "unit_cost", "base_price",
        "avg_daily_demand", "price_sensitivity"
    }
    missing = required - set(products.columns)
    if missing:
        raise ValueError(f"Missing product columns: {sorted(missing)}")
    return products


def markdown_discount(days_left, two_day_discount=0.20,
                      one_day_discount=0.40):
    """Return the discount based on the earliest-expiring stock."""
    if days_left <= 1:
        return one_day_discount
    if days_left <= 2:
        return two_day_discount
    return 0.0


def simulate_store(
    products,
    policy="fixed",
    seed=42,
    days=30,
    two_day_discount=0.20,
    one_day_discount=0.40,
    discount_response=1.0,
):
    """
    Simulate one store.

    Each batch contains:
      quantity, arrival_day, expiry_day

    Expiry convention:
      A batch arriving on day 0 with shelf life 2 can sell on
      days 0 and 1. It expires before sales on day 2.
    """
    if policy not in {"fixed", "markdown", "selective"}:
      raise ValueError(
        "policy must be 'fixed', 'markdown', or 'selective'"
    )

    if not 0 <= two_day_discount <= 0.8:
        raise ValueError("two_day_discount must be between 0 and 0.8")
    if not 0 <= one_day_discount <= 0.8:
        raise ValueError("one_day_discount must be between 0 and 0.8")
    if discount_response < 0:
        raise ValueError("discount_response cannot be negative")

    # Separate random streams keep arrivals and baseline demand
    # identical when comparing policies with the same seed.
    arrival_rng = np.random.default_rng(seed + 100_003)
    demand_rng = np.random.default_rng(seed)

    # Generate baseline demand for every product and day in advance.
    # This keeps random demand scenarios aligned across policies.
    baseline_demands = np.zeros((len(products), days), dtype=int)

    for i, row in products.iterrows():
        for day in range(days):
            weekday_factor = 1.15 if day % 7 in (5, 6) else 1.0
            mean_demand = row["avg_daily_demand"] * weekday_factor

            baseline_demands[i, day] = demand_rng.poisson(mean_demand)

    inventory = {i: deque() for i in range(len(products))}
    daily_records = []
    event_records = []

    total_revenue = 0.0
    sold_cost = 0.0
    expired_cost = 0.0
    units_sold = 0
    units_wasted = 0
    units_received = 0
    units_marked_down = 0

    for day in range(days):
        day_revenue = 0.0
        day_sold = 0
        day_wasted = 0
        day_marked_down = 0

        for i, row in products.iterrows():
            batches = inventory[i]

            # 1. Remove stock that expired before today's sales.
            while batches and batches[0]["expiry_day"] <= day:
                batch = batches.popleft()
                wasted = batch["quantity"]
                day_wasted += wasted
                units_wasted += wasted
                expired_cost += wasted * row["unit_cost"]

                event_records.append({
                    "day": day,
                    "product": row["product"],
                    "event": "expired",
                    "quantity": wasted,
                    "discount_pct": 0.0,
                    "unit_price": 0.0,
                })

            # 2. Receive a new batch every two days.
            if day % 2 == 0:
                quantity = max(
                    1,
                    int(round(
                        arrival_rng.normal(
                            row["avg_daily_demand"] * 2,
                            max(1, row["avg_daily_demand"] * 0.2),
                        )
                    )),
                )

                batches.append({
                    "quantity": quantity,
                    "arrival_day": day,
                    "expiry_day": day + int(row["shelf_life_days"]),
                })
                units_received += quantity

                event_records.append({
                    "day": day,
                    "product": row["product"],
                    "event": "arrival",
                    "quantity": quantity,
                    "discount_pct": 0.0,
                    "unit_price": row["base_price"],
                })

            if not batches:
                continue

            # 3. Determine the expiry risk from the oldest batch.
            days_left = min(b["expiry_day"] for b in batches) - day

            discount = 0.0

            if policy == "markdown":
                discount = markdown_discount(
                    days_left,
                    two_day_discount,
                    one_day_discount,
                )
            elif policy == "selective":
                stock_quantity = sum(
                    batch["quantity"] for batch in batches
                )
                expected_daily_demand = max(
                    1, row["avg_daily_demand"]
                )
                stock_cover = stock_quantity / expected_daily_demand

                if days_left <= 1 and stock_cover >= 1.0:
                    discount = min(one_day_discount, 0.10)
                elif days_left <= 2 and stock_cover >= 2.0:
                    discount = min(two_day_discount, 0.05)


            price = row["base_price"] * (1 - discount)

            # 4. Generate common baseline demand. This same random
            # baseline is used by both policies for the same seed.
            freshness_factor = 0.90 if days_left <= 1 else (
                0.97 if days_left == 2 else 1.0
            )
            baseline_demand = int(baseline_demands[i, day])
            baseline_demand = int(round(
                baseline_demand * freshness_factor
            ))

            # Price elasticity: lowering price increases expected
            # demand. Sensitivity is a synthetic assumption.
            price_ratio = price / row["base_price"]
            price_factor = price_ratio ** (
                -row["price_sensitivity"] * discount_response
            )
            demand = int(round(baseline_demand * price_factor))

            # 5. Sell earliest-expiring batches first (FEFO).
            remaining_demand = demand
            sold_today = 0

            while batches and remaining_demand > 0:
                batch = batches[0]
                sold = min(batch["quantity"], remaining_demand)

                batch["quantity"] -= sold
                remaining_demand -= sold
                sold_today += sold

                if batch["quantity"] == 0:
                    batches.popleft()

            revenue = sold_today * price
            cost_of_sold = sold_today * row["unit_cost"]

            total_revenue += revenue
            sold_cost += cost_of_sold
            units_sold += sold_today
            day_revenue += revenue
            day_sold += sold_today

            if discount > 0 and sold_today > 0:
                day_marked_down += sold_today
                units_marked_down += sold_today

            event_records.append({
                "day": day,
                "product": row["product"],
                "event": "sale",
                "quantity": sold_today,
                "discount_pct": round(discount * 100, 1),
                "unit_price": round(price, 2),
            })

        # 6. Daily snapshot.
        daily_records.append({
            "day": day + 1,
            "revenue": round(day_revenue, 2),
            "units_sold": day_sold,
            "units_wasted": day_wasted,
            "units_marked_down": day_marked_down,
        })

    # Count stock that expires after the simulation horizon as
    # remaining inventory, not as already-wasted stock.
    ending_stock = sum(
        batch["quantity"]
        for batches in inventory.values()
        for batch in batches
    )

    # Gross profit includes the purchase cost of sold units and
    # expired units. Remaining stock is not treated as waste yet.
    profit = total_revenue - sold_cost - expired_cost
    margin_pct = (
        100 * profit / total_revenue if total_revenue > 0 else 0.0
    )

    summary = {
        "policy": policy,
        "seed": seed,
        "days": days,
        "units_received": units_received,
        "units_sold": units_sold,
        "units_wasted": units_wasted,
        "ending_stock": ending_stock,
        "units_marked_down": units_marked_down,
        "revenue": round(total_revenue, 2),
        "cost_of_sold_goods": round(sold_cost, 2),
        "cost_of_expired_goods": round(expired_cost, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin_pct, 2),
    }

    return (
        summary,
        pd.DataFrame(daily_records),
        pd.DataFrame(event_records),
    )




if __name__ == "__main__":
    products = load_products()
    seeds = range(42, 52)  # 10 reproducible seeds

    results = []

    # Fixed-price baseline across all seeds
    for seed in seeds:
        summary, _, _ = simulate_store(
            products, policy="fixed", seed=seed
        )
        results.append({
            **summary,
            "policy": "Fixed price",
            "two_day_discount": 0.0,
            "one_day_discount": 0.0,
        })

    # Search candidate markdown policies
    for two_day in [0.05, 0.10, 0.15, 0.20]:
        for one_day in [0.10, 0.20, 0.30, 0.40, 0.50]:
            if one_day < two_day:
                continue

            for seed in seeds:
                summary, _, _ = simulate_store(
                    products,
                    policy="markdown",
                    seed=seed,
                    two_day_discount=two_day,
                    one_day_discount=one_day,
                )

                results.append({
                    **summary,
                    "policy": "Markdown",
                    "two_day_discount": two_day,
                    "one_day_discount": one_day,
                })

    df = pd.DataFrame(results)

    # Average performance across seeds for each policy
    comparison = (
        df.groupby(
            ["policy", "two_day_discount", "one_day_discount"],
            as_index=False,
        )
        .agg(
            avg_profit=("profit", "mean"),
            avg_waste=("units_wasted", "mean"),
            avg_revenue=("revenue", "mean"),
            avg_margin=("margin_pct", "mean"),
        )
    )

    baseline = comparison[comparison["policy"] == "Fixed price"].iloc[0]

    comparison["waste_reduction_pct"] = (
        100 * (baseline["avg_waste"] - comparison["avg_waste"])
        / baseline["avg_waste"]
        if baseline["avg_waste"] > 0
        else 0.0
    )

    comparison["profit_change_pct"] = (
        100 * (comparison["avg_profit"] - baseline["avg_profit"])
        / baseline["avg_profit"]
    )

    comparison.to_csv("policy_comparison.csv", index=False)

    print("\nFIXED-PRICE BASELINE (10 SEEDS)")
    print(f"Average profit: ₹{baseline['avg_profit']:,.2f}")
    print(f"Average waste: {baseline['avg_waste']:.1f} units")

    markdown = comparison[comparison["policy"] == "Markdown"].copy()

    print("\nTOP POLICIES THAT REDUCE WASTE")
    eligible = markdown[markdown["avg_waste"] < baseline["avg_waste"]]

    print(
        eligible.sort_values("avg_profit", ascending=False)
        .head(10)
        .round(2)
        .to_string(index=False)
    )

    print("\nLOWEST-WASTE POLICIES")
    print(
        markdown.sort_values(["avg_waste", "avg_profit"],
                             ascending=[True, False])
        .head(5)
        .round(2)
        .to_string(index=False)
    )

    print("\nSaved all results to policy_comparison.csv")
