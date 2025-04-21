import os, json, streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime
import pytz
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def format_awst_time(ts):
    """Convert any timestamp to AWST formatted time."""
    if isinstance(ts, str):
        # Handle string timestamps
        if 'T' in ts:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(ts)
    else:
        # It's already a datetime object
        dt = ts
        
    # Ensure timezone info exists
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=pytz.utc)
        
    # Convert to AWST
    awst = pytz.timezone('Australia/Perth')
    awst_time = dt.astimezone(awst)
    return awst_time.strftime('%Y-%m-%d %H:%M:%S AWST')

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

def send_email(to_email, subject, html_content):
    """Send an email with HTML content."""
    # Add this debugging line
    print(f"Sending from: {FROM_EMAIL}, SMTP user: {SMTP_USER}")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM_EMAIL, to_email, msg.as_string())
    print(f"Email sent to {to_email}")
    
# ─── PAGE CONFIG & FONT ──────────────────────────────────────
st.set_page_config(
    page_title="BamBot - Bamba Tracker",
    layout="centered",
    page_icon="bamlogo.png"
)

# Get the query parameters to check for unsubscribe tokens
query_params = st.query_params

# Enhanced unsubscribe handler in app.py
if "token" in query_params:
    try:
        from supabase_client import verify_unsubscribe_token, unsubscribe_email
        
        token = query_params["token"][0]
        # Debug output (you can remove this later)
        st.write(f"Debug - Token received: {token[:10]}...")
        
        # Try to verify the token with detailed error handling
        try:
            email = verify_unsubscribe_token(token)
            if email:
                st.write(f"Debug - Token verified for: {email}")
            else:
                st.write("Debug - Token verification failed")
                
                # Get the actual Fernet key being used (partially masked for security)
                import os
                key = os.getenv("FERNET_KEY", "")
                if key:
                    st.write(f"Debug - Using Fernet key: {key[:5]}...{key[-5:]}")
                else:
                    st.write("Debug - Fernet key not found in environment")
        except Exception as e:
            st.write(f"Debug - Token verification error: {str(e)}")
        
        st.title("Unsubscribe from Bamba Tracker")
        
        # Continue with enhanced manual unsubscribe form
        st.write("### Unsubscribe by Email")
        manual_email = st.text_input("Enter your email address:")
        if st.button("Unsubscribe"):
            if manual_email and "@" in manual_email:
                if unsubscribe_email(manual_email):
                    st.success(f"You have been unsubscribed. You will no longer receive Bamba notifications.")
                else:
                    st.warning("Email not found in our subscriber list or already unsubscribed.")
            else:
                st.error("Please enter a valid email address.")
                    
        # Stop here - don't show the main app
        st.stop()
    except Exception as e:
        st.error(f"Error processing unsubscribe request: {str(e)}")
        st.error("Please try the manual unsubscribe option at the bottom of the page.")

# Try to import Supabase client
try:
    from supabase_client import add_subscriber, get_subscribers, unsubscribe_email
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
    st.markdown("<h2>🥜 BamBot WA - Availability Tracker Signup</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div>
        <p><b>Immediate Update</b> – Send emails only when Bamba availability changes since the last check.</p>  
        <p><b>Daily summary</b> – One friendly recap at 15:00 AWST.</p>  
        <p>🔐 We keep your address <b>encrypted</b>— only our bot can read it.
        </div>
        """,
        unsafe_allow_html=True,
    )
    
with col_he:
    st.markdown("<h2 dir='rtl'>🥜 במבוט WA - הרשמה למעקב על במבה</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div dir="rtl">
        <p><b>התראות מיידיות</b> – שלח דחוף אימייל ברגע שאתה מזהה שיש שינוי בסטטוס של הבמבה בסניף דיאנלה או מיררבוקה למה אני זקוק למנת בוטנים.</p>
        <p><b>סיכום יומי</b> – סיכום פעם ביום שנייה לפני שאוספים את הילדים ב–15:00.</p>
        <p> 🔐 האימייל שלך <b>מוצפן</b> – הגנה מפני אנטישמים מובטחת, אלא אם הבוט שלנו יתאסלם.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── SUBSCRIPTION FORM ───────────────────────────────────────
st.markdown("---")

# Create columns to center the form elements

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
        options=["Both stores", "Dianella only / לא יוצא/ת מהגטו", "Mirrabooka only / יש עוד עולם מחוץ לגטו?!"],
        index=0
    )
        
        # Size preference
    size_preference = st.radio(
        "Which Bamba size(s) would you like alerts for? / במילים אחרות, הגודל כן קובע",
        options=["Both sizes", "25g only", "100g only"],
        index=0
    )
        
        # Notification preferences - CHANGED THIS LINE
    cols = st.columns(2)
    with cols[0]:
        notify_every_check = st.checkbox("Send me updates on every check (even when nothing changes) / אין לי חיים חוץ מבמבה! בקיצור, את אמא שלי הייתי מוכר בשביל מנת בוטנים", value=False)
    with cols[1]:
        include_facts = st.checkbox("Include Bamba facts with notifications / אני רוצה עובדות על במבה שיהיה לי מה לקרוא בשירותים", value=False)
    
email = st.text_input("Your email / כתובת המייל שלך")
    
# Find this section in app.py (around line 326)
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
                "notify_on_change_only": not notify_every_check,
                "include_facts": include_facts
            }
                
            # Try to use Supabase if available
            if use_supabase:
                try:
                    # Add to Supabase with detailed error logging
                    result = add_subscriber(email, preferences)
                        
                    if result["status"] == "created":
                        st.success("🎉 You're signed up! Check your inbox soon.")
                        
                        # *** ADD THE WELCOME EMAIL CODE HERE ***
                        try:
                            # Create welcome email HTML
                            welcome_subject = "👋 Welcome to Bamba Tracker!"
                            welcome_html = f"""
                            <style>
                            .container {{font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;}}
                            .header {{color: #4CAF50; font-size: 24px;}}
                            .section {{margin: 15px 0;}}
                            </style>
                            <div class="container">
                                <h1 class="header">Welcome to Bamba Tracker!</h1>
                                <p>Hi there,</p>
                                <p>Thanks for subscribing to Bamba Tracker! You'll now receive updates about Bamba availability at Coles stores in Perth.</p>
                                
                                <div class="section">
                                    <h3>Your subscription details:</h3>
                                    <ul>
                                        <li><strong>Notification mode:</strong> {preferences['mode']}</li>
                                        <li><strong>Store preference:</strong> {preferences['store_preference']}</li>
                                        <li><strong>Size preference:</strong> {preferences['product_size_preference']}</li>
                                    </ul>
                                </div>
                                
                                <p>We'll keep you updated on Bamba availability according to your preferences. Keep it nutty! 🤪</p>
                                
                                <p style="color: #777; margin-top: 20px;">Your BamBot WA</p>
                            </div>
                            """
                            
                            # Send the welcome email
                            send_email(email, welcome_subject, welcome_html)
                            print(f"Welcome email sent to {email}")
                        except Exception as e:
                            print(f"Error sending welcome email: {e}")
                        # *** END OF WELCOME EMAIL CODE ***
                        
                    else:
                        st.success("✅ Your subscription preferences have been updated.")
                except Exception as e:
                    st.error(f"Supabase subscription error: {str(e)}")
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
st.subheader("🔍 Current Bamba Status / גיא פינאטס של הבמבות")

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

# Removed extra closing div that was causing rendering issues
st.markdown("---")

# ─── AVAILABILITY HISTORY CHART ─────────────────────────────
st.subheader("Availability History")

# Add a refresh button
refresh = st.button("🔄 Refresh History Data")

try:
    # Always reload data from file to ensure we have latest
    with open("history.json", "r") as f:
        hist_content = f.read()
        hist = json.loads(hist_content)["runs"]
    
    if len(hist) > 1:  # Only show if we have multiple data points
        # Convert data for charting with size breakdown
        chart_data = []
        
        for i, run in enumerate(hist):
            # Get timestamp in readable format
            ts = run[0]["timestamp"].replace("T", " ").split(".")[0]
            
            # Process each store
            for store_data in run:
                store_name = store_data["store"]
                
                # Initialize counters for different product sizes
                size_25g_available = 0
                size_100g_available = 0
                size_25g_total = 0
                size_100g_total = 0
                
                # Count products by size
                for product in store_data["products"]:
                    # Extract size from product name
                    product_size = "unknown"
                    if "|" in product["name"]:
                        size_part = product["name"].split("|")[1].strip()
                        if "25g" in size_part:
                            product_size = "25g"
                            size_25g_total += 1
                            if product["available"]:
                                size_25g_available += 1
                        elif "100g" in size_part:
                            product_size = "100g"
                            size_100g_total += 1
                            if product["available"]:
                                size_100g_available += 1
                    
                # Add entry for this store and timestamp with size breakdown
                chart_data.append({
                    "run": i,
                    "time": ts,
                    "store": store_name,
                    "size": "25g",
                    "available": size_25g_available,
                    "total": size_25g_total,
                    "availability_pct": round(size_25g_available/size_25g_total*100 if size_25g_total > 0 else 0)
                })
                
                chart_data.append({
                    "run": i,
                    "time": ts,
                    "store": store_name,
                    "size": "100g",
                    "available": size_100g_available,
                    "total": size_100g_total,
                    "availability_pct": round(size_100g_available/size_100g_total*100 if size_100g_total > 0 else 0)
                })
        
        # Display as a table with better formatting
        st.write("### Check History Data")
        
        # Create a cleaner dataframe view
        import pandas as pd
        df = pd.DataFrame(chart_data)
        
        # Format the time column
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df['Time'] = df['time'].apply(format_awst_time)
        
        # Create a display-friendly dataframe
        display_df = df[['time', 'store', 'size', 'available', 'total', 'availability_pct']].rename(
            columns={
                'time': 'Time',
                'store': 'Store',
                'size': 'Size',
                'available': 'In Stock',
                'total': 'Total Products', 
                'availability_pct': 'Availability %'
            }
        )
        
        # Add % sign to availability
        display_df['Availability %'] = display_df['Availability %'].astype(str) + '%'
        
        # Sort by most recent time first
        display_df = display_df.sort_values(by=['Time', 'Store', 'Size'], ascending=[False, True, True])
        
        st.dataframe(display_df, use_container_width=True)
        
        # Create a visual chart that shows size breakdown
        st.write("### Availability Trend by Size")
        
        try:
            # Use Altair for nicer charts
            import altair as alt
            
            # Create a chart that shows size availability over time
            chart_df = df.copy()
            chart_df['product_size'] = chart_df['store'] + ' - ' + chart_df['size']
            
            # Group by time and store-size combination
            pivot_df = pd.pivot_table(
                chart_df,
                index='time',
                columns='product_size',
                values='available',
                aggfunc='sum'
            ).reset_index()
            
            # Melt for charting
            chart_data = pd.melt(
                pivot_df, 
                id_vars=['time'], 
                var_name='Product', 
                value_name='Available Count'
            )
            
            # Create the chart
            chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('time:N', title='Time', sort=None),
                y=alt.Y('Available Count:Q', title='Products Available'),
                color=alt.Color('Product:N', title='Store - Size'),
                tooltip=['time', 'Product', 'Available Count']
            ).properties(
                width=600,
                height=300,
                title='Bamba Availability Trend by Size'
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            # Fallback to basic chart if Altair fails
            st.error(f"Advanced chart error: {str(e)}")
            st.line_chart(pivot_df.set_index('time'))
    else:
        st.info("Not enough history data for trends yet.")
except Exception as e:
    st.error(f"Error generating history chart: {str(e)}")
    st.code(f"Error details: {traceback.format_exc()}")

# ─── UNSUBSCRIBE SECTION ─────────────────────────────────────
st.markdown("---")
with st.expander("Unsubscribe from Notifications"):
    st.write("If you no longer wish to receive Bamba notifications, enter your email below:")
    unsub_email = st.text_input("Your email address", key="unsubscribe_email")
    
    if st.button("Unsubscribe Me", key="unsubscribe_button"):
        if unsub_email and "@" in unsub_email:
            if use_supabase:
                try:
                    if unsubscribe_email(unsub_email):
                        st.success("YYou have been unsubscribed. You will no longer receive Bamba notifications. תמות! בייייי")
                    else:
                        st.warning("Email not found in our subscriber list or already unsubscribed.")
                except Exception as e:
                    st.error(f"Error unsubscribing: {str(e)}")
            else:
                # Fallback to local file approach
                try:
                    subfile = "subscribers.json"
                    data = json.load(open(subfile)) if os.path.exists(subfile) else {"users":[]}
                    
                    found = False
                    new_users = []
                    for user in data["users"]:
                        try:
                            email = f.decrypt(user["token"].encode()).decode()
                            if email.lower() != unsub_email.lower():
                                new_users.append(user)
                            else:
                                found = True
                        except:
                            new_users.append(user)
                    
                    if found:
                        data["users"] = new_users
                        with open(subfile, "w") as fp:
                            json.dump(data, fp, indent=2)
                        st.success("You have been unsubscribed. You will no longer receive Bamba notifications. תמות! בייייי")
                    else:
                        st.warning("Email not found in our subscriber list or already unsubscribed.")
                except Exception as e:
                    st.error(f"Error unsubscribing: {str(e)}")
        else:
            st.error("Please enter a valid email address.")
            
# ─── APP FOOTER ────────────────────────────────────────────
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown(
        """
        <div style="text-align: center;">
            <h4>About</h4>
            <p>Bamba Tracker helps the Perth Israeli community find their 'favorite' snack. / מוזמנים להזמין אותי לשבת איתכם לשיחה עם במבה יבשה בלבד או ביסלי גריל שהוא החטיף האולטימטיבי, וכמובן אפרופו שהוא בכלל עוד להיט מאילנית</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

with footer_col2:
    st.markdown(
        """
        <div style="text-align: center;">
            <h4>Contact in case of emergency</h4>
            <p>Email: <a href="mailto:bambotwa@gmail.com">bambotwa@gmail.com</a></p>
        </div>
        """, 
        unsafe_allow_html=True
    )

with footer_col3:
    st.markdown(
        """
        <div style="text-align: center;">
            <h4>Credits</h4>
            <p>Created by Chen Mor</p>
            <p>© 2025 All rights reserved to no one</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
