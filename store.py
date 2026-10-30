
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="FreshMart | SmartMarkdown AI",
    page_icon="🛒",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent

# Load the product catalogue
products = pd.read_csv(BASE_DIR / "products.csv")

st.markdown("""
<style>
.stApp {
    background-color: #f7f9f5;
}
.hero {
    background: linear-gradient(120deg, #123c2b, #28734c);
    padding: 35px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
}
.hero h1 {
    color: white;
    font-size: 42px;
}
.product-card {
    background: white;
    border: 1px solid #e4e9e2;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 10px;
}
.price {
    color: #176b3a;
    font-size: 25px;
    font-weight: bold;
}
.old-price {
    color: #777;
    text-decoration: line-through;
}
.deal {
    color: #b42318;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# Session state for shopping cart
if "cart" not in st.session_state:
    st.session_state.cart = {}

st.markdown("""
<div class="hero">
    <h1>🛒 FreshMart</h1>
    <h3>Fresh groceries. Smarter prices.</h3>
    <p>Discover fresh essentials and save more with AI-powered markdown deals.</p>
</div>
""", unsafe_allow_html=True)

# Navigation
page = st.radio(
    "Navigate",
    ["Shop", "My Cart", "About SmartMarkdown"],
    horizontal=True
)

# Prepare prices and illustrative expiry-aware discounts.
# These discounts are a storefront demonstration, not live inventory data.
products = products.copy()
products["display_price"] = products["base_price"]
products["discount"] = 0.0

st.sidebar.header("Find groceries")

search = st.sidebar.text_input("Search products")
categories = ["All"] + sorted(products["category"].dropna().unique().tolist())
category = st.sidebar.selectbox("Category", categories)

deal_only = st.sidebar.checkbox("Show SmartMarkdown deals only")

# Demonstration markdown rules:
# 5% for the simulated two-day window; 10% for one day or less.
# Actual expiry dates will be connected in a later step.
products["discount"] = 0.0
products.loc[products["shelf_life_days"] <= 2, "discount"] = 0.05
products.loc[products["shelf_life_days"] <= 1, "discount"] = 0.10
products["display_price"] = (
    products["base_price"] * (1 - products["discount"])
).round(2)

filtered = products.copy()

if search:
    filtered = filtered[
        filtered["product"].str.contains(search, case=False, na=False)
    ]

if category != "All":
    filtered = filtered[filtered["category"] == category]

if deal_only:
    filtered = filtered[filtered["discount"] > 0]

if page == "Shop":
    st.subheader("Explore our groceries")
    st.caption(f"{len(filtered)} products found")

    if filtered.empty:
        st.info("No products match your search. Try another category or keyword.")

    columns = st.columns(3)

    for index, (_, product) in enumerate(filtered.iterrows()):
        with columns[index % 3]:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)

            st.subheader(str(product["product"]))
            st.caption(str(product["category"]).title())

            if product["discount"] > 0:
                st.markdown(
                    f'<span class="deal">{product["discount"]:.0%} OFF</span>',
                    unsafe_allow_html=True
                )

            st.markdown(
                f'<span class="price">₹{product["display_price"]:.2f}</span>',
                unsafe_allow_html=True
            )

            if product["discount"] > 0:
                st.markdown(
                    f'<span class="old-price">₹{product["base_price"]:.2f}</span>',
                    unsafe_allow_html=True
                )

            st.caption(
                f"Shelf life: {int(product['shelf_life_days'])} days"
            )

            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=20,
                value=1,
                step=1,
                key=f"qty_{product['product']}"
            )

            if st.button(
                "Add to cart",
                key=f"add_{product['product']}",
                use_container_width=True
            ):
                name = str(product["product"])
                current = st.session_state.cart.get(name, {
                    "quantity": 0,
                    "price": float(product["display_price"])
                })
                current["quantity"] += int(quantity)
                current["price"] = float(product["display_price"])
                st.session_state.cart[name] = current
                st.success(f"{name} added to cart!")

            st.markdown("</div>", unsafe_allow_html=True)

elif page == "My Cart":
    st.subheader("🛍️ Your shopping cart")

    if not st.session_state.cart:
        st.info("Your cart is empty. Visit Shop to add products.")
    else:
        total = 0.0

        for name, item in list(st.session_state.cart.items()):
            row = st.columns([3, 1, 1, 1])

            row[0].write(name)
            row[1].write(f"₹{item['price']:.2f}")
            row[2].write(f"Qty: {item['quantity']}")

            line_total = item["price"] * item["quantity"]
            total += line_total

            if row[3].button("Remove", key=f"remove_{name}"):
                del st.session_state.cart[name]
                st.rerun()

        st.divider()
        st.subheader(f"Cart total: ₹{total:.2f}")

        if st.button("Place demo order", type="primary"):
            st.success(
                "Demo order placed! No payment was collected."
            )
            st.session_state.cart = {}
            st.rerun()

        if st.button("Clear cart"):
            st.session_state.cart = {}
            st.rerun()

elif page == "About SmartMarkdown":
    st.subheader("About SmartMarkdown AI")
    st.write(
        "SmartMarkdown AI is a grocery retail demonstration that explores "
        "how price markdowns can help sell perishable products before expiry."
    )
    st.write("The catalogue uses synthetic product data.")
    st.warning(
        "Current deals are illustrative, based on shelf-life settings. "
        "They do not represent live stock quantities or actual expiry dates."
    )
