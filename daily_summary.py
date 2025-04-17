import json, os
from datetime import date
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# 1) Gather today’s runs
hist = json.load(open("history.json"))
today = date.today().isoformat()
runs  = [r for r in hist["runs"] if r and r[0]["timestamp"].startswith(today)]
if not runs:
    print("No runs today; nothing to email.")
    exit()

# 2) Build a *fun* daily summary
html = "<h2>🥜 Bamba Daily Chuckle & Check</h2>"
for run in runs:
    ts = run[0]["timestamp"]
    html += f"<h3>Checked at {ts.split('T')[1][:8]}</h3><ul>"
    for s in run:
        mark = "✅" if s["available"] else "❌"
        html += f"<li>{mark} {s['store']} — {len(s['products'])} products seen</li>"
    html += "</ul>"
html += "<p>That's all for today! Stay nutty 🤪</p>"

# 3) Email every “daily” subscriber
subs = [u for u in json.load(open("subscribers.json"))["users"] if u["mode"]=="daily"]
sg   = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
for u in subs:
    msg = Mail(
        from_email="noreply@bambabot.com",
        to_emails=u["email"],
        subject="🌰 Bamba Daily Report: your peanut roundup",
        html_content=html
    )
    sg.send(msg)
    print("✉️ Daily summary to", u["email"])
