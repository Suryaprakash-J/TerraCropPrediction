"""
TerraAI – Flask Application
Run:  python app.py
"""

import os
import re
import pickle
import json
import numpy as np
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv

# Load .env file (no-op if running on Render/Heroku where vars are set natively)
load_dotenv()

# ── Gemini API ────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

def get_gemini_explanation(crop: str, confidence: float, N, P, K, temp, humidity, ph, rainfall) -> tuple[str, bool]:
    """Returns (explanation_text, is_gemini_powered)."""
    prompt = (
        f"You are an agricultural AI assistant. The ML model predicted '{crop}' as the best crop "
        f"with {confidence}% confidence based on these soil/climate values: "
        f"Nitrogen={N} kg/ha, Phosphorus={P} kg/ha, Potassium={K} kg/ha, "
        f"Temperature={temp}°C, Humidity={humidity}%, pH={ph}, Rainfall={rainfall}mm. "
        f"Write exactly 2-3 sentences explaining WHY {crop} is recommended for these conditions. "
        f"Be specific about which values make it suitable. Keep it simple and farmer-friendly."
    )
    try:
        resp = requests.post(
            GEMINI_URL,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=10,
        )
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text, True
    except Exception:
        pass
    return _local_explanation(crop, confidence, float(N), float(P), float(K),
                              float(temp), float(humidity), float(ph), float(rainfall)), False


def _local_explanation(crop: str, confidence: float,
                       N: float, P: float, K: float,
                       temp: float, humidity: float, ph: float, rainfall: float) -> str:
    """Rule-based fallback explanation when Gemini API is unavailable."""
    reasons = []

    # pH suitability
    if 5.5 <= ph <= 7.5:
        reasons.append(f"the soil pH of {ph} is within the ideal neutral-to-slightly-acidic range")
    elif ph < 5.5:
        reasons.append(f"the acidic soil pH of {ph} suits acid-tolerant crops like {crop}")
    else:
        reasons.append(f"the alkaline soil pH of {ph} is compatible with {crop}")

    # Rainfall
    if rainfall > 150:
        reasons.append(f"the high rainfall of {rainfall}mm provides excellent moisture for growth")
    elif rainfall > 80:
        reasons.append(f"the moderate rainfall of {rainfall}mm supports steady crop development")
    else:
        reasons.append(f"the low rainfall of {rainfall}mm suits drought-tolerant varieties")

    # Humidity
    if humidity > 70:
        reasons.append(f"the high humidity of {humidity}% creates favorable growing conditions")
    elif humidity > 40:
        reasons.append(f"the moderate humidity of {humidity}% is well-suited for cultivation")

    # Nitrogen
    if N > 60:
        reasons.append(f"the rich nitrogen content of {N} kg/ha supports strong vegetative growth")
    elif N > 20:
        reasons.append(f"the adequate nitrogen level of {N} kg/ha meets the crop's nutritional needs")

    # Temperature
    if 18 <= temp <= 32:
        reasons.append(f"the temperature of {temp}°C is within the optimal growing range")

    # Build sentence
    if len(reasons) >= 2:
        intro = f"{crop} is highly recommended with {confidence}% confidence because "
        body  = reasons[0] + " and " + reasons[1] + ". "
        extra = ("Additionally, " + reasons[2] + ".") if len(reasons) > 2 else ""
        return intro + body + extra
    return (
        f"{crop} is the best match for your soil and climate conditions with {confidence}% confidence. "
        f"The combination of soil nutrients, pH, and environmental factors aligns well with "
        f"{crop}'s growth requirements."
    )

# ── OCR imports (optional) ────────────────────────────────────────────────────
try:
    from PIL import Image
    import pytesseract
    # Point to Tesseract binary on Windows
    import platform
    if platform.system() == "Windows":
        _tess_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for _p in _tess_paths:
            if os.path.exists(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                break
    OCR_AVAILABLE = True
    print("[INFO] OCR (pytesseract + Pillow) loaded successfully.")
except ImportError:
    OCR_AVAILABLE = False
    print("[WARN] OCR libraries not installed (Pillow / pytesseract).")

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16 MB
app.secret_key = os.getenv("FLASK_SECRET_KEY", "")
if not app.secret_key:
    import secrets as _secrets
    app.secret_key = _secrets.token_hex(32)
    print("[WARN] FLASK_SECRET_KEY not set — using a random key (sessions will reset on restart)")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"}

os.makedirs("uploads", exist_ok=True)
os.makedirs("models", exist_ok=True)

# ── Auth import ───────────────────────────────────────────────────────────────
from auth import (
    generate_otp, store_otp, verify_otp, resend_otp,
    user_exists, authenticate, get_user, send_otp_email
)

# ── Login required decorator ──────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ── Load ML model ─────────────────────────────────────────────────────────────
MODEL_PATH = "models/crop_model.pkl"
ENCODER_PATH = "models/label_encoder.pkl"

model, label_encoder = None, None

def load_model():
    global model, label_encoder
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(ENCODER_PATH, "rb") as f:
            label_encoder = pickle.load(f)
        print("[INFO] Model loaded successfully.")
    else:
        print("[WARN] Model files not found. Run train_model.py first.")

load_model()

# ── Weather API ───────────────────────────────────────────────────────────────
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "9f0265fb9cdccedb133031348db7209a")

# ── Crop emoji map ────────────────────────────────────────────────────────────
CROP_EMOJI = {
    "rice": "🌾", "maize": "🌽", "chickpea": "🫘", "kidneybeans": "🫘",
    "pigeonpeas": "🌿", "mothbeans": "🌱", "mungbean": "🌱",
    "blackgram": "🌿", "lentil": "🫘", "pomegranate": "🍎",
    "banana": "🍌", "mango": "🥭", "grapes": "🍇", "watermelon": "🍉",
    "muskmelon": "🍈", "apple": "🍎", "orange": "🍊", "papaya": "🍈",
    "coconuttree": "🥥", "cotton": "🌸", "jute": "🌿", "coffee": "☕",
}

def get_crop_emoji(crop_name: str) -> str:
    return CROP_EMOJI.get(crop_name.lower().replace(" ", ""), "🌱")

# ── Reverse compatibility knowledge base ─────────────────────────────────────
SOIL_CROP_COMPAT = {
    # (crop_lower, soil_lower) → (score 0-100, label, tips[])
    ("rice",        "clay"):        (92, "Excellent", ["Clay retains water perfectly for rice paddies", "Maintain flooded conditions", "Add organic matter to improve aeration"]),
    ("rice",        "loamy"):       (78, "Good",      ["Loamy soil supports rice well", "Ensure adequate irrigation", "Monitor drainage"]),
    ("rice",        "sandy"):       (35, "Poor",      ["Sandy soil drains too fast for rice", "Add clay amendments", "Increase irrigation frequency", "Use mulching to retain moisture"]),
    ("wheat",       "loamy"):       (90, "Excellent", ["Loamy soil is ideal for wheat", "Ensure good drainage", "Add nitrogen fertilizer"]),
    ("wheat",       "clay"):        (65, "Moderate",  ["Clay can waterlog wheat roots", "Improve drainage with sand", "Avoid over-irrigation"]),
    ("wheat",       "sandy"):       (50, "Moderate",  ["Sandy soil needs more fertilizer", "Increase irrigation", "Add organic compost"]),
    ("maize",       "loamy"):       (88, "Excellent", ["Loamy soil is perfect for maize", "Ensure good drainage", "Add phosphorus fertilizer"]),
    ("maize",       "sandy"):       (60, "Moderate",  ["Sandy soil needs frequent watering", "Add organic matter", "Use drip irrigation"]),
    ("maize",       "clay"):        (55, "Moderate",  ["Improve clay drainage", "Avoid waterlogging", "Add sand and compost"]),
    ("cotton",      "black"):       (95, "Excellent", ["Black cotton soil is ideal", "Excellent moisture retention", "Rich in nutrients naturally"]),
    ("cotton",      "loamy"):       (75, "Good",      ["Loamy soil supports cotton well", "Ensure good drainage", "Add potassium fertilizer"]),
    ("cotton",      "sandy"):       (40, "Poor",      ["Sandy soil lacks nutrients for cotton", "Add heavy compost", "Increase potassium and phosphorus", "Use drip irrigation"]),
    ("sugarcane",   "loamy"):       (85, "Excellent", ["Loamy soil is great for sugarcane", "Ensure adequate irrigation", "Add nitrogen-rich fertilizer"]),
    ("sugarcane",   "sandy"):       (45, "Moderate",  ["Increase moisture retention", "Add compost", "Improve potassium levels", "Use mulching"]),
    ("sugarcane",   "clay"):        (60, "Moderate",  ["Improve drainage", "Avoid waterlogging", "Add organic matter"]),
    ("tomato",      "loamy"):       (90, "Excellent", ["Loamy soil is perfect for tomatoes", "Ensure good drainage", "Add calcium to prevent blossom end rot"]),
    ("tomato",      "sandy"):       (55, "Moderate",  ["Sandy soil needs frequent watering", "Add organic matter", "Use balanced NPK fertilizer"]),
    ("potato",      "loamy"):       (88, "Excellent", ["Loamy soil is ideal for potatoes", "Ensure good drainage", "Add potassium fertilizer"]),
    ("potato",      "sandy"):       (70, "Good",      ["Sandy soil allows good tuber development", "Increase irrigation", "Add organic matter"]),
    ("potato",      "clay"):        (40, "Poor",      ["Clay soil restricts tuber growth", "Add sand and compost", "Improve drainage significantly"]),
    ("coffee",      "loamy"):       (82, "Good",      ["Loamy soil supports coffee well", "Ensure good drainage", "Add organic matter"]),
    ("coffee",      "red"):         (88, "Excellent", ["Red laterite soil is ideal for coffee", "Slightly acidic pH preferred", "Add organic compost"]),
    ("banana",      "loamy"):       (85, "Excellent", ["Loamy soil is great for bananas", "Ensure good drainage", "Add potassium-rich fertilizer"]),
    ("mango",       "loamy"):       (80, "Good",      ["Loamy soil supports mango well", "Ensure deep soil for roots", "Add phosphorus fertilizer"]),
    ("mango",       "sandy"):       (55, "Moderate",  ["Sandy soil needs more water", "Add organic matter", "Increase irrigation frequency"]),
}

GENERIC_TIPS = {
    "excellent": ["Soil is highly compatible with this crop", "Maintain current soil conditions", "Regular monitoring recommended"],
    "good":      ["Soil is suitable with minor adjustments", "Add balanced NPK fertilizer", "Monitor soil moisture regularly"],
    "moderate":  ["Soil needs improvement for optimal yield", "Add organic compost", "Test soil pH and adjust accordingly", "Consider soil amendment"],
    "poor":      ["Significant soil improvement needed", "Add heavy organic matter", "Consider raised bed farming", "Consult agricultural expert", "Test and correct soil pH"],
}

def analyze_compatibility(crop: str, soil: str):
    key = (crop.lower().strip(), soil.lower().strip().replace(" soil", "").replace(" ", ""))
    # direct match
    if key in SOIL_CROP_COMPAT:
        score, label, tips = SOIL_CROP_COMPAT[key]
        return score, label, tips
    # partial match
    for (c, s), (score, label, tips) in SOIL_CROP_COMPAT.items():
        if c in crop.lower() and s in soil.lower():
            return score, label, tips
    # generic fallback
    score = np.random.randint(45, 75)
    if score >= 70:
        label = "Good"
    elif score >= 50:
        label = "Moderate"
    else:
        label = "Poor"
    tips = GENERIC_TIPS[label.lower()]
    return score, label, tips

# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_value(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    user = get_user(session["user_email"])
    return render_template("index.html", user=user)

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user(session["user_email"])
    return render_template("dashboard.html", user=user)

# ── Auth routes ───────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_email" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return render_template("login.html", error="Please fill in all fields.")

        ok, user = authenticate(email, password)
        if ok:
            session["user_email"] = email
            session["user_name"]  = user["name"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_email" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()

        # Validation
        if not all([name, email, password, confirm]):
            return render_template("signup.html", error="Please fill in all fields.")
        if len(password) < 6:
            return render_template("signup.html", error="Password must be at least 6 characters.", name=name, email=email)
        if password != confirm:
            return render_template("signup.html", error="Passwords do not match.", name=name, email=email)
        if user_exists(email):
            return render_template("signup.html", error="An account with this email already exists.", email=email)

        # Generate & send OTP
        otp = generate_otp()
        store_otp(email, otp, {"name": name, "email": email, "password": password})
        ok, msg = send_otp_email(email, otp, name)

        if not ok:
            return render_template("signup.html", error=f"Could not send OTP: {msg}", name=name, email=email)

        return redirect(url_for("verify_otp_page", email=email))

    return render_template("signup.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp_page():
    email = request.args.get("email") or request.form.get("email", "")
    if not email:
        return redirect(url_for("signup"))

    if request.method == "POST":
        otp = (
            request.form.get("otp1", "") +
            request.form.get("otp2", "") +
            request.form.get("otp3", "") +
            request.form.get("otp4", "") +
            request.form.get("otp5", "") +
            request.form.get("otp6", "")
        )
        ok, msg = verify_otp(email, otp)
        if ok:
            # Auto-login after verification
            user = get_user(email)
            session["user_email"] = email
            session["user_name"]  = user["name"]
            return redirect(url_for("index"))
        else:
            return render_template("verify_otp.html", email=email, error=msg)

    return render_template("verify_otp.html", email=email)


@app.route("/resend-otp", methods=["POST"])
def resend_otp_route():
    email = request.form.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    ok, msg = resend_otp(email)
    return jsonify({"success": ok, "message": msg})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── Debug env check (remove after confirming Railway vars are set) ────────────
@app.route("/debug-env")
def debug_env():
    """Temporary route — shows which env vars are set (NOT their values)."""
    checks = {
        "FLASK_SECRET_KEY":   bool(os.getenv("FLASK_SECRET_KEY")),
        "GEMINI_API_KEY":     bool(os.getenv("GEMINI_API_KEY")),
        "OPENWEATHER_API_KEY":bool(os.getenv("OPENWEATHER_API_KEY")),
        "SMTP_EMAIL":         bool(os.getenv("SMTP_EMAIL")),
        "SMTP_PASSWORD":      bool(os.getenv("SMTP_PASSWORD")),
        "SMTP_HOST":          os.getenv("SMTP_HOST", "NOT SET"),
        "SMTP_PORT":          os.getenv("SMTP_PORT", "NOT SET"),
    }
    lines = [f"{'✅' if v is True else ('❌ NOT SET' if v is False else v)}  {k}"
             for k, v in checks.items()]
    return "<pre style='font-family:monospace;font-size:16px;padding:2rem'>" + \
           "TerraAI — Environment Variable Check\n\n" + "\n".join(lines) + "</pre>"

# ── Predict crop ──────────────────────────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    if model is None:
        return jsonify({"error": "Model not loaded. Run train_model.py first."}), 503

    data = request.get_json()
    try:
        features = np.array([[
            float(data["N"]),
            float(data["P"]),
            float(data["K"]),
            float(data["temperature"]),
            float(data["humidity"]),
            float(data["ph"]),
            float(data["rainfall"]),
        ]])
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    proba = model.predict_proba(features)[0]
    top5_idx = np.argsort(proba)[::-1][:5]

    recommendations = []
    for idx in top5_idx:
        crop_name = label_encoder.inverse_transform([idx])[0]
        confidence = round(float(proba[idx]) * 100, 1)
        recommendations.append({
            "crop": crop_name,
            "confidence": confidence,
            "emoji": get_crop_emoji(crop_name),
        })

    best = recommendations[0]
    explanation, is_gemini = get_gemini_explanation(
        best["crop"], best["confidence"],
        data["N"], data["P"], data["K"],
        data["temperature"], data["humidity"], data["ph"], data["rainfall"],
    )
    return jsonify({
        "best_crop":       best["crop"],
        "best_confidence": best["confidence"],
        "best_emoji":      best["emoji"],
        "explanation":     explanation,
        "gemini_powered":  is_gemini,
        "recommendations": recommendations,
    })

# ── OCR extract ───────────────────────────────────────────────────────────────
@app.route("/ocr", methods=["POST"])
def ocr_extract():
    if not OCR_AVAILABLE:
        return jsonify({"error": "OCR libraries not installed (Pillow / pytesseract)."}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        with Image.open(filepath) as img:
            img.load()   # force full read into memory
            text = pytesseract.image_to_string(img)
    except Exception as e:
        return jsonify({"error": f"OCR failed: {e}"}), 500
    finally:
        try:
            os.remove(filepath)
        except Exception:
            pass  # ignore if already removed or still locked

    # ── Pre-process text: fix common OCR artifacts ───────────────────────────
    # "pHs 55" → "pHs 5.5"  (missing decimal in pH values like 55, 65, 70)
    # "05" → "0.5"  (OCR drops decimal point in values like 0.5, 1.0)
    text_clean = text

    # Fix pH: "pHs 55" or "pH 55" where value should be "5.5" (single digit . single digit)
    def fix_ph_decimal(t):
        def replacer(m):
            val = m.group(2)
            # If it's a 2-digit number that looks like a pH (30-99) with no decimal, insert one
            if re.match(r'^\d{2}$', val):
                fixed = val[0] + '.' + val[1]
                return m.group(1) + fixed
            return m.group(0)
        return re.sub(r'(p[Hh]s?\s+)(\d{2})\b', replacer, t)

    text_clean = fix_ph_decimal(text_clean)

    # ── Extract N ─────────────────────────────────────────────────────────────
    N = extract_value(text_clean, [
        # "Nitrogen (N): 45"  or  "Nitrogen(N)  45"  — label+value on same line
        r"nitrogen\s*[\(\[]n[\)\]]\s*[:\s]+(\d+\.?\d*)",
        # Fertilizer table: "Nitrogen(N)" header then first data row value
        r"nitrogen\s*\(?n\)?\s*[^\n]*\n[^\n]*?(\d+\.?\d+)",
        # Any line containing nitrogen followed by a number
        r"\bnitrogen\b[^\n]{0,15}(\d+\.?\d+)",
    ])

    # ── Extract P ─────────────────────────────────────────────────────────────
    P = extract_value(text_clean, [
        # "Phosphorus (P)  7  lbs/a"
        r"phosphorus\s*[\(\[]p[\)\]]\s+(\d+\.?\d*)\s*(?:lbs?|kg|ppm|mg|$)",
        r"phosphorus\s*[\(\[]p[\)\]]\s*[:\s]+(\d+\.?\d*)",
        r"phospho\w*\s*[\(\[]p[\)\]][^\n]{0,20}?(\d+\.?\d+)",
        r"phospho\w*[^\n]{0,30}?(\d+\.?\d+)",
    ])

    # ── Extract K ─────────────────────────────────────────────────────────────
    K = extract_value(text_clean, [
        # "Potassium (K)  191  lbs/a"  — OCR may read (K) as (kK) or (K)
        r"potassium\s*[\(\[][kK]{1,2}[\)\]]\s+(\d+\.?\d*)\s*(?:lbs?|kg|ppm|mg|$)",
        r"potassium\s*[\(\[][kK]{1,2}[\)\]]\s*[:\s]+(\d+\.?\d*)",
        r"potassium[^\n]{0,20}?(\d+\.?\d+)",
    ])

    # ── Extract pH ────────────────────────────────────────────────────────────
    ph = extract_value(text_clean, [
        # "pHs  5.5"  or  "pHs  55" (after decimal fix above)
        r"\bphs?\s+(\d+\.?\d*)",
        r"soil\s*p\.?h\.?\s*[:\s=]+(\d+\.?\d*)",
        r"\bp\.?h\.?\s*[:\s=]+(\d+\.?\d*)",
        r"\bph\s+(\d+\.?\d*)",
    ])

    # ── Amendment-specific items (for soil amendment reports) ─────────────────
    AMENDMENT_PATTERNS = [
        ("azomite",      r"azom[il]te[^\n]*?([\d\.]+)\s*(?:oz|0z)"),
        ("gypsum",       r"gyps[uo]m[^\n]*?([\d\.]+)\s*(?:lbs?|oz|tbs?)"),
        ("feather_meal", r"feather\s*meal[^\n]*?([\d\.]+)\s*(?:oz|0z)"),
        ("sulfur",       r"(?:tiger|elemental|sultur|sulfur)[^\n]*?([\d\.]+)\s*(?:oz|0z)"),
        ("copper",       r"biomin\s*copper[^\n]*?([\d\.]+)\s*(?:oz|0z)"),
        ("zinc",         r"z[il]n[ce][^\n]*?sulfate[^\n]*?([\d\.]+)\s*(?:oz|0z)"),
        ("borax",        r"bor[ao]x[^\n]*?([\d\.]+)\s*(?:oz|0z)"),
    ]
    amendments = {}
    for name, pat in AMENDMENT_PATTERNS:
        m = re.search(pat, text_clean, re.IGNORECASE)
        if m:
            amendments[name] = m.group(1)

    # ── Report metadata ───────────────────────────────────────────────────────
    report_name = extract_value(text_clean, [r"report\s*(?:a?me|name)[\s:=\-]*([^\n]+)"])
    test_date   = extract_value(text_clean, [r"test\s*date[\s:=\-]*([^\n]+)", r"testdate[\s:=\-]*([^\n]+)"])
    area        = extract_value(text_clean, [r"(\d+)\s*(?:sq|s[qg])\s*(?:feet|ft|feat)"])
    total_wt    = extract_value(text_clean, [r"total\s*weight[^\n]*?([\d\.]+)\s*(?:lbs?|oz)"])

    extracted = {}
    if N:  extracted["N"] = N
    if P:  extracted["P"] = P
    if K:  extracted["K"] = K
    if ph: extracted["ph"] = ph

    if not extracted and not amendments:
        return jsonify({
            "warning": "Could not extract values. Try a clearer image.",
            "raw_text": text_clean[:800],
            "extracted": {},
            "amendments": {},
        })

    return jsonify({
        "extracted":   extracted,
        "amendments":  amendments,
        "report_meta": {
            "name":       report_name,
            "test_date":  test_date,
            "area_sqft":  area,
            "total_weight": total_wt,
        },
        "raw_text": text_clean[:800],
    })

# ── Weather ───────────────────────────────────────────────────────────────────
@app.route("/weather", methods=["GET"])
def weather():
    city = request.args.get("city", "")
    lat  = request.args.get("lat", "")
    lon  = request.args.get("lon", "")

    if WEATHER_API_KEY == "YOUR_API_KEY_HERE":
        # Return mock data so the UI still works without a real key
        return jsonify({
            "city": city or "Demo City",
            "temperature": 26.4,
            "humidity": 72,
            "rainfall": 85.0,
            "description": "Partly Cloudy",
            "icon": "02d",
            "mock": True,
        })

    try:
        if lat and lon:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
            )
        elif city:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
            )
        else:
            return jsonify({"error": "Provide city or coordinates."}), 400

        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        d = resp.json()

        rainfall = 0.0
        if "rain" in d:
            rainfall = d["rain"].get("1h", d["rain"].get("3h", 0.0))

        return jsonify({
            "city":        d.get("name", city),
            "temperature": round(d["main"]["temp"], 1),
            "humidity":    d["main"]["humidity"],
            "rainfall":    round(rainfall, 1),
            "description": d["weather"][0]["description"].title(),
            "icon":        d["weather"][0]["icon"],
            "mock":        False,
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 502

# ── Reverse compatibility ─────────────────────────────────────────────────────
@app.route("/compatibility", methods=["POST"])
def compatibility():
    data = request.get_json()
    crop = data.get("crop", "").strip()
    soil = data.get("soil", "").strip()

    if not crop or not soil:
        return jsonify({"error": "Crop and soil type are required."}), 400

    score, label, tips = analyze_compatibility(crop, soil)

    color_map = {
        "Excellent": "#00e676",
        "Good":      "#69f0ae",
        "Moderate":  "#ffab40",
        "Poor":      "#ff5252",
    }

    return jsonify({
        "crop":  crop,
        "soil":  soil,
        "score": score,
        "label": label,
        "color": color_map.get(label, "#69f0ae"),
        "tips":  tips,
    })

# ── City autocomplete ─────────────────────────────────────────────────────────
INDIAN_CITIES = [
    "Mumbai","Delhi","Bangalore","Hyderabad","Ahmedabad","Chennai","Kolkata",
    "Surat","Pune","Jaipur","Lucknow","Kanpur","Nagpur","Indore","Thane",
    "Bhopal","Visakhapatnam","Pimpri","Patna","Vadodara","Ghaziabad","Ludhiana",
    "Agra","Nashik","Faridabad","Meerut","Rajkot","Kalyan","Vasai","Varanasi",
    "Srinagar","Aurangabad","Dhanbad","Amritsar","Navi Mumbai","Allahabad",
    "Ranchi","Howrah","Coimbatore","Jabalpur","Gwalior","Vijayawada","Jodhpur",
    "Madurai","Raipur","Kota","Guwahati","Chandigarh","Solapur","Hubli",
    "Mysore","Tiruchirappalli","Bareilly","Aligarh","Tiruppur","Moradabad",
    "Jalandhar","Bhubaneswar","Salem","Warangal","Guntur","Bhiwandi","Saharanpur",
    "Gorakhpur","Bikaner","Amravati","Noida","Jamshedpur","Bhilai","Cuttack",
    "Firozabad","Kochi","Dehradun","Durgapur","Asansol","Nanded","Kolhapur",
    "Ajmer","Gulbarga","Jamnagar","Ujjain","Loni","Siliguri","Jhansi",
    "Ulhasnagar","Jammu","Sangli","Mangalore","Erode","Belgaum","Ambattur",
    "Tirunelveli","Malegaon","Gaya","Jalgaon","Udaipur","Maheshtala",
]

@app.route("/cities", methods=["GET"])
def cities():
    q = request.args.get("q", "").lower()
    if not q:
        return jsonify([])
    matches = [c for c in INDIAN_CITIES if q in c.lower()][:10]
    return jsonify(matches)

# ── Per-crop explanation (called when user clicks a result card) ──────────────
@app.route("/explain", methods=["POST"])
def explain():
    data = request.get_json()
    try:
        crop       = data["crop"]
        confidence = float(data["confidence"])
        N          = data["N"]
        P          = data["P"]
        K          = data["K"]
        temp       = data["temperature"]
        humidity   = data["humidity"]
        ph         = data["ph"]
        rainfall   = data["rainfall"]
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    explanation, is_gemini = get_gemini_explanation(
        crop, confidence, N, P, K, temp, humidity, ph, rainfall
    )
    return jsonify({"explanation": explanation, "gemini_powered": is_gemini})


# ── Soil improvement insight ──────────────────────────────────────────────────
def _local_soil_improvement(crop: str, soil: str, score: int, label: str) -> dict:
    """
    Rule-based soil improvement insight structured into 5 categories.
    Returns a dict with keys: problem, npk, water, amendments, techniques.
    """
    crop_l = crop.lower().strip()
    soil_l = soil.lower().strip().replace(" soil", "")

    # ── Problem analysis ──────────────────────────────────────────────────────
    problem_map = {
        ("rice",      "sandy"):  "Sandy soil drains water too quickly for rice cultivation, making it difficult to maintain the flooded conditions rice requires. The low nutrient retention also means essential minerals leach away before the crop can absorb them.",
        ("rice",      "clay"):   "Clay soil is naturally well-suited for rice. Its high water retention supports paddy conditions. Minor aeration improvements will maximise yield.",
        ("cotton",    "sandy"):  "Sandy soil lacks the moisture retention and nutrient density that cotton needs for strong boll development. Water stress during flowering can severely reduce yield.",
        ("wheat",     "clay"):   "Clay soil can become waterlogged, suffocating wheat roots and promoting fungal diseases. Drainage management is the primary concern.",
        ("sugarcane", "sandy"):  "Sandy soil cannot hold the large volumes of water sugarcane demands. Frequent irrigation is needed but water efficiency is poor without amendments.",
        ("maize",     "clay"):   "Clay soil compacts easily, restricting maize root penetration and reducing oxygen availability. Drainage and aeration are critical.",
        ("potato",    "clay"):   "Clay soil restricts tuber expansion and causes misshapen potatoes. Waterlogging also promotes rot diseases.",
        ("coffee",    "loamy"):  "Loamy soil is generally suitable for coffee but may need pH adjustment toward the slightly acidic range coffee prefers.",
    }
    default_problem = (
        f"{soil.title()} soil presents compatibility challenges for {crop} cultivation. "
        f"The current compatibility score of {score}% indicates that targeted soil improvements "
        f"are needed to achieve optimal yield. Addressing nutrient balance, water management, "
        f"and soil structure will significantly improve growing conditions."
    )
    problem = problem_map.get((crop_l, soil_l), default_problem)

    # ── NPK recommendations ───────────────────────────────────────────────────
    npk_map = {
        "sandy":    "Sandy soil is low in all nutrients. Apply urea (46-0-0) at 120–150 kg/ha for nitrogen. Use DAP (18-46-0) at 100 kg/ha for phosphorus. Apply MOP (0-0-60) at 80 kg/ha for potassium. Split nitrogen applications into 3 doses to reduce leaching.",
        "clay":     "Clay soil often has adequate potassium but may be deficient in phosphorus availability. Apply superphosphate at 80 kg/ha. Avoid excess nitrogen which promotes lush growth susceptible to disease. Use slow-release fertilizers to prevent runoff.",
        "loamy":    "Loamy soil has good nutrient retention. Apply balanced NPK 12-32-16 at 100 kg/ha as a base dose. Top-dress with urea at 50 kg/ha during vegetative growth. Potassium supplementation with SOP at 40 kg/ha improves fruit/grain quality.",
        "black":    "Black soil is naturally rich in calcium and magnesium. Focus on phosphorus (SSP at 100 kg/ha) and micronutrients like zinc sulfate at 25 kg/ha. Avoid excess nitrogen to prevent lodging.",
        "red":      "Red soil is deficient in nitrogen and phosphorus. Apply FYM at 10 tonnes/ha before sowing. Use urea at 100 kg/ha split in 3 doses. Apply SSP at 120 kg/ha for phosphorus. Zinc sulfate at 20 kg/ha corrects common micronutrient deficiency.",
        "alluvial": "Alluvial soil is fertile but benefits from balanced fertilization. Apply NPK 10-26-26 at 100 kg/ha as base. Top-dress nitrogen at 60 kg/ha. Micronutrient mix including boron and zinc improves crop quality.",
    }
    npk = npk_map.get(soil_l, f"Apply balanced NPK fertilizer based on soil test results. For {crop}, ensure adequate nitrogen for vegetative growth, phosphorus for root development, and potassium for stress resistance and yield quality. Conduct a soil test every 2 years to calibrate fertilizer doses.")

    # ── Water management ──────────────────────────────────────────────────────
    water_map = {
        "sandy":    "Install drip irrigation to deliver water directly to the root zone, reducing waste by 40–60%. Apply mulch (straw or plastic) 5–8 cm thick to reduce evaporation. Irrigate frequently in small doses rather than large infrequent applications. Consider sub-surface drip for row crops.",
        "clay":     "Install raised beds or ridge-and-furrow systems to improve drainage. Create drainage channels at 10–15 m intervals. Avoid irrigation within 48 hours of rain. Use furrow irrigation rather than flood irrigation to prevent waterlogging.",
        "loamy":    "Loamy soil has good water balance. Use sprinkler or drip irrigation for efficiency. Irrigate when soil moisture drops to 50% field capacity. Mulching reduces water requirement by 25–30%.",
        "black":    "Black soil has excellent moisture retention — avoid over-irrigation. Use deficit irrigation strategy. Irrigate at critical growth stages only (germination, flowering, grain filling). Ensure field drainage to prevent waterlogging during monsoon.",
        "red":      "Red soil drains quickly. Use drip irrigation with 2–3 daily cycles. Apply organic mulch to retain moisture. Construct farm ponds for water harvesting. Contour bunding on slopes reduces runoff.",
        "alluvial": "Alluvial soil has moderate water retention. Use canal or sprinkler irrigation. Maintain irrigation at 5–7 day intervals during dry periods. Avoid waterlogging in low-lying areas.",
    }
    water = water_map.get(soil_l, "Implement efficient irrigation based on crop water requirements. Monitor soil moisture regularly and irrigate at critical growth stages. Use mulching to conserve moisture and reduce irrigation frequency.")

    # ── Soil amendments ───────────────────────────────────────────────────────
    amendment_map = {
        "sandy":    "Add 15–20 tonnes/ha of farmyard manure (FYM) or compost to improve water retention and nutrient holding capacity. Incorporate 2–3 tonnes/ha of bentonite clay to improve soil structure. Apply vermicompost at 5 tonnes/ha for microbial activity. Green manuring with dhaincha or sunhemp before the main crop adds organic matter.",
        "clay":     "Add coarse sand or grit at 20–30% by volume to improve drainage and aeration. Incorporate organic matter (FYM at 10 tonnes/ha) to improve soil structure. Apply gypsum at 500 kg/ha to break clay hardpan and improve permeability. Lime application corrects acidity if pH < 6.0.",
        "loamy":    "Maintain organic matter with annual FYM application at 8–10 tonnes/ha. Add vermicompost at 3 tonnes/ha to sustain microbial diversity. Green manuring every 3 years maintains soil health. Minimal structural amendments needed.",
        "black":    "Apply organic matter to prevent cracking during dry periods. Use FYM at 8 tonnes/ha. Gypsum at 400 kg/ha improves soil structure. Avoid deep tillage which disrupts the natural soil profile.",
        "red":      "Heavy organic matter addition is essential. Apply FYM at 15 tonnes/ha. Use green manure crops. Add lime at 1–2 tonnes/ha to correct acidity. Phosphate-solubilizing bacteria (PSB) inoculants improve phosphorus availability.",
        "alluvial": "Maintain organic matter with FYM at 8 tonnes/ha. Crop rotation with legumes adds nitrogen naturally. Minimal structural amendments needed for well-managed alluvial soils.",
    }
    amendments = amendment_map.get(soil_l, f"Add organic matter through farmyard manure (8–12 tonnes/ha) to improve soil structure and nutrient availability. Consider green manuring before the {crop} crop. Conduct a soil health card analysis to identify specific deficiencies.")

    # ── Farming techniques ────────────────────────────────────────────────────
    technique_map = {
        "sandy":    f"Use raised bed farming to concentrate nutrients and moisture. Practice intercropping with legumes to fix nitrogen naturally. Apply mulching immediately after sowing. Consider conservation tillage to preserve organic matter. For {crop}, use shorter-duration varieties that complete their cycle before soil moisture is depleted.",
        "clay":     f"Practice deep ploughing (30–35 cm) once every 3 years to break hardpan. Use subsoil drainage tiles in severely waterlogged areas. Raised bed cultivation improves aeration for {crop}. Avoid field operations when soil is wet to prevent compaction.",
        "loamy":    f"Loamy soil supports most farming techniques. Practice crop rotation to maintain soil health. Minimum tillage preserves soil structure. Integrated nutrient management combining organic and inorganic fertilizers gives best results for {crop}.",
        "black":    f"Avoid deep tillage in black soil. Use conservation agriculture practices. Broad-bed furrow (BBF) system improves drainage and aeration. For {crop}, sow on ridges to avoid waterlogging during heavy rains.",
        "red":      f"Contour farming on slopes prevents erosion. Use stone bunds and check dams for water conservation. Mulching is critical for moisture retention. For {crop}, use drought-tolerant varieties and stress-tolerant rootstocks.",
        "alluvial": f"Alluvial soil supports intensive farming. Practice crop rotation with legumes. Use precision farming techniques for fertilizer optimization. For {crop}, follow recommended spacing and density for maximum yield.",
    }
    techniques = technique_map.get(soil_l, f"Implement integrated soil management combining organic amendments, balanced fertilization, and efficient irrigation. Practice crop rotation to break pest cycles and improve soil health. Use soil health card recommendations for site-specific management of {crop}.")

    return {
        "problem":    problem,
        "npk":        npk,
        "water":      water,
        "amendments": amendments,
        "techniques": techniques,
    }


def get_gemini_soil_improvement(crop: str, soil: str, score: int, label: str) -> tuple[dict, bool]:
    """
    Returns (improvement_dict, is_gemini_powered).
    improvement_dict has keys: problem, npk, water, amendments, techniques.
    """
    prompt = (
        f"You are an expert agricultural soil scientist. A farmer wants to grow {crop} on {soil} soil. "
        f"The AI compatibility score is {score}% ({label}). "
        f"Provide a detailed soil improvement plan in exactly this JSON format with no extra text:\n"
        f'{{"problem":"2-3 sentences on why this soil is not ideal for {crop}","npk":"specific NPK fertilizer recommendations with doses","water":"irrigation and water management suggestions","amendments":"organic and inorganic soil amendment recommendations","techniques":"farming techniques to improve compatibility"}}\n'
        f"Be specific, practical, and farmer-friendly. Use actual product names and quantities."
    )
    try:
        resp = requests.post(
            GEMINI_URL,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=12,
        )
        if resp.status_code == 200:
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            # Validate all keys present
            required = {"problem", "npk", "water", "amendments", "techniques"}
            if required.issubset(parsed.keys()):
                return parsed, True
    except Exception:
        pass
    return _local_soil_improvement(crop, soil, score, label), False


@app.route("/soil-improvement", methods=["POST"])
def soil_improvement():
    data = request.get_json()
    crop  = data.get("crop",  "").strip()
    soil  = data.get("soil",  "").strip()
    score = int(data.get("score", 50))
    label = data.get("label", "Moderate").strip()

    if not crop or not soil:
        return jsonify({"error": "Crop and soil are required."}), 400

    improvement, is_gemini = get_gemini_soil_improvement(crop, soil, score, label)
    return jsonify({
        "improvement":   improvement,
        "gemini_powered": is_gemini,
    })

# ── Land Planning & Yield Estimation ─────────────────────────────────────────

# Per-crop data: seed_kg_per_ha, water_mm_per_season, yield_tonnes_per_ha,
#                npk_kg_per_ha (N, P, K), notes
CROP_YIELD_DATA = {
    "rice":        {"seed": 50,  "water": 1200, "yield": 4.5,  "N": 120, "P": 60,  "K": 60,  "unit": "tonnes", "season": "120–150 days"},
    "maize":       {"seed": 20,  "water": 600,  "yield": 5.5,  "N": 150, "P": 75,  "K": 75,  "unit": "tonnes", "season": "90–120 days"},
    "wheat":       {"seed": 100, "water": 450,  "yield": 3.5,  "N": 120, "P": 60,  "K": 40,  "unit": "tonnes", "season": "120–150 days"},
    "cotton":      {"seed": 15,  "water": 700,  "yield": 2.0,  "N": 100, "P": 50,  "K": 50,  "unit": "tonnes", "season": "150–180 days"},
    "sugarcane":   {"seed": 8000,"water": 1800, "yield": 70.0, "N": 250, "P": 100, "K": 120, "unit": "tonnes", "season": "12–18 months"},
    "banana":      {"seed": 2500,"water": 1200, "yield": 35.0, "N": 200, "P": 60,  "K": 300, "unit": "tonnes", "season": "10–12 months"},
    "chickpea":    {"seed": 60,  "water": 350,  "yield": 1.5,  "N": 20,  "P": 60,  "K": 30,  "unit": "tonnes", "season": "90–110 days"},
    "kidneybeans": {"seed": 80,  "water": 400,  "yield": 1.2,  "N": 20,  "P": 50,  "K": 30,  "unit": "tonnes", "season": "80–100 days"},
    "pigeonpeas":  {"seed": 15,  "water": 500,  "yield": 1.0,  "N": 20,  "P": 50,  "K": 30,  "unit": "tonnes", "season": "150–180 days"},
    "mothbeans":   {"seed": 10,  "water": 300,  "yield": 0.8,  "N": 15,  "P": 40,  "K": 20,  "unit": "tonnes", "season": "70–90 days"},
    "mungbean":    {"seed": 15,  "water": 350,  "yield": 1.0,  "N": 20,  "P": 40,  "K": 20,  "unit": "tonnes", "season": "60–75 days"},
    "blackgram":   {"seed": 15,  "water": 350,  "yield": 0.9,  "N": 20,  "P": 40,  "K": 20,  "unit": "tonnes", "season": "70–90 days"},
    "lentil":      {"seed": 40,  "water": 300,  "yield": 1.0,  "N": 20,  "P": 50,  "K": 20,  "unit": "tonnes", "season": "90–120 days"},
    "pomegranate": {"seed": 400, "water": 600,  "yield": 12.0, "N": 100, "P": 50,  "K": 100, "unit": "tonnes", "season": "5–7 months"},
    "mango":       {"seed": 100, "water": 800,  "yield": 10.0, "N": 100, "P": 50,  "K": 100, "unit": "tonnes", "season": "4–5 months"},
    "grapes":      {"seed": 1200,"water": 700,  "yield": 15.0, "N": 100, "P": 60,  "K": 120, "unit": "tonnes", "season": "6–8 months"},
    "watermelon":  {"seed": 2,   "water": 500,  "yield": 25.0, "N": 80,  "P": 40,  "K": 80,  "unit": "tonnes", "season": "70–90 days"},
    "muskmelon":   {"seed": 2,   "water": 450,  "yield": 18.0, "N": 80,  "P": 40,  "K": 80,  "unit": "tonnes", "season": "70–90 days"},
    "apple":       {"seed": 200, "water": 900,  "yield": 20.0, "N": 80,  "P": 40,  "K": 80,  "unit": "tonnes", "season": "5–6 months"},
    "orange":      {"seed": 150, "water": 900,  "yield": 15.0, "N": 80,  "P": 40,  "K": 80,  "unit": "tonnes", "season": "7–8 months"},
    "papaya":      {"seed": 0.5, "water": 1000, "yield": 40.0, "N": 200, "P": 100, "K": 200, "unit": "tonnes", "season": "9–11 months"},
    "coconuttree": {"seed": 80,  "water": 1200, "yield": 15000,"N": 100, "P": 40,  "K": 200, "unit": "nuts",   "season": "12 months"},
    "jute":        {"seed": 5,   "water": 1000, "yield": 2.5,  "N": 60,  "P": 30,  "K": 30,  "unit": "tonnes", "season": "100–120 days"},
    "coffee":      {"seed": 400, "water": 1200, "yield": 1.5,  "N": 100, "P": 30,  "K": 100, "unit": "tonnes", "season": "9–11 months"},
    "tomato":      {"seed": 0.3, "water": 600,  "yield": 25.0, "N": 120, "P": 60,  "K": 120, "unit": "tonnes", "season": "90–120 days"},
    "potato":      {"seed": 1500,"water": 500,  "yield": 20.0, "N": 120, "P": 80,  "K": 120, "unit": "tonnes", "season": "90–120 days"},
}

HA_PER_ACRE = 0.404686   # 1 acre = 0.404686 ha

def _local_yield_insight(crop: str, area: float, unit: str, data: dict) -> str:
    ha = area if unit == "hectare" else area * HA_PER_ACRE
    area_label = f"{area} {'acre' if unit == 'acre' else 'hectare'}{'s' if area != 1 else ''}"
    yield_est  = round(data["yield"] * ha, 1)
    water_est  = round(data["water"] * ha)
    seed_est   = round(data["seed"] * ha, 1)
    N_est = round(data["N"] * ha); P_est = round(data["P"] * ha); K_est = round(data["K"] * ha)

    return (
        f"For {area_label} of {crop} cultivation, you will need approximately {seed_est} kg of seeds "
        f"and {water_est} mm of water over the {data['season']} growing season. "
        f"Apply nitrogen at {N_est} kg, phosphorus at {P_est} kg, and potassium at {K_est} kg "
        f"split across basal and top-dress applications. "
        f"Expected yield is {yield_est} {data['unit']} under good management practices. "
        f"Use drip or sprinkler irrigation to improve water-use efficiency by 30–40%. "
        f"Timely pest scouting and integrated nutrient management will help achieve maximum yield potential."
    )


def get_gemini_yield_insight(crop: str, area: float, unit: str, estimates: dict) -> tuple[str, bool]:
    area_label = f"{area} {'acre' if unit == 'acre' else 'hectare'}{'s' if area != 1 else ''}"
    prompt = (
        f"You are an expert agricultural advisor. A farmer wants to cultivate {crop} on {area_label}. "
        f"The estimated requirements are: Seeds={estimates['seed_req']} kg, "
        f"Water={estimates['water_req']} mm/season, "
        f"Fertilizer N={estimates['N_kg']} kg, P={estimates['P_kg']} kg, K={estimates['K_kg']} kg, "
        f"Expected yield={estimates['yield_est']} {estimates['yield_unit']}. "
        f"Write 3-4 practical sentences covering: irrigation schedule, yield improvement tips, "
        f"fertilizer application timing, and one key farming recommendation specific to {crop}. "
        f"Be specific and farmer-friendly."
    )
    try:
        resp = requests.post(
            GEMINI_URL,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=10,
        )
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text, True
    except Exception:
        pass
    return _local_yield_insight(crop, area, unit, CROP_YIELD_DATA.get(crop.lower(), CROP_YIELD_DATA["rice"])), False


@app.route("/yield-estimate", methods=["POST"])
def yield_estimate():
    data  = request.get_json()
    crop  = data.get("crop",  "").strip().lower()
    area  = float(data.get("area",  1))
    unit  = data.get("unit",  "acre").lower()   # "acre" or "hectare"

    if not crop:
        return jsonify({"error": "Crop name is required."}), 400
    if area <= 0:
        return jsonify({"error": "Area must be greater than 0."}), 400

    # Lookup crop data (fuzzy match)
    crop_data = None
    for key in CROP_YIELD_DATA:
        if key in crop or crop in key:
            crop_data = CROP_YIELD_DATA[key]
            crop = key   # normalise
            break
    if not crop_data:
        # Generic fallback
        crop_data = {"seed": 30, "water": 600, "yield": 3.0, "N": 100, "P": 50, "K": 50,
                     "unit": "tonnes", "season": "90–120 days"}

    ha = area if unit == "hectare" else area * HA_PER_ACRE

    estimates = {
        "seed_req":   round(crop_data["seed"] * ha, 1),
        "water_req":  round(crop_data["water"] * ha),
        "N_kg":       round(crop_data["N"] * ha),
        "P_kg":       round(crop_data["P"] * ha),
        "K_kg":       round(crop_data["K"] * ha),
        "yield_est":  round(crop_data["yield"] * ha, 1),
        "yield_unit": crop_data["unit"],
        "season":     crop_data["season"],
        "area_ha":    round(ha, 3),
    }

    insight, is_gemini = get_gemini_yield_insight(crop, area, unit, estimates)

    return jsonify({
        "crop":         crop.title(),
        "area":         area,
        "unit":         unit,
        "estimates":    estimates,
        "insight":      insight,
        "gemini_powered": is_gemini,
    })


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
