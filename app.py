import os, json, streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime

# ─── PAGE CONFIG & FONT ──────────────────────────────────────
st.set_page_config(
    page_title="Bam.Bot - Bamba Tracker",
    layout="wide",
    page_icon="bamlogo.png"
)

# ─── CUSTOM CSS FOR BETTER STYLING ────────────────────────────
st.markdown("""
  <style>
    /* Base font for everything */
    * { font-family: 'Calibri', sans-serif !important; }
    
    /* Container styling for subscription box */
    .subscription-container {
        background-color: #f7f7f7;
        border-radius: 10px;
        padding: 20px;
        margin: 20px auto;
        max-width: 600px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Status container styling */
    .status-container {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        margin: 20px 0;
    }
    
    /* Product card styling */
    .product-card {
        background-color: #f5be60;
        border-radius: 8px;
        padding: 10px;
        margin: 10px 0;
        border-left: 4px solid #ffffff;
    }
    
    .product-unavailable {
        border-left: 4px solid #f44336;
    }
    
    /* Form controls styling */
    .stButton > button {
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 5px !important;
        font-weight: bold !important;
    }
    
    .stTextInput > div > div > input {
        border-radius: 5px !important;
    }
    
    /* Prevent the infinite scrolling issue */
    footer {
        visibility: hidden;
    }
    
    /* Fix for main content area */
    .main .block-container {
        padding-bottom: 1rem;
        max-width: 1200px;
        margin: 0 auto;
    }
  </style>
""", unsafe_allow_html=True)

# ─── FERNET SETUP ────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY", "")
if not FERNET_KEY:
    st.error("⚠️ FERNET_KEY not set"); st.stop()
f = Fernet(FERNET_KEY.encode())

# ─── ONE IMAGE AT TOP ────────────────────────────────────────
st.markdown("""
<div style='text-align: center; margin-bottom: 30px;'>
  <img src='https://raw.githubusercontent.com/DrChenMor/bam.bot/main/bamlogo.png' width='300'/>
</div>
""", unsafe_allow_html=True)

# ─── TWO‑COLUMN BILINGUAL HEADER ────────────────────────────
col_en, col_he = st.columns(2)

with col_en:
    st.markdown("<h2>🥜 Bam.Bot WA Availability Tracker Signup</h2>", unsafe_allow_html=True)
    st.markdown("""
    **Immediate** – Email the second Bamba pops up in Coles Dianella or Mirrabooka.  
    **Daily summary** – One friendly recap at 15:00 AWST.  

    🔐 We keep your address **encrypted**— only our bot can read it.
    """)

with col_he:
    st.markdown("<h2 dir='rtl'>🥜 הרשמה למעקב במבה – במבוט WA</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div dir="rtl">
        <p><b>במיידי</b> – שלח דחוף אימייל ברגע שאתה מזהה שיש במבה בסניף דיאנלה או מיררבוקה למה אני זקוק למנת בוטנים.</p>
        <p><b>סיכום יומי</b> – סיכום פעם ביום שנייה לפני שאוספים את הילדים ב–15:00.</p>
        <p> 🔐 האימייל שלך <b>מוצפן</b> – הגנה מפני אנטישמיים מובטחת, אלא אם הבוט שלנו יתאסלם.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── SUBSCRIPTION FORM ───────────────────────────────────────

# Create columns to center the form elements
col1, col2, col3 = st.columns([1, 3, 1])
st.subheader("Subscribe for Bamba Alerts")

with col2:
    mode = st.radio(
        "Notify me when / הודיעו לי כאשר:",
        ["Immediate / במיידי", "Daily summary / סיכום פעם ביום"]
    )
    
    email = st.text_input("Your email / כתובת המייל שלך")
    
    if st.button("Subscribe", use_container_width=True):
        if not email or "@" not in email:
            st.error("Please enter a valid email address")
        else:
            try:
                token = f.encrypt(email.encode()).decode()
                subfile = "subscribers.json"
                data = json.load(open(subfile)) if os.path.exists(subfile) else {"users":[]}
                
                # Check if email already exists
                existing_emails = []
                for user in data["users"]:
                    try:
                        decrypted_email = f.decrypt(user["token"].encode()).decode()
                        existing_emails.append(decrypted_email)
                    except:
                        pass
                        
                if email in existing_emails:
                    st.warning("This email is already subscribed! No need to sign up again.")
                else:
                    data["users"].append({
                        "token": token,
                        "mode":  "immediate" if mode.startswith("Immediate") else "daily",
                        "date_added": datetime.now().isoformat()
                    })
                    with open(subfile,"w") as fp:
                        json.dump(data, fp, indent=2)
                    st.success("🎉 You're signed up! Check your inbox soon.")
            except Exception as e:
                st.error(f"Subscription error: {str(e)}")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ─── IMPROVED LATEST STATUS ─────────────────────────────────
st.markdown('<div class="status-container">', unsafe_allow_html=True)
st.subheader("🔍 Current Bamba Status")

try:
    # Refresh the data on each page load to ensure we have the latest
    hist = json.load(open("history.json"))["runs"]
    latest = hist[-1]
    
    # Format timestamp for better readability
    ts = latest[0]["timestamp"].replace("T", " ").split(".")[0]
    st.write(f"### Last checked at {ts} AWST")
    
    # Create columns for stores
    columns = st.columns(len(latest))
    
    for i, store_data in enumerate(latest):
        with columns[i]:
            # Store header with availability indicator
            store_avail = "✅" if store_data["available"] else "❌"
            st.write(f"### {store_avail} {store_data['store']}")
            
            if not store_data["products"]:
                st.write("No products found at this store")
                continue
                
            # Display each product as a card
            for product in store_data["products"]:
                # Extract size from product name if available (e.g., "25g" from "Osem Bamba Peanut Snack KB | 25g")
                size = "Unknown size"
                if "|" in product["name"]:
                    size_part = product["name"].split("|")[1].strip()
                    size = size_part
                
                # Split product name for cleaner display
                product_name = product["name"].split("|")[0].strip() if "|" in product["name"] else product["name"]
                
                # Style based on availability
                availability_class = "" if product["available"] else "product-unavailable"
                mark = "✅" if product["available"] else "❌"
                
                st.markdown(f"""
                <div class="product-card {availability_class}">
                    <div><strong>{mark} {product_name}</strong></div>
                    <div><b>Size:</b> {size}</div>
                    <div><b>Price:</b> {product["price"]}</div>
                    <div><b>Status:</b> {"Available now" if product["available"] else "Currently unavailable"}</div>
                </div>
                """, unsafe_allow_html=True)
except Exception as e:
    st.info("No checks have run yet or error loading data.")
    st.error(f"Debug info: {str(e)}")
st.markdown('</div>', unsafe_allow_html=True)

# ─── AVAILABILITY HISTORY CHART ─────────────────────────────
st.subheader("Availability History")
try:
    hist = json.load(open("history.json"))["runs"]
    if len(hist) > 1:  # Only show if we have multiple data points
        # Convert data for charting
        chart_data = []
        for i, run in enumerate(hist):
            # Get timestamp in readable format
            ts = run[0]["timestamp"].replace("T", " ").split(".")[0]
            
            # For each store in this run
            for store_data in run:
                # Count available products
                available_count = sum(1 for p in store_data["products"] if p["available"])
                
                chart_data.append({
                    "run": i,
                    "time": ts,
                    "store": store_data["store"],
                    "available_products": available_count,
                    "total_products": len(store_data["products"])
                })
        
        # Display as a table with better formatting
        st.write("### Check History Data")
        
        # Create a cleaner dataframe view
        import pandas as pd
        df = pd.DataFrame(chart_data)
        # Format the time column
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M')
        
        # Add availability percentage
        if 'available_products' in df.columns and 'total_products' in df.columns:
            df['availability'] = (df['available_products'] / df['total_products'] * 100).round(0).astype(int).astype(str) + '%'
        
        # Select and rename columns for display
        display_df = df[['time', 'store', 'available_products', 'total_products', 'availability']].rename(
            columns={
                'time': 'Time',
                'store': 'Store',
                'available_products': 'In Stock',
                'total_products': 'Total Products', 
                'availability': 'Availability %'
            }
        )
        
        st.dataframe(display_df, use_container_width=True)
        
        # Create a visual chart
        st.write("### Availability Trend")
        
        try:
            # Use Altair for nicer charts
            import altair as alt
            
            # Group by time and store to get availability over time
            pivot_df = pd.pivot_table(
                df,
                index='time',
                columns='store',
                values='available_products',
                aggfunc='sum'
            ).reset_index()
            
            # Melt for charting
            chart_data = pd.melt(
                pivot_df, 
                id_vars=['time'], 
                var_name='Store', 
                value_name='Available Products'
            )
            
            # Create the chart
            chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('time:N', title='Time'),
                y=alt.Y('Available Products:Q', title='Products Available'),
                color=alt.Color('Store:N', title='Store'),
                tooltip=['time', 'Store', 'Available Products']
            ).properties(
                width=600,
                height=300,
                title='Bamba Availability Trend'
            )
            
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            # Fallback to basic chart if Altair fails
            st.line_chart(pivot_df.set_index('time'))
            st.error(f"Advanced chart error: {str(e)}")
    else:
        st.info("Not enough history data for trends yet.")
except Exception as e:
    st.error(f"Error generating history chart: {str(e)}")
