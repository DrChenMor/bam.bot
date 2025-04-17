import os
import json
import streamlit as st
from cryptography.fernet import Fernet

# Load your Fernet key from env (must be set before running)
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    st.error("⚠️ FERNET_KEY not set in environment")
    st.stop()

# Initialize Fernet
f = Fernet(FERNET_KEY.encode())

st.title("🥜 Bamba Availability Tracker Signup")

# Show only latest status (optional)
try:
    latest = json.load(open("history.json"))["runs"][-1]
    ts = latest[0]["timestamp"].replace("T"," ").split(".")[0]
    st.subheader(f"Last checked at {ts} AWST")
    for s in latest:
        mark = "✅" if s["available"] else "❌"
        st.write(f"{mark} **{s['store']}**")
except:
    st.write("No checks run yet.")

st.header("Subscribe for Email Alerts")
mode  = st.radio("Notify me when:", ["Immediate", "Daily summary"])
email = st.text_input("Your email address")

if st.button("Subscribe"):
    # Encrypt the email
    token = f.encrypt(email.encode()).decode()

    # Load existing subscribers (or create fresh)
    subs_file = "subscribers.json"
    if os.path.exists(subs_file):
        data = json.load(open(subs_file))
    else:
        data = {"users": []}

    # Append new subscriber
    data["users"].append({
        "token": token,
        "mode":  "immediate" if mode=="Immediate" else "daily"
    })

    # Save back
    with open(subs_file, "w") as fp:
        json.dump(data, fp, indent=2)

    st.success("🎉 You're subscribed! Check your inbox soon.")
