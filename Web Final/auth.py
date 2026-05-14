"""
TerraAI – Authentication Module
Handles: user storage, OTP generation, email sending, session management
"""

import os
import json
import random
import string
import smtplib
import hashlib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load .env (safe no-op on Render/Heroku where vars are injected natively)
load_dotenv()

# ── Config — all values from environment variables ────────────────────────────
SMTP_EMAIL    = os.getenv("SMTP_EMAIL",    "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))

USERS_FILE    = "users.json"
OTP_EXPIRY    = 600   # 10 minutes in seconds

# ── User store (JSON file) ────────────────────────────────────────────────────
def _load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ── OTP store (in-memory, keyed by email) ────────────────────────────────────
# Structure: { email: { "otp": "123456", "expires": timestamp, "data": {...} } }
_otp_store: dict = {}

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))

def store_otp(email: str, otp: str, user_data: dict):
    """Store OTP with expiry and pending user data."""
    _otp_store[email.lower()] = {
        "otp":     otp,
        "expires": time.time() + OTP_EXPIRY,
        "data":    user_data,
    }

def verify_otp(email: str, otp: str) -> tuple[bool, str]:
    """
    Returns (success, message).
    On success, creates the user account and removes OTP entry.
    """
    key = email.lower()
    entry = _otp_store.get(key)

    if not entry:
        return False, "No OTP found for this email. Please sign up again."

    if time.time() > entry["expires"]:
        _otp_store.pop(key, None)
        return False, "OTP has expired. Please sign up again."

    if entry["otp"] != otp.strip():
        return False, "Incorrect OTP. Please try again."

    # OTP correct — create account
    users = _load_users()
    data  = entry["data"]
    users[key] = {
        "name":     data["name"],
        "email":    key,
        "password": _hash_password(data["password"]),
        "created":  time.time(),
    }
    _save_users(users)
    _otp_store.pop(key, None)
    return True, "Account created successfully!"

def resend_otp(email: str) -> tuple[bool, str]:
    """Generate a fresh OTP for an existing pending signup."""
    key = email.lower()
    entry = _otp_store.get(key)
    if not entry:
        return False, "No pending signup found. Please sign up again."
    new_otp = generate_otp()
    entry["otp"]     = new_otp
    entry["expires"] = time.time() + OTP_EXPIRY
    ok, msg = send_otp_email(email, new_otp, entry["data"]["name"])
    return ok, msg

# ── User lookup ───────────────────────────────────────────────────────────────
def user_exists(email: str) -> bool:
    return email.lower() in _load_users()

def authenticate(email: str, password: str) -> tuple[bool, dict | None]:
    users = _load_users()
    user  = users.get(email.lower())
    if not user:
        return False, None
    if user["password"] == _hash_password(password):
        return True, user
    return False, None

def get_user(email: str) -> dict | None:
    return _load_users().get(email.lower())

# ── Email sender ──────────────────────────────────────────────────────────────
def send_otp_email(to_email: str, otp: str, name: str) -> tuple[bool, str]:
    """Send OTP verification email. Returns (success, message)."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False, "SMTP credentials not configured. Set SMTP_EMAIL and SMTP_PASSWORD in Railway environment variables."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🌱 TerraAI – Your Verification Code"
        msg["From"]    = f"TerraAI <{SMTP_EMAIL}>"
        msg["To"]      = to_email

        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    body {{ margin:0; padding:0; background:#0a0e1a; font-family:'Segoe UI',Arial,sans-serif; }}
    .wrap {{ max-width:520px; margin:40px auto; background:#0f1629;
             border:1px solid rgba(0,230,118,0.2); border-radius:20px; overflow:hidden; }}
    .header {{ background:linear-gradient(135deg,#00e676,#00b248);
               padding:32px 40px; text-align:center; }}
    .header h1 {{ margin:0; color:#000; font-size:26px; font-weight:800; }}
    .header p  {{ margin:6px 0 0; color:#003d1a; font-size:14px; }}
    .body {{ padding:36px 40px; }}
    .greeting {{ color:#f0f4f8; font-size:16px; margin-bottom:20px; }}
    .otp-box {{ background:rgba(0,230,118,0.08); border:2px solid rgba(0,230,118,0.3);
                border-radius:14px; padding:24px; text-align:center; margin:24px 0; }}
    .otp-label {{ color:#8899aa; font-size:12px; text-transform:uppercase;
                  letter-spacing:0.1em; margin-bottom:10px; }}
    .otp-code {{ font-size:42px; font-weight:800; color:#00e676;
                 letter-spacing:12px; font-family:'Courier New',monospace; }}
    .otp-expiry {{ color:#8899aa; font-size:12px; margin-top:10px; }}
    .note {{ color:#556677; font-size:13px; line-height:1.6; margin-top:20px; }}
    .footer {{ border-top:1px solid rgba(255,255,255,0.06); padding:20px 40px;
               text-align:center; color:#556677; font-size:12px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>🌱 TerraAI</h1>
      <p>Smart Agriculture Intelligence Platform</p>
    </div>
    <div class="body">
      <p class="greeting">Hi <strong style="color:#00e676">{name}</strong>,</p>
      <p style="color:#8899aa;font-size:14px;">
        Thanks for signing up! Use the verification code below to complete your registration.
      </p>
      <div class="otp-box">
        <div class="otp-label">Your Verification Code</div>
        <div class="otp-code">{otp}</div>
        <div class="otp-expiry">⏱ Expires in 10 minutes</div>
      </div>
      <p class="note">
        If you didn't request this, you can safely ignore this email.<br/>
        Never share this code with anyone.
      </p>
    </div>
    <div class="footer">
      © 2025 TerraAI &nbsp;|&nbsp; B.Tech CSE Final Year Project
    </div>
  </div>
</body>
</html>
"""
        text_part = MIMEText(
            f"Hi {name},\n\nYour TerraAI verification code is: {otp}\n\nExpires in 10 minutes.",
            "plain"
        )
        html_part = MIMEText(html, "html")
        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        print(f"[INFO] OTP email sent to {to_email}")
        return True, "OTP sent successfully."

    except smtplib.SMTPAuthenticationError:
        print(f"[ERROR] SMTP auth failed for {SMTP_EMAIL}")
        return False, "Email authentication failed. Check SMTP credentials."
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error: {e}")
        return False, f"Email send failed: {e}"
    except Exception as e:
        print(f"[ERROR] Unexpected email error: {e}")
        return False, f"Unexpected error: {e}"
