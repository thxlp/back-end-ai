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
current_model_name = None

# รายการไฟล์ model ทั้งหมดที่มีอยู่
model_configs = [
    {
        'name': 'best_logisticregression',
        'model_path': 'best_logisticregression_model.joblib',
        'vectorizer_path': 'best_logisticregression_vectorizer.joblib'
    },
    {
        'name': 'fallback',
        'model_path': 'fallback_model.joblib',
        'vectorizer_path': 'fallback_vectorizer.joblib'
    },
    {
        'name': 'phishing_detector_updated',
        'model_path': 'phishing_detector_updated.joblib',
        'vectorizer_path': 'tfidf_vectorizer_updated.joblib'
    }
]

# โหลดโมเดลและ Vectorizer จากไฟล์
def load_model_with_fallback():
    global model, tfidf_vectorizer, current_model_name
    
    # ลองโหลดทุกไฟล์ model ตามลำดับ
    for config in model_configs:
        model_path = config['model_path']
        vectorizer_path = config['vectorizer_path']
        model_name = config['name']
        
        try:
            if os.path.exists(model_path) and os.path.exists(vectorizer_path):
                print(f"Attempting to load {model_name} model...")
                print(f"Model file: {model_path}")
                print(f"Vectorizer file: {vectorizer_path}")
                
                model = joblib.load(model_path)
                tfidf_vectorizer = joblib.load(vectorizer_path)
                current_model_name = model_name
                
                print(f"✅ {model_name} model loaded successfully!")
                print(f"Model type: {type(model)}")
                print(f"Vectorizer type: {type(tfidf_vectorizer)}")
                
                # ทดสอบว่า model ทำงานได้หรือไม่
                try:
                    test_text = "test email content"
                    test_processed = preprocess_text(test_text)
                    test_vector = tfidf_vectorizer.transform([test_processed])
                    test_prediction = model.predict(test_vector)
                    test_proba = model.predict_proba(test_vector)
                    print(f"✅ Model test successful - prediction: {test_prediction[0]}")
                    return True
                except Exception as test_error:
                    print(f"❌ Model test failed: {test_error}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error loading {model_name} model: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print("❌ All model loading attempts failed.")
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
    print(f"Original content: {email_content[:100]}...")
    print(f"Processed content: {processed_content}")
    
    vectorized_content = tfidf_vectorizer.transform([processed_content])
    print(f"Vector shape: {vectorized_content.shape}")
    print(f"Non-zero features: {vectorized_content.nnz}")
    
    prediction = model.predict(vectorized_content)[0]
    prediction_proba = model.predict_proba(vectorized_content)[0].tolist()
    print(f"Raw prediction: {prediction}")
    print(f"Raw probabilities: {prediction_proba}")
    
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
        "risk_level": risk_level,
        "model_used": current_model_name or "unknown",
        "debug_info": {
            "original_length": len(email_content),
            "processed_length": len(processed_content),
            "vector_features": vectorized_content.nnz,
            "raw_prediction": int(prediction),
            "raw_probabilities": prediction_proba
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

    