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

# Small version tag to help confirm which code is running when debugging
APP_VERSION = "2025-09-26-1"

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

models_available = []  # list of dicts: {name, model, vectorizer, vocab_size}
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
    """Load all model configs that can be loaded and tested. Store in models_available."""
    global models_available, current_model_name
    models_available = []

    for config in model_configs:
        model_path = config['model_path']
        vectorizer_path = config['vectorizer_path']
        model_name = config['name']
        try:
            if os.path.exists(model_path) and os.path.exists(vectorizer_path):
                print(f"Attempting to load {model_name} model...")
                m = joblib.load(model_path)
                v = joblib.load(vectorizer_path)
                # determine vocab size
                try:
                    if hasattr(v, 'get_feature_names_out'):
                        vocab_size = len(v.get_feature_names_out())
                    elif hasattr(v, 'vocabulary_'):
                        vocab_size = len(v.vocabulary_)
                    else:
                        vocab_size = -1
                except Exception:
                    vocab_size = -1

                # quick test transform
                try:
                    test_text = "test email content"
                    test_processed = preprocess_text(test_text)
                    tv = v.transform([test_processed])
                    _ = m.predict(tv)
                    _ = m.predict_proba(tv)
                    models_available.append({
                        'name': model_name,
                        'model': m,
                        'vectorizer': v,
                        'vocab_size': vocab_size
                    })
                    print(f"✅ {model_name} loaded (vocab={vocab_size})")
                except Exception as te:
                    print(f"❌ {model_name} loaded but test transform failed: {te}")
                    continue
        except Exception as e:
            print(f"❌ Error loading {model_name}: {e}")
            continue

    if models_available:
        # choose a default primary model (largest vocab) for display
        primary = max(models_available, key=lambda x: x.get('vocab_size', -1))
        current_model_name = primary['name']
        return True
    else:
        print("❌ No models available after loading attempts.")
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
    # Try to reload models if none loaded
    if not models_available:
        print("No models loaded, attempting to reload...")
        if not load_model_with_fallback():
            return jsonify({"error": "No models available. Server error."}), 500
    
    data = request.get_json()
    email_content = data.get('email_content')
    
    if not email_content:
        return jsonify({"error": "'email_content' not provided in request body."}), 400
    
    print(f"Original content: {email_content[:100]}...")
    processed_content = preprocess_text(email_content)
    print(f"Processed content: {processed_content}")

    # Evaluate each loaded model and pick the best candidate
    raw_text = (email_content or '')
    best = None

    for entry in models_available:
        m_name = entry['name']
        m = entry['model']
        v = entry['vectorizer']
        used_processed_fallback_local = False
        overlap_local = None
        vector_local = None

        def try_transform_local(name, text):
            try:
                vv = v.transform([text])
                print(f"[{m_name}] Vector shape ({name}): {vv.shape}")
                print(f"[{m_name}] Non-zero features ({name}): {vv.nnz}")
                return vv
            except Exception as e:
                print(f"[{m_name}] {name} vectorization error: {e}")
                return None

        # 1) raw
        vector_local = try_transform_local('raw', raw_text)

        # 2) processed
        if vector_local is None or getattr(vector_local, 'nnz', 0) == 0:
            processed_vector = try_transform_local('processed', processed_content)
            if processed_vector is not None and getattr(processed_vector, 'nnz', 0) > 0:
                vector_local = processed_vector
                used_processed_fallback_local = True

        # 3) analyzer filtered
        try:
            vocab = None
            if hasattr(v, 'vocabulary_'):
                vocab = set(v.vocabulary_.keys())

            analyzer_fn = None
            if hasattr(v, 'build_analyzer'):
                try:
                    analyzer_fn = v.build_analyzer()
                except Exception:
                    analyzer_fn = None

            tokens_raw = analyzer_fn(raw_text) if analyzer_fn else []
            tokens_processed = analyzer_fn(processed_content) if analyzer_fn else []
            tokens = tokens_raw or tokens_processed or []

            if tokens:
                overlap_local = len(set(tokens) & (vocab or set())) if vocab is not None else -1
                print(f"[{m_name}] Analyzer tokens count: {len(tokens)}, overlap with vocab: {overlap_local}")
                if vocab:
                    filtered = [t for t in tokens if t in vocab]
                else:
                    filtered = tokens
                if filtered and (vector_local is None or getattr(vector_local, 'nnz', 0) == 0):
                    token_text = ' '.join(filtered)
                    token_vector = try_transform_local('analyzer_filtered', token_text)
                    if token_vector is not None and getattr(token_vector, 'nnz', 0) > 0:
                        vector_local = token_vector
        except Exception as e:
            print(f"[{m_name}] Analyzer/vocab debug failed: {e}")

        # 4) simple tokens
        if vector_local is None or getattr(vector_local, 'nnz', 0) == 0:
            try:
                simple_tokens = re.findall(r"[A-Za-z\u0E00-\u0E7F]+", processed_content)
                print(f"[{m_name}] Simple tokens count: {len(simple_tokens)}")
                if simple_tokens:
                    simple_text = ' '.join(simple_tokens)
                    simple_vector = try_transform_local('simple', simple_text)
                    if simple_vector is not None and getattr(simple_vector, 'nnz', 0) > 0:
                        vector_local = simple_vector
                        used_processed_fallback_local = True
            except Exception as e:
                print(f"[{m_name}] Simple tokenization fallback failed: {e}")

        if vector_local is None:
            vector_local = try_transform_local('empty', '')

        # get prediction/proba for this model (wrap safe)
        pred = None
        proba = None
        try:
            pred = int(m.predict(vector_local)[0])
            proba = m.predict_proba(vector_local)[0].tolist()
            print(f"[{m_name}] Raw prediction: {pred}")
            print(f"[{m_name}] Raw probabilities: {proba}")
        except Exception as e:
            print(f"[{m_name}] Prediction failed: {e}")

        nnz = getattr(vector_local, 'nnz', 0)

        candidate = {
            'name': m_name,
            'model': m,
            'vectorizer': v,
            'vector': vector_local,
            'nnz': nnz,
            'used_processed_fallback': used_processed_fallback_local,
            'analyzer_overlap': overlap_local,
            'prediction': pred,
            'proba': proba
        }

        # choose best by nnz then phishing prob
        if best is None:
            best = candidate
        else:
            if candidate['nnz'] > best['nnz']:
                best = candidate
            elif candidate['nnz'] == best['nnz']:
                # tie-breaker: higher phishing probability
                cand_phish = (candidate['proba'][1] if candidate['proba'] and len(candidate['proba'])>1 else (candidate['proba'][0] if candidate['proba'] else 0))
                best_phish = (best['proba'][1] if best['proba'] and len(best['proba'])>1 else (best['proba'][0] if best['proba'] else 0))
                if cand_phish > best_phish:
                    best = candidate

    # If still no meaningful features (nnz==0), apply simple keyword heuristic
    if best is None:
        return jsonify({"error": "No model candidates available."}), 500

    # Ensure chosen is always defined for response building
    chosen = best

    # If the best candidate has no non-zero features, use heuristic fallback
    if best.get('nnz', 0) == 0:
        keywords_en = ['verify', 'password', 'click', 'account', 'suspended', 'urgent', 'login', 'confirm']
        keywords_th = ['ยืนยัน', 'รหัส', 'บัญชี', 'คลิก', 'ยกเลิก', 'แจ้งเตือน', 'ยืนยันตัว', 'ยืนยันอีเมล']
        text_lower = processed_content.lower()
        matches_en = sum(1 for k in keywords_en if k in text_lower)
        matches_th = sum(1 for k in keywords_th if k in text_lower)
        matches = matches_en + matches_th
        if matches >= 2:
            heuristic_prob = 0.85
        elif matches == 1:
            heuristic_prob = 0.6
        else:
            heuristic_prob = 0.25
        prediction = 1 if heuristic_prob >= 0.5 else 0
        prediction_proba = [1-heuristic_prob, heuristic_prob]
        model_used_name = 'heuristic_fallback'
        print(f"Heuristic fallback used (en_matches={matches_en}, th_matches={matches_th}) -> prob={heuristic_prob}")
    else:
        prediction = chosen['prediction']
        prediction_proba = chosen['proba'] or [0, 0]
        model_used_name = chosen['name']
    
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
        "model_used": model_used_name,
        "debug_info": {
            "original_length": len(email_content),
            "processed_length": len(processed_content),
            "vector_features": getattr(chosen.get('vector'), 'nnz', 0) if chosen else 0,
            "used_processed_fallback": chosen.get('used_processed_fallback') if chosen else False,
            "analyzer_overlap": chosen.get('analyzer_overlap') if chosen else None,
            "raw_prediction": int(prediction),
            "raw_probabilities": prediction_proba,
            "heuristic_used": (model_used_name == 'heuristic_fallback')
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

    