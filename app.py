
import streamlit as st
import pandas as pd
import plotly.express as px

from simulator import load_products, simulate_store


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="SmartMarkdown AI",
    page_icon="🥬",
    layout="wide",
)

st.title("🥬 SmartMarkdown AI")
st.caption(
    "Intelligent markdown pricing for perishable grocery products"
)

st.markdown(
    """
    Compare fixed pricing with expiry-aware markdowns.
    Explore the trade-off between profitability and food waste
    using a reproducible 30-day store simulation.
    """
)


# -----------------------------
# Load product catalogue
# -----------------------------
@st.cache_data
def get_products():
    return load_products("products.csv")


try:
    products = get_products()
except Exception as exc:
    st.error(f"Could not load products.csv: {exc}")
    st.stop()


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Simulation settings")

seed = st.sidebar.number_input(
    "Random seed",
    min_value=0,
    max_value=999999,
    value=42,
    step=1,
)

days = st.sidebar.slider(
    "Simulation duration (days)",
    min_value=7,
    max_value=30,
    value=30,
)

st.sidebar.subheader("Markdown rules")

two_day_discount = st.sidebar.slider(
    "Discount with 2 days remaining",
    min_value=0,
    max_value=40,
    value=5,
    step=5,
) / 100

one_day_discount = st.sidebar.slider(
    "Discount with 1 day remaining",
    min_value=0,
    max_value=60,
    value=10,
    step=5,
) / 100

if one_day_discount < two_day_discount:
    st.sidebar.warning(
        "The 1-day discount should be at least as high "
        "as the 2-day discount."
    )

discount_response = st.sidebar.slider(
    "Shopper response strength",
    min_value=0.5,
    max_value=1.5,
    value=1.0,
    step=0.25,
    help="0.5 means shoppers respond half as strongly to price changes.",
)

run_simulation = st.sidebar.button(
    "Run comparison",
    type="primary",
    use_container_width=True,
)


# -----------------------------
# Run both policies
# -----------------------------
if "results" not in st.session_state:
    st.session_state.results = None

if run_simulation:
    if one_day_discount < two_day_discount:
        st.error(
            "Increase the 1-day discount so it is at least "
            "as high as the 2-day discount."
        )
        st.stop()

    with st.spinner("Simulating both pricing policies..."):
        fixed_summary, fixed_daily, fixed_events = simulate_store(
            products=products,
            policy="fixed",
            seed=int(seed),
            days=int(days),
            discount_response=discount_response,
        )

        markdown_summary, markdown_daily, markdown_events = simulate_store(
            products=products,
            policy="markdown",
            seed=int(seed),
            days=int(days),
            two_day_discount=two_day_discount,
            one_day_discount=one_day_discount,
            discount_response=discount_response,
        )

        st.session_state.results = {
            "fixed_summary": fixed_summary,
            "fixed_daily": fixed_daily,
            "fixed_events": fixed_events,
            "markdown_summary": markdown_summary,
            "markdown_daily": markdown_daily,
            "markdown_events": markdown_events,
            "seed": int(seed),
            "days": int(days),
            "two_day_discount": two_day_discount,
            "one_day_discount": one_day_discount,
            "discount_response": discount_response,
        }


# -----------------------------
# Display results
# -----------------------------
results = st.session_state.results

if results is None:
    st.info(
        "Choose your settings in the sidebar and click "
        "**Run comparison** to start."
    )

    st.subheader("Your product catalogue")
    st.dataframe(products, use_container_width=True)

    st.subheader("How it works")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **Fixed pricing**
            
            Products retain their base price. Unsold products
            may expire and become waste.
            """
        )

    with col2:
        st.markdown(
            """
            **Smart markdown**
            
            Discounts increase as expiry approaches, aiming
            to sell more stock before it expires.
            """
        )

    st.stop()


fixed = results["fixed_summary"]
markdown = results["markdown_summary"]

fixed_daily = results["fixed_daily"].copy()
markdown_daily = results["markdown_daily"].copy()

fixed_events = results["fixed_events"].copy()
markdown_events = results["markdown_events"].copy()


# Handle common alternative metric names.
def get_metric(summary, possible_names, default=0):
    for name in possible_names:
        if name in summary:
            return summary[name]
    return default


fixed_revenue = get_metric(fixed, ["revenue", "total_revenue"])
markdown_revenue = get_metric(markdown, ["revenue", "total_revenue"])

fixed_profit = get_metric(fixed, ["profit", "total_profit"])
markdown_profit = get_metric(markdown, ["profit", "total_profit"])

fixed_waste = get_metric(
    fixed, ["units_wasted", "waste", "total_waste", "expired_units"]
)
markdown_waste = get_metric(
    markdown, ["units_wasted", "waste", "total_waste", "expired_units"]
)

fixed_margin = get_metric(
    fixed, ["margin", "profit_margin", "margin_pct"]
)
markdown_margin = get_metric(
    markdown, ["margin", "profit_margin", "margin_pct"]
)

if fixed_revenue:
    fixed_margin = fixed_profit / fixed_revenue * 100

if markdown_revenue:
    markdown_margin = markdown_profit / markdown_revenue * 100

waste_reduction = (
    (fixed_waste - markdown_waste) / fixed_waste * 100
    if fixed_waste
    else 0
)

profit_change = (
    (markdown_profit - fixed_profit) / abs(fixed_profit) * 100
    if fixed_profit
    else 0
)


st.divider()
st.subheader("Simulation overview")

st.caption(
    f"Seed: {results['seed']} · "
    f"Duration: {results['days']} days · "
    f"Products: {len(products)} · "
    f"Shopper response: {results['discount_response']:.2f}×"
)

# Key performance indicators
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Markdown profit",
    f"₹{markdown_profit:,.0f}",
    f"{profit_change:+.2f}% vs fixed",
)

c2.metric(
    "Units wasted",
    f"{markdown_waste:,.0f}",
    f"{markdown_waste - fixed_waste:+,.0f} vs fixed",
    delta_color="inverse",
)

c3.metric(
    "Waste reduction",
    f"{waste_reduction:.1f}%",
)

c4.metric(
    "Profit margin",
    f"{markdown_margin:.2f}%",
    f"{markdown_margin - fixed_margin:+.2f} percentage points",
)

st.divider()


# -----------------------------
# Policy comparison table
# -----------------------------
st.subheader("Fixed price vs. smart markdown")

comparison = pd.DataFrame(
    [
        {
            "Metric": "Revenue",
            "Fixed price": fixed_revenue,
            "Smart markdown": markdown_revenue,
        },
        {
            "Metric": "Profit",
            "Fixed price": fixed_profit,
            "Smart markdown": markdown_profit,
        },
        {
            "Metric": "Profit margin (%)",
            "Fixed price": fixed_margin,
            "Smart markdown": markdown_margin,
        },
        {
            "Metric": "Units wasted",
            "Fixed price": fixed_waste,
            "Smart markdown": markdown_waste,
        },
    ]
)

st.dataframe(
    comparison,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Fixed price": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Smart markdown": st.column_config.NumberColumn(
            format="%.2f"
        ),
    },
)

st.caption(
    "Profit and margin use the simulator's accounting definitions. "
    "Results are synthetic simulations, not measured store performance."
)


# -----------------------------
# Daily performance charts
# -----------------------------
st.divider()
st.subheader("Daily performance")

def prepare_daily(df, policy_name):
    df = df.copy()
    df["Policy"] = policy_name

    # Standardize common column names for charting.
    aliases = {
        "day": ["day", "Day"],
        "revenue": ["revenue", "daily_revenue"],
        "profit": ["profit", "daily_profit"],
        "waste": [
            "units_wasted",
            "waste",
            "expired_units",
            "daily_waste",
        ],
    }

    rename = {}
    for standard, candidates in aliases.items():
        if standard not in df.columns:
            for candidate in candidates:
                if candidate in df.columns:
                    rename[candidate] = standard
                    break

    return df.rename(columns=rename)


daily = pd.concat(
    [
        prepare_daily(fixed_daily, "Fixed price"),
        prepare_daily(markdown_daily, "Smart markdown"),
    ],
    ignore_index=True,
)

tab1, tab2, tab3 = st.tabs(
    ["Revenue", "Profit", "Food waste"]
)

with tab1:
    if {"day", "revenue"}.issubset(daily.columns):
        fig = px.line(
            daily,
            x="day",
            y="revenue",
            color="Policy",
            markers=True,
            title="Daily revenue comparison",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(
            "Revenue chart unavailable. Check the daily DataFrame "
            "column names in simulator.py."
        )

with tab2:
    if {"day", "profit"}.issubset(daily.columns):
        fig = px.line(
            daily,
            x="day",
            y="profit",
            color="Policy",
            markers=True,
            title="Daily profit comparison",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(
            "Profit chart unavailable. Check the daily DataFrame "
            "column names in simulator.py."
        )

with tab3:
    if {"day", "waste"}.issubset(daily.columns):
        fig = px.bar(
            daily,
            x="day",
            y="waste",
            color="Policy",
            barmode="group",
            title="Daily expired units",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(
            "Waste chart unavailable. Check the daily DataFrame "
            "column names in simulator.py."
        )


# -----------------------------
# Product and markdown history
# -----------------------------
st.divider()
st.subheader("Product-level event history")

st.caption(
    f"Current markdown rules: "
    f"{results['two_day_discount']:.0%} with 2 days left, "
    f"{results['one_day_discount']:.0%} with 1 day left."
)

events = pd.concat(
    [
        fixed_events.assign(Policy="Fixed price"),
        markdown_events.assign(Policy="Smart markdown"),
    ],
    ignore_index=True,
)

if not events.empty:
    if "product" in events.columns:
        product_names = sorted(
            events["product"].dropna().astype(str).unique()
        )

        selected_product = st.selectbox(
            "Choose a product",
            ["All products"] + product_names,
        )

        if selected_product != "All products":
            events = events[
                events["product"].astype(str) == selected_product
            ]

    if "Policy" in events.columns:
        selected_policy = st.radio(
            "Pricing policy",
            ["Both", "Fixed price", "Smart markdown"],
            horizontal=True,
        )

        if selected_policy != "Both":
            events = events[events["Policy"] == selected_policy]

    st.dataframe(
        events,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = events.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download event history as CSV",
        data=csv_data,
        file_name="smartmarkdown_event_history.csv",
        mime="text/csv",
    )
else:
    st.info("No events were returned for this simulation.")


# -----------------------------
# Synthetic data transparency
# -----------------------------
with st.expander("Simulation assumptions and limitations"):
    st.markdown(
        """
        - Product catalogue and demand are synthetic.
        - The store simulation runs for the selected number of days.
        - The fixed-price and markdown policies use the same random seed.
        - Markdown discounts are triggered by the expiry of the
          oldest available inventory batch.
        - Demand depends on base demand, weekday effects, freshness,
          price sensitivity, and shopper response strength.
        - Simulation outputs depend on the assumptions in
          `simulator.py`; they are not guarantees of real-world results.
        """
    )

st.caption(
    "SmartMarkdown AI · Hackathon prototype · Synthetic data"
)

# ==========================================
# SMARTMARKDOWN AI - INVENTORY MANAGEMENT
# ==========================================
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

st.divider()
st.subheader("🛒 SmartMarkdown AI — Owner Control Panel")

owner_section = st.radio(
    "Go to section",
    [
        "Overview",
        "Inventory",
        "Smart Pricing",
        "Record a Sale",
        "Sales History",
        "Expiry Risk",
    ],
    horizontal=True,
    key="owner_navigation",
)
st.header("📦 Daily Inventory Management")
st.write(
    "Upload a complete snapshot of all batches currently in stock. "
    "Each batch must have a unique Batch ID."
)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CURRENT_INVENTORY = DATA_DIR / "current_inventory.csv"
UPLOAD_HISTORY = DATA_DIR / "inventory_upload_history"

required_columns = [
    "product",
    "batch_id",
    "quantity",
    "expiry_date",
    "unit_cost",
    "base_price",
]

uploaded_file = st.file_uploader(
    "Upload today's stock CSV",
    type=["csv"],
    key="daily_inventory_upload",
)

if uploaded_file is not None:
    try:
        incoming = pd.read_csv(uploaded_file)
        incoming.columns = incoming.columns.str.strip().str.lower()

        missing = [
            col for col in required_columns
            if col not in incoming.columns
        ]

        if missing:
            st.error("Missing columns: " + ", ".join(missing))

        else:
            incoming = incoming[required_columns].copy()

            # Clean and validate values
            for col in ["product", "batch_id"]:
                incoming[col] = incoming[col].astype("string").str.strip()

            for col in ["quantity", "unit_cost", "base_price"]:
                incoming[col] = pd.to_numeric(
                    incoming[col], errors="coerce"
                )

            incoming["expiry_date"] = pd.to_datetime(
                incoming["expiry_date"], errors="coerce"
            ).dt.normalize()

            errors = []

            if incoming.empty:
                errors.append("The CSV contains no stock records.")

            if incoming[["product", "batch_id"]].isna().any().any():
                errors.append("Product and Batch ID cannot be empty.")

            if (
                incoming["product"].eq("").any()
                or incoming["batch_id"].eq("").any()
            ):
                errors.append("Product and Batch ID cannot be blank.")

            if incoming["batch_id"].duplicated().any():
                errors.append(
                    "Each Batch ID must be unique within the CSV."
                )

            if incoming["quantity"].isna().any():
                errors.append("Quantity must contain valid numbers.")
            elif (
                (incoming["quantity"] < 0).any()
                or (incoming["quantity"] % 1 != 0).any()
            ):
                errors.append(
                    "Quantity must be a non-negative whole number."
                )

            for col in ["unit_cost", "base_price"]:
                if incoming[col].isna().any() or (incoming[col] < 0).any():
                    errors.append(
                        f"{col} must contain valid non-negative numbers."
                    )

            if incoming["expiry_date"].isna().any():
                errors.append(
                    "Every batch must have a valid expiry date."
                )

            if errors:
                for error in errors:
                    st.error(error)

            else:
                today = pd.Timestamp.now().normalize()
                incoming["days_to_expiry"] = (
                    incoming["expiry_date"] - today
                ).dt.days

                st.subheader("Preview uploaded inventory")
                st.dataframe(incoming, use_container_width=True)

                st.caption(
                    "Uploading replaces the current snapshot. "
                    "It does not add quantities to the previous snapshot."
                )

                if st.button(
                    "Validate and update inventory",
                    type="primary",
                    key="save_daily_inventory",
                ):
                    # Save the previous snapshot to history first
                    if CURRENT_INVENTORY.exists():
                        old = pd.read_csv(CURRENT_INVENTORY)
                        if not old.empty:
                            UPLOAD_HISTORY.mkdir(
                                parents=True, exist_ok=True
                            )
                            stamp = datetime.now().strftime(
                                "%Y%m%d_%H%M%S"
                            )
                            old.to_csv(
                                UPLOAD_HISTORY
                                / f"inventory_{stamp}.csv",
                                index=False,
                            )

                    # Save the new complete snapshot
                    incoming.to_csv(CURRENT_INVENTORY, index=False)

                    # Archive the exact uploaded snapshot as well
                    UPLOAD_HISTORY.mkdir(parents=True, exist_ok=True)
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    incoming.to_csv(
                        UPLOAD_HISTORY / f"upload_{stamp}.csv",
                        index=False,
                    )

                    st.success(
                        f"Inventory updated successfully: "
                        f"{len(incoming)} batches saved."
                    )
                    st.rerun()

    except Exception as exc:
        st.error(f"Could not read the CSV: {exc}")

# Show the currently saved inventory
if CURRENT_INVENTORY.exists():
    st.subheader("Current saved inventory")

    saved = pd.read_csv(CURRENT_INVENTORY)
    saved["expiry_date"] = pd.to_datetime(
        saved["expiry_date"], errors="coerce"
    )

    today = pd.Timestamp.now().normalize()
    saved["days_to_expiry"] = (
        saved["expiry_date"] - today
    ).dt.days

    total_units = int(saved["quantity"].sum())
    expired_units = int(
        saved.loc[saved["days_to_expiry"] < 0, "quantity"].sum()
    )
    urgent_units = int(
        saved.loc[
            saved["days_to_expiry"].between(0, 2),
            "quantity",
        ].sum()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Batches", len(saved))
    c2.metric("Units in stock", total_units)
    c3.metric("Expired units", expired_units)

    st.metric("Units expiring within 2 days", urgent_units)

    def expiry_status(days):
        if pd.isna(days):
            return "Unknown"
        if days < 0:
            return "Expired — remove from sale"
        if days <= 1:
            return "Urgent — review now"
        if days <= 2:
            return "Consider markdown"
        return "Normal price — monitor"

    saved["status"] = saved["days_to_expiry"].apply(expiry_status)

    st.dataframe(
        saved.sort_values("days_to_expiry"),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Upload a stock CSV to start tracking batches.")


# ==========================================
# SMARTMARKDOWN AI - BATCH PRICING
# ==========================================
st.divider()
st.header("🏷️ Smart Pricing Recommendations")

if CURRENT_INVENTORY.exists():
    pricing = pd.read_csv(CURRENT_INVENTORY)

    pricing["expiry_date"] = pd.to_datetime(
        pricing["expiry_date"], errors="coerce"
    ).dt.normalize()

    today = pd.Timestamp.now().normalize()

    pricing["days_to_expiry"] = (
        pricing["expiry_date"] - today
    ).dt.days

    # Calculate stock cover for each product across all batches.
    pricing["quantity"] = pd.to_numeric(
        pricing["quantity"], errors="coerce"
    ).fillna(0)

    pricing["avg_daily_demand"] = (
        pricing["product"].map(
            products.set_index("product")["avg_daily_demand"]
        )
        if "products" in globals()
        and {"product", "avg_daily_demand"}.issubset(products.columns)
        else 0
    )

    pricing["product_stock"] = pricing.groupby("product")[
        "quantity"
    ].transform("sum")

    pricing["stock_cover"] = pricing.apply(
        lambda row: (
            row["product_stock"] / max(row["avg_daily_demand"], 1)
        ),
        axis=1,
    )

    # Selective markdown rules based on expiry and stock cover.
    def selective_discount(row):
        days = row["days_to_expiry"]
        cover = row["stock_cover"]

        if pd.isna(days) or days < 0:
            return 0.0
        if days <= 1 and cover >= 1:
            return 0.10
        if days <= 2 and cover >= 2:
            return 0.05
        return 0.0

    pricing["recommended_discount"] = pricing.apply(
        selective_discount, axis=1
    )

    pricing["recommended_price"] = (
        pricing["base_price"] * (1 - pricing["recommended_discount"])
    ).round(2)

    def recommendation(row):
        if row["days_to_expiry"] < 0:
            return "Expired — remove from sale"
        if row["days_to_expiry"] <= 1 and row["recommended_discount"] > 0:
            return "Urgent — prioritize sale"
        if row["recommended_discount"] > 0:
            return "Markdown recommended"
        return "Normal price"

    pricing["recommendation"] = pricing.apply(
        recommendation, axis=1
    )

    st.caption(
        "Recommendations use expiry risk and total product stock cover. "
        "These are proposed prices; they are not applied to a POS system."
    )

    st.dataframe(
        pricing[
            [
                "product",
                "batch_id",
                "quantity",
                "days_to_expiry",
                "stock_cover",
                "base_price",
                "recommended_discount",
                "recommended_price",
                "recommendation",
            ]
        ].sort_values("days_to_expiry"),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download pricing recommendations",
        data=pricing.to_csv(index=False).encode("utf-8"),
        file_name="smartmarkdown_recommendations.csv",
        mime="text/csv",
    )
else:
    st.info("Upload inventory first to generate pricing recommendations.")
    

# ==========================================
# STOCK SALES TRACKER
# ==========================================
st.divider()
st.header("🧾 Record a Sale")

if CURRENT_INVENTORY.exists():
    stock = pd.read_csv(CURRENT_INVENTORY)

    if not stock.empty:
        stock["quantity"] = pd.to_numeric(
            stock["quantity"], errors="coerce"
        ).fillna(0).astype(int)

        batch_options = {
            f"{row['product']} | Batch {row['batch_id']} | "
            f"{row['quantity']} units": str(row["batch_id"])
            for _, row in stock.iterrows()
            if row["quantity"] > 0
        }

        if batch_options:
            selected_label = st.selectbox(
                "Select the batch sold",
                list(batch_options.keys()),
            )
            selected_batch = batch_options[selected_label]

            available = int(
                stock.loc[
                    stock["batch_id"].astype(str) == selected_batch,
                    "quantity",
                ].iloc[0]
            )

            sold_quantity = st.number_input(
                "Quantity sold",
                min_value=1,
                max_value=available,
                value=1,
                step=1,
            )

            
            if st.button("Confirm sale", type="primary"):
                sales_file = DATA_DIR / "sales_history.csv"

                # Load current stock and identify the selected batch
                batch_mask = (
                    stock["batch_id"].astype(str) == selected_batch
                )
                batch_row = stock.loc[batch_mask].iloc[0]

                # Do not sell expired products
                expiry = pd.to_datetime(
                    batch_row["expiry_date"], errors="coerce"
                )
                today = pd.Timestamp.now().normalize()

                if pd.isna(expiry) or expiry.normalize() < today:
                    st.error(
                        "This batch is expired or has an invalid expiry date. "
                        "Do not sell it."
                    )
                else:
                    quantity_sold = int(sold_quantity)
                    unit_cost = float(batch_row["unit_cost"])
                    base_price = float(batch_row["base_price"])

                    # Apply the current batch markdown recommendation
                    days_left = (expiry.normalize() - today).days

                    if days_left <= 1:
                        discount = 0.10
                    elif days_left <= 2:
                        discount = 0.05
                    else:
                        discount = 0.0

                    unit_price = round(base_price * (1 - discount), 2)
                    revenue = round(unit_price * quantity_sold, 2)
                    profit = round(
                        (unit_price - unit_cost) * quantity_sold, 2
                    )

                    # Update inventory
                    stock.loc[batch_mask, "quantity"] -= quantity_sold
                    stock.to_csv(CURRENT_INVENTORY, index=False)

                    # Record transaction
                    transaction = pd.DataFrame([{
                        "date": datetime.now().isoformat(timespec="seconds"),
                        "product": batch_row["product"],
                        "batch_id": selected_batch,
                        "quantity": quantity_sold,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "revenue": revenue,
                        "profit": profit,
                    }])

                    if sales_file.exists():
                        old_sales = pd.read_csv(sales_file)
                        sales = pd.concat(
                            [old_sales, transaction], ignore_index=True
                        )
                    else:
                        sales = transaction

                    sales.to_csv(sales_file, index=False)

                    st.success(
                        f"Sale recorded: {quantity_sold} units at "
                        f"₹{unit_price:.2f} each. "
                        f"Revenue: ₹{revenue:.2f}; "
                        f"estimated profit: ₹{profit:.2f}."
                    )
                    st.rerun()

        else:
            st.info("There is no stock available to sell.")
else:
    st.info("Upload inventory before recording sales.")
    

# ==========================================
# SALES HISTORY AND PROFIT TRACKING
# ==========================================
st.divider()
st.header("📊 Sales History & Profit")

SALES_HISTORY = DATA_DIR / "sales_history.csv"

if SALES_HISTORY.exists():
    sales = pd.read_csv(SALES_HISTORY)
else:
    sales = pd.DataFrame(
        columns=[
            "date", "product", "batch_id", "quantity",
            "unit_price", "unit_cost", "revenue", "profit"
        ]
    )

if not sales.empty:
    sales["revenue"] = pd.to_numeric(sales["revenue"], errors="coerce").fillna(0)
    sales["profit"] = pd.to_numeric(sales["profit"], errors="coerce").fillna(0)

    col1, col2, col3 = st.columns(3)
    col1.metric("Recorded revenue", f"₹{sales['revenue'].sum():,.2f}")
    col2.metric("Recorded profit", f"₹{sales['profit'].sum():,.2f}")
    col3.metric("Units sold", int(sales["quantity"].sum()))

    st.dataframe(sales, use_container_width=True, hide_index=True)

    st.download_button(
        "Download sales history",
        data=sales.to_csv(index=False).encode("utf-8"),
        file_name="sales_history.csv",
        mime="text/csv",
    )
else:
    st.info(
        "No sales history recorded yet. "
        "Next, we will connect the sale confirmation button to this history."
    )

# ==========================================
# EXPIRY RISK OVERVIEW
# ==========================================
st.divider()
st.header("⚠️ Expiry Risk Overview")

if CURRENT_INVENTORY.exists():
    risk = pd.read_csv(CURRENT_INVENTORY)

    risk["expiry_date"] = pd.to_datetime(
        risk["expiry_date"], errors="coerce"
    ).dt.normalize()
    risk["quantity"] = pd.to_numeric(
        risk["quantity"], errors="coerce"
    ).fillna(0)

    today = pd.Timestamp.now().normalize()
    risk["days_to_expiry"] = (
        risk["expiry_date"] - today
    ).dt.days

    # Exclude zero-stock batches from active inventory risk
    active = risk[risk["quantity"] > 0].copy()

    expired = active[active["days_to_expiry"] < 0]
    urgent = active[active["days_to_expiry"].between(0, 1)]
    soon = active[active["days_to_expiry"].between(2, 3)]
    fresh = active[active["days_to_expiry"] > 3]

    a, b, c, d = st.columns(4)
    a.metric("Expired units", int(expired["quantity"].sum()))
    b.metric("Urgent units (0–1 days)", int(urgent["quantity"].sum()))
    c.metric("Expiring soon (2–3 days)", int(soon["quantity"].sum()))
    d.metric("More than 3 days", int(fresh["quantity"].sum()))

    st.subheader("Priority batches")

    priority = active[active["days_to_expiry"] <= 3].copy()

    if priority.empty:
        st.success("No active batches need urgent expiry attention.")
    else:
        priority["risk_status"] = priority["days_to_expiry"].apply(
            lambda days: (
                "Expired — remove from sale" if days < 0
                else "Urgent — review today" if days <= 1
                else "Markdown review" if days <= 3
                else "Normal"
            )
        )

        st.dataframe(
            priority[
                [
                    "product",
                    "batch_id",
                    "quantity",
                    "expiry_date",
                    "days_to_expiry",
                    "risk_status",
                ]
            ].sort_values("days_to_expiry"),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download priority batches",
            data=priority.to_csv(index=False).encode("utf-8"),
            file_name="expiry_risk_report.csv",
            mime="text/csv",
        )
else:
    st.info("Upload inventory to see expiry risks.")

