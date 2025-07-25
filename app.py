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
model_path = 'phishing_detector_model.pkl'
vectorizer_path = 'tfidf_vectorizer.pkl'
if os.path.exists(model_path) and os.path.exists(vectorizer_path):
    model = joblib.load(model_path)
    tfidf_vectorizer = joblib.load(vectorizer_path)


@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Phishing Detection API is running"})

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
    result = "Phishing" if prediction == 1 else "Not Phishing"
    confidence_phishing = prediction_proba[1]
    # Risk level logic
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