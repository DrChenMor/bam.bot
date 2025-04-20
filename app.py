import os, json, streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime
import pytz  # Add this import - it was missing before

def format_awst_time(timestamp_str):
    """Convert any timestamp to AWST formatted time."""
    if 'T' in timestamp_str:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    else:
        dt = datetime.fromisoformat(timestamp_str)
    
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=pytz.utc)
        
    # Convert to AWST
    awst = pytz.timezone('Australia/Perth')
    awst_time = dt.astimezone(awst)
    return awst_time.strftime('%Y-%m-%d %H:%M:%S AWST')
    
# ─── PAGE CONFIG & FONT ──────────────────────────────────────
st.set_page_config(
    page_title="Bam.Bot - Bamba Tracker",
    layout="centered",
    page_icon="bamlogo.png"
)

# Try to import Supabase client
try:
    from supabase_client import add_subscriber, get_subscribers
    use_supabase = True
    st.sidebar.success("✅ Supabase connected")
except ImportError as e:
    use_supabase = False
    st.sidebar.error(f"❌ Supabase not connected: {e}")
except Exception as e:
    use_supabase = False
    st.sidebar.error(f"❌ Supabase error: {e}")

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
        border-left: 4px solid #000000;
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
st.markdown("---")

# Create columns to center the form elements
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.subheader("Subscribe for Bamba Alerts")
    
    # Basic subscription mode
    mode = st.radio(
        "Notification frequency / תדירות ההתראות:",
        ["Immediate updates / התראות מיידיות", "Daily summary / סיכום יומי"]
    )
    
    # Advanced settings expander
    with st.expander("Advanced Subscription Options"):
        st.write("Customize your Bamba alerts:")
        
        # Store preference
        store_preference = st.radio(
            "Which store(s) would you like alerts for?",
            options=["Both stores", "Dianella only", "Mirrabooka only"],
            index=0
        )
        
        # Size preference
        size_preference = st.radio(
            "Which Bamba size(s) would you like alerts for?",
            options=["Both sizes", "25g only", "100g only"],
            index=0
        )
        
        # Notification preferences
        cols = st.columns(2)
        with cols[0]:
            notify_on_change = st.checkbox("Only notify when availability changes", value=False)
        with cols[1]:
            include_facts = st.checkbox("Include Bamba facts with notifications", value=False)
    
    email = st.text_input("Your email / כתובת המייל שלך")
    
    if st.button("Subscribe", use_container_width=True):
        if not email or "@" not in email:
            st.error("Please enter a valid email address")
        else:
            try:
                # Convert UI selections to database format
                preferences = {
                    "mode": "immediate" if mode.startswith("Immediate") else "daily",
                    "store_preference": "both" if store_preference == "Both stores" else store_preference.replace(" only", "").lower(),
                    "product_size_preference": "both" if size_preference == "Both sizes" else size_preference.replace(" only", "").lower(),
                    "notify_on_change_only": notify_on_change,
                    "include_facts": include_facts
                }
                
                # Try to use Supabase if available
                if use_supabase:
                    try:
                        # Add to Supabase with detailed error logging
                        result = add_subscriber(email, preferences)
                        
                        if result["status"] == "created":
                            st.success("🎉 You're signed up! Check your inbox soon.")
                        else:
                            st.success("✅ Your subscription preferences have been updated.")
                    except Exception as e:
                        st.error(f"Supabase subscription error: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
                else:
                    # Fall back to local file if Supabase is not available
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
                            "mode": preferences["mode"],
                            "date_added": datetime.now().isoformat()
                            # Note: The local file approach doesn't support advanced preferences
                        })
                        with open(subfile,"w") as fp:
                            json.dump(data, fp, indent=2)
                        st.success("🎉 You're signed up! Check your inbox soon.")
            except Exception as e:
                st.error(f"Subscription error: {str(e)}")
                
st.markdown("---")

# ─── IMPROVED LATEST STATUS ─────────────────────────────────
st.subheader("🔍 Current Bamba Status")

try:
    # Refresh the data on each page load to ensure we have the latest
    hist = json.load(open("history.json"))["runs"]
    latest = hist[-1]
    
    # Format timestamp for better readability
    ts_raw = latest[0]["timestamp"]
    ts = format_awst_time(ts_raw)
    st.write(f"### Last checked at {ts}")
    
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

st.markdown("---")

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
