from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Simple health check
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "message": "Phishing Detection API is running"
    })

# Simple prediction endpoint (always returns safe for now)
@app.route('/predict_phishing', methods=['POST'])
def predict_phishing():
    data = request.get_json()
    email_content = data.get('email_content', '')
    
    if not email_content:
        return jsonify({"error": "'email_content' not provided in request body."}), 400
    
    # Simple rule-based detection for now
    suspicious_keywords = ['urgent', 'click here', 'verify', 'suspended', 'password', 'account']
    email_lower = email_content.lower()
    
    suspicious_count = sum(1 for keyword in suspicious_keywords if keyword in email_lower)
    
    if suspicious_count >= 2:
        result = "Phishing"
        confidence = 0.8
        risk_level = "High risk"
    elif suspicious_count >= 1:
        result = "Phishing" 
        confidence = 0.6
        risk_level = "Medium risk"
    else:
        result = "Not Phishing"
        confidence = 0.3
        risk_level = "Low risk"
    
    return jsonify({
        "prediction": result,
        "confidence": f"{confidence:.4f}",
        "risk_level": risk_level
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
