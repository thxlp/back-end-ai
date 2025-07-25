# Phishing Detection API

API สำหรับตรวจจับอีเมลฟิชชิ่งโดยใช้ Machine Learning

## Features
- ตรวจจับอีเมลฟิชชิ่งด้วย Machine Learning
- ประเมินระดับความเสี่ยง (High, Medium, Low)
- API ที่เรียกใช้งานง่าย

## API Endpoints

### Health Check
```
GET /
```

### Predict Phishing
```
POST /predict_phishing
Content-Type: application/json

{
  "email_content": "Your email content here"
}
```

Response:
```json
{
  "prediction": "Phishing" | "Not Phishing",
  "confidence": "0.8500",
  "risk_level": "High risk" | "Medium risk" | "Low risk"
}
```

## Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python app.py`

## Railway Deployment
This app is configured for Railway deployment with:
- `requirements.txt` - Python dependencies
- `Procfile` - Process definition
- `runtime.txt` - Python version
- `railway.json` - Railway configuration 