import streamlit as st, json
from datetime import datetime

st.title("🥜 Bamba Availability Community")

# Current status
st.header("Latest Check")
try:
    latest = json.load(open("history.json"))["runs"][-1]
    ts = latest[0]["timestamp"].replace("T"," ").split(".")[0]
    st.subheader(f"Checked at {ts} AWST")
    for s in latest:
        mark = "✅" if s["available"] else "❌"
        st.write(f"{mark} **{s['store']}**")
except:
    st.write("No data yet—please check back soon!")

# Signup form
st.header("Subscribe for Email Alerts")
mode = st.radio("Notify me when:", ["Immediate", "Daily summary"])
email = st.text_input("Your email address")

if st.button("Subscribe"):
    data = json.load(open("subscribers.json"))
    data["users"].append({
      "email": email,
      "mode":  "immediate" if mode=="Immediate" else "daily"
    })
    with open("subscribers.json","w") as f:
        json.dump(data, f, indent=2)
    st.success("🎉 You’re subscribed! Keep an eye on your inbox.")
