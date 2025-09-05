from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import re
import string
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import os

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ตรวจสอบและดาวน์โหลดทรัพยากร NLTK ที่จำเป็น
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4', quiet=True)

# ฟังก์ชันสำหรับประมวลผลข้อความ
def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'<.*?>+', '', text)
    text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub(r'\n', '', text)
    text = re.sub(r'\w*\d\w*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    stop_words = set(stopwords.words('english'))
    text = ' '.join([word for word in text.split() if word not in stop_words])
    lemmatizer = WordNetLemmatizer()
    text = ' '.join([lemmatizer.lemmatize(word) for word in text.split()])
    return text

model = None
tfidf_vectorizer = None
model_path = 'phishing_detector_updated.joblib'
vectorizer_path = 'tfidf_vectorizer_updated.joblib'

# โหลดโมเดลและ Vectorizer จากไฟล์
try:
    if os.path.exists(model_path) and os.path.exists(vectorizer_path):
        model = joblib.load(model_path)
        tfidf_vectorizer = joblib.load(vectorizer_path)
        print("Model and vectorizer loaded successfully.")
    else:
        print("Model or vectorizer files not found. Please ensure they are in the same directory.")
except Exception as e:
    print(f"Error loading model or vectorizer: {e}")

# Health Check Endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Phishing Detection API is running"})

# Prediction Endpoint
@app.route('/predict_phishing', methods=['POST'])
def predict_phishing():
    if model is None or tfidf_vectorizer is None:
        return jsonify({"error": "Model or vectorizer not loaded. Server error."}), 500
    
    data = request.get_json()
    email_content = data.get('email_content')
    
    if not email_content:
        return jsonify({"error": "'email_content' not provided in request body."}), 400
    
    processed_content = preprocess_text(email_content)
    vectorized_content = tfidf_vectorizer.transform([processed_content])
    
    prediction = model.predict(vectorized_content)[0]
    prediction_proba = model.predict_proba(vectorized_content)[0].tolist()
    
    # กำหนดผลลัพธ์จากค่าทำนาย
    # คุณต้องแน่ใจว่าค่า 0 และ 1 ตรงกับ 'Not Phishing' และ 'Phishing'
    # ในกรณีที่คุณได้ผลลัพธ์ 0 และ 1
    # หากคุณมี 4 คลาส (0, 1, 2, 3) ต้องกำหนดการแสดงผลให้เหมาะสม
    # หากผลลัพธ์เป็น 0 และ 1 สามารถใช้การเช็คแบบนี้ได้
    result = "Phishing" if prediction == 1 else "Not Phishing"
    
    # กำหนดค่าความน่าเชื่อถือและความเสี่ยง
    confidence_phishing = prediction_proba[1] if len(prediction_proba) > 1 else prediction_proba[0]
    
    if confidence_phishing >= 0.8:
        risk_level = "High risk"
    elif confidence_phishing >= 0.5:
        risk_level = "Medium risk"
    else:
        risk_level = "Low risk"
        
    return jsonify({
        "prediction": result,
        "confidence": f"{confidence_phishing:.4f}",
        "risk_level": risk_level
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)