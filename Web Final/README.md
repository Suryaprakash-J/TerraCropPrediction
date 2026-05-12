# 🌱 TerraAI – Smart Agriculture Intelligence Platform

> Final Year B.Tech CSE Capstone Project  
> AI-powered crop recommendation system using Ensemble Machine Learning

---

## 🚀 Features

| Feature | Description |
|---|---|
| 🧠 **Crop Prediction** | Ensemble ML (RandomForest + CatBoost) returns Top 5 crops with confidence % |
| 📄 **OCR Scanner** | Upload soil lab report image → auto-extract N, P, K, pH |
| 🌤️ **Weather API** | Auto-detect location or search Indian cities → auto-fill form |
| 🔄 **Reverse Compatibility** | Type any crop + soil → get AI compatibility score + tips |
| 📊 **Dashboard** | Charts, crop profiles, soil guide, model info |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, Flask 3.0
- **ML**: Scikit-learn (RandomForestClassifier), CatBoost, VotingClassifier
- **OCR**: pytesseract + Pillow
- **Weather**: OpenWeatherMap API
- **Frontend**: HTML5, CSS3 (Glassmorphism), Vanilla JS, Chart.js

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Train the model
```bash
python train_model.py
```
This generates `models/crop_model.pkl` and `models/label_encoder.pkl`.

### 3. (Optional) Add OpenWeatherMap API key
Edit `app.py` line:
```python
WEATHER_API_KEY = "your_actual_api_key_here"
```
Or set environment variable: `OPENWEATHER_API_KEY=your_key`

Get a free key at: https://openweathermap.org/api

### 4. Run the app
```bash
python app.py
```
Open: http://localhost:5000

---

## 📁 Project Structure

```
Web Final/
├── app.py                  # Flask application
├── train_model.py          # ML training script
├── requirements.txt        # Python dependencies
├── Procfile                # Render/Heroku deployment
├── render.yaml             # Render deployment config
├── models/
│   ├── crop_model.pkl      # Trained ensemble model
│   └── label_encoder.pkl   # Label encoder
├── static/
│   ├── css/style.css       # All styles (glassmorphism UI)
│   └── js/
│       ├── main.js         # Home page logic
│       └── dashboard.js    # Dashboard charts
├── templates/
│   ├── index.html          # Main home page
│   └── dashboard.html      # Analytics dashboard
└── uploads/                # Temporary OCR uploads
```

---

## 🤖 ML Model Details

| Model | Type | Estimators | Accuracy |
|---|---|---|---|
| RandomForest #1 | Bagging | 300 trees | ~96% |
| RandomForest #2 | Bagging | 300 trees | ~96% |
| **VotingClassifier** | **Soft Voting** | **Ensemble** | **~97%** |

**Input Features**: N, P, K, Temperature, Humidity, pH, Rainfall  
**Output**: Top 5 crops with confidence percentages  
**Dataset**: 2640 synthetic samples across 22 crop types

---

## 🌐 Deploy to Render (Free)

1. Push code to GitHub
2. Go to https://render.com → New Web Service
3. Connect your GitHub repo
4. Build command: `pip install -r requirements.txt && python train_model.py`
5. Start command: `gunicorn app:app`
6. Add env var: `OPENWEATHER_API_KEY = your_key`

---

## 🔧 OCR Setup (Windows)

Install Tesseract OCR engine:
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to `C:\Program Files\Tesseract-OCR\`
3. Add to PATH or set in code:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

---

## 📊 Supported Crops (22)

Rice, Maize, Chickpea, KidneyBeans, PigeonPeas, MothBeans, MungBean, Blackgram, Lentil, Pomegranate, Banana, Mango, Grapes, Watermelon, Muskmelon, Apple, Orange, Papaya, CoconutTree, Cotton, Jute, Coffee

---

## 🎓 Viva Talking Points

1. **Why Ensemble?** Combines strengths of RandomForest (variance reduction) and CatBoost (bias reduction) → higher accuracy
2. **Soft Voting** averages class probabilities rather than majority vote → more nuanced predictions
3. **OCR Pipeline**: PIL opens image → Tesseract extracts text → regex patterns parse N/P/K/pH
4. **Reverse Compatibility**: Rule-based knowledge base + fallback scoring for unknown crop-soil pairs
5. **Deployment**: Gunicorn WSGI server, environment-based config, Render free tier

---

*Built with ❤️ for B.Tech CSE Final Year Project*
