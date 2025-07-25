document.addEventListener('DOMContentLoaded', () => {
    const scanButton = document.getElementById('scanButton');
    const resultDiv = document.getElementById('result');
    function resetResult() {
        resultDiv.textContent = "Scanning...";
        resultDiv.className = '';
    }
    scanButton.addEventListener('click', () => {
        resetResult();
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { type: "scan_email" }, (response) => {
                    // Handle response or ignore if no response needed
                    if (chrome.runtime.lastError) {
                        console.log("Message sending error:", chrome.runtime.lastError.message);
                        resultDiv.textContent = "Extension error: " + chrome.runtime.lastError.message;
                        resultDiv.className = 'error';
                    }
                });
            } else {
                resultDiv.textContent = "No active tab found or insufficient permissions.";
                resultDiv.className = 'error';
            }
        });
    });
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === "phishing_result") {
            const result = message.result;
            let displayConfidence = '';
            if (result.confidence) {
                const confidenceValue = parseFloat(result.confidence);
                if (!isNaN(confidenceValue)) {
                    displayConfidence = ` (Confidence: ${(confidenceValue * 100).toFixed(2)}%)`;
                }
            }
            let riskLevel = result.risk_level ? `\n\nRisk Level: ${result.risk_level}` : '';
            let recommendation = '';
            if (result.risk_level === 'High risk') {
                recommendation = '<br><br><span style="font-weight:600;">Recommendation:</span> <span style="color:#c62828;">Do NOT click any links or open attachments in this email!</span>';
            } else if (result.risk_level === 'Medium risk') {
                recommendation = '<br><br><span style="font-weight:600;">Recommendation:</span> Be cautious. Double-check the sender and content before clicking.';
            } else if (result.risk_level === 'Low risk') {
                recommendation = '<br><br><span style="font-weight:600;">Recommendation:</span> This email appears safe, but always stay alert.';
            }
            if (result.prediction === "Phishing") {
                resultDiv.className = 'result-box phishing';
                resultDiv.innerHTML = `<span style="font-weight:600;">Result:</span> <span style="font-weight:500;">Phishing${displayConfidence}</span>${riskLevel}${recommendation}`;
            } else if (result.prediction === "Not Phishing") {
                resultDiv.className = 'result-box not-phishing';
                resultDiv.innerHTML = `<span style="font-weight:600;">Result:</span> <span style="font-weight:500;">Not Phishing${displayConfidence}</span>${riskLevel}${recommendation}`;
            } else {
                resultDiv.className = 'result-box error';
                resultDiv.innerHTML = `<span style='font-weight:600;'>Error:</span> ${result.message || 'Unknown error'}`;
            }
        } else if (message.type === "phishing_error") {
            resultDiv.textContent = `API Error: ${message.error}`;
            resultDiv.className = 'error';
        }
    });
});