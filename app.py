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

# ตรวจสอบทรัพยากร NLTK ที่จำเป็นแบบไม่พยายามดาวน์โหลด (เพื่อให้สตาร์ทเร็วขึ้นบน Railway)
has_stopwords = False
has_wordnet = False
try:
    nltk.data.find('corpora/stopwords')
    has_stopwords = True
except LookupError:
    has_stopwords = False
try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/omw-1.4')
    has_wordnet = True
except LookupError:
    has_wordnet = False

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
    if has_stopwords:
        stop_words = set(stopwords.words('english'))
        text = ' '.join([word for word in text.split() if word not in stop_words])
    if has_wordnet:
        lemmatizer = WordNetLemmatizer()
        text = ' '.join([lemmatizer.lemmatize(word) for word in text.split()])
    return text

model = None
tfidf_vectorizer = None
model_path = 'best_logisticregression_model.joblib'
vectorizer_path = 'best_logisticregression_vectorizer.joblib'

# โหลดโมเดลและ Vectorizer จากไฟล์
def load_model_with_fallback():
    global model, tfidf_vectorizer
    
    # Try loading the main model files
    try:
        if os.path.exists(model_path) and os.path.exists(vectorizer_path):
            print(f"Loading model from: {model_path}")
            print(f"Loading vectorizer from: {vectorizer_path}")
            model = joblib.load(model_path)
            tfidf_vectorizer = joblib.load(vectorizer_path)
            print("Model and vectorizer loaded successfully.")
            print(f"Model type: {type(model)}")
            print(f"Vectorizer type: {type(tfidf_vectorizer)}")
            return True
    except Exception as e:
        print(f"Error loading main model: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
    
    # Fallback: try old model files
    try:
        old_model_path = 'phishing_detector_updated.joblib'
        old_vectorizer_path = 'tfidf_vectorizer_updated.joblib'
        if os.path.exists(old_model_path) and os.path.exists(old_vectorizer_path):
            print("Trying fallback model files...")
            model = joblib.load(old_model_path)
            tfidf_vectorizer = joblib.load(old_vectorizer_path)
            print("Fallback model loaded successfully.")
            return True
    except Exception as e:
        print(f"Error loading fallback model: {e}")
    
    # Final fallback: try simple fallback model
    try:
        fallback_model_path = 'fallback_model.joblib'
        fallback_vectorizer_path = 'fallback_vectorizer.joblib'
        if os.path.exists(fallback_model_path) and os.path.exists(fallback_vectorizer_path):
            print("Trying simple fallback model...")
            model = joblib.load(fallback_model_path)
            tfidf_vectorizer = joblib.load(fallback_vectorizer_path)
            print("Simple fallback model loaded successfully.")
            return True
    except Exception as e:
        print(f"Error loading simple fallback model: {e}")
    
    print("All model loading attempts failed.")
    return False

# Load model on startup (async to avoid blocking)
import threading
def load_model_async():
    try:
        load_model_with_fallback()
    except Exception as e:
        print(f"Background model loading failed: {e}")

# Start model loading in background thread
threading.Thread(target=load_model_async, daemon=True).start()

# Health Check Endpoint - Always return healthy immediately
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "message": "Phishing Detection API is running"
    })

# Prediction Endpoint
@app.route('/predict_phishing', methods=['POST'])
def predict_phishing():
    # Try to reload model if not loaded
    if model is None or tfidf_vectorizer is None:
        print("Model not loaded, attempting to reload...")
        if not load_model_with_fallback():
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