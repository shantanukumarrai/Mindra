import os
import requests
from dotenv import load_dotenv
load_dotenv()

def send_reminder_email(to_email, name):
    """Send daily meditation reminder using Resend API[](https://resend.com)"""
    api_key = os.getenv('RESEND_API_KEY')
    sender_email = os.getenv('SENDER_EMAIL')
    app_name = os.getenv('APP_NAME', 'Daily Meditation Streak')

    if not api_key or not sender_email:
        print("⚠️  Resend credentials missing in .env")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    login_link = "http://127.0.0.1:5000/login"   # ← change to your real domain in production

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #00695c;">🧘 Hi {name},</h2>
        <p>It's time for your daily 1-minute meditation session!</p>
        <p style="font-size: 1.1em; margin: 20px 0;">
          <strong>Take a moment, breathe, and keep your streak alive! 🔥</strong>
        </p>
        <p>
          <a href="{login_link}" style="background: #00695c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
            Log in & Start Meditation
          </a>
        </p>
        <p style="color: #666; font-size: 0.9em;">
          {app_name}<br>
          Sent via Resend
        </p>
      </body>
    </html>
    """

    payload = {
        "from": f"{app_name} <{sender_email}>",
        "to": [to_email],
        "subject": "🧘 Your 1-Minute Meditation Reminder",
        "html": html_content
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"✅ Reminder email sent to {to_email}")
            return True
        else:
            print(f"❌ Resend API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False