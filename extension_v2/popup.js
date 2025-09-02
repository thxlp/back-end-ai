document.addEventListener('DOMContentLoaded', () => {
    const scanButton = document.getElementById('scanBtn');
    const resultDiv = document.getElementById('result');
    const spinner = document.getElementById('spinner');
    const statusText = document.getElementById('statusText');
    const copyBtn = document.getElementById('copyBtn');
    const clearBtn = document.getElementById('clearBtn');

    let lastReportText = '';

    function setBusy(busy) {
        scanButton.disabled = busy;
        spinner.style.opacity = busy ? '1' : '0';
        statusText.textContent = busy ? 'Scanning...' : 'Ready';
    }

    function renderReport(result) {
        if (!result) {
            resultDiv.innerHTML = '<div class="small">No scan performed yet.</div>';
            lastReportText = '';
            return;
        }
        const confidence = (result.confidence !== undefined && result.confidence !== null) ? `Confidence: ${(parseFloat(result.confidence)*100).toFixed(2)}%` : '';
        const risk = result.risk_level ? `Risk Level: ${result.risk_level}` : '';
        const rec = result.risk_level ? `Recommendation: ${result.risk_level === 'High risk' ? 'Do NOT click links or open attachments.' : result.risk_level === 'Medium risk' ? 'Be cautious and verify sender.' : 'Appears low risk.'}` : '';

        const predClass = result.prediction === 'Phishing' ? 'phishing' : 'safe';
        resultDiv.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><div><div class="small">${risk}</div><div style="margin-top:6px;font-weight:700" class="pred ${predClass}">${result.prediction || 'Unknown'}</div></div><div class="small">${confidence}</div></div><div style="margin-top:10px" class="small">${rec}</div>`;

        lastReportText = `Prediction: ${result.prediction}\n${confidence}\n${risk}\n${rec}`;
    }

    scanButton.addEventListener('click', () => {
        setBusy(true);
        statusText.textContent = 'Requesting page...';
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (!tabs || !tabs[0]) {
                setBusy(false);
                resultDiv.innerHTML = '<div class="small">No active tab found or insufficient permissions.</div>';
                return;
            }
            const tab = tabs[0];
            const trySend = (attemptsLeft = 1) => {
                chrome.tabs.sendMessage(tab.id, { type: 'scan_email' }, (response) => {
                    if (chrome.runtime.lastError) {
                        const msg = chrome.runtime.lastError.message || '';
                        console.warn('sendMessage failed:', msg);
                        if (msg.includes('Receiving end does not exist') && attemptsLeft > 0) {
                            statusText.textContent = 'Injecting helper...';
                            chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] }).then(() => {
                                setTimeout(() => trySend(attemptsLeft - 1), 250);
                            }).catch((err) => {
                                console.error('Injection failed:', err);
                                setBusy(false);
                                resultDiv.innerHTML = `<div class="small">Failed to inject content script: ${err.message}</div>`;
                            });
                        } else {
                            setBusy(false);
                            resultDiv.innerHTML = `<div class="small">Extension error: ${msg}</div>`;
                        }
                        return;
                    }
                    // If no runtime.lastError, wait for content script to send result via runtime.sendMessage
                    statusText.textContent = 'Waiting for result...';
                });
            };
            trySend(1);
        });
    });

    // Receive results from content script
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === 'phishing_result') {
            setBusy(false);
            statusText.textContent = 'Scan complete';
            renderReport(message.result || {});
        } else if (message.type === 'phishing_error') {
            setBusy(false);
            statusText.textContent = 'Error';
            resultDiv.innerHTML = `<div class="small">API Error: ${message.error}</div>`;
        }
    });

    copyBtn.addEventListener('click', () => {
        if (!lastReportText) return;
        navigator.clipboard.writeText(lastReportText).then(() => {
            statusText.textContent = 'Report copied';
            setTimeout(() => statusText.textContent = 'Ready', 1200);
        }).catch(() => {
            statusText.textContent = 'Copy failed';
        });
    });

    clearBtn.addEventListener('click', () => {
        renderReport(null);
        statusText.textContent = 'Ready';
    });
});