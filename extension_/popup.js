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
            }
            const tab = tabs[0];
            console.log('Current tab URL:', tab.url);
            console.log('Current tab ID:', tab.id);
            
            // Check if tab is ready
            if (tab.status !== 'complete') {
                setBusy(false);
                resultDiv.innerHTML = '<div class="small">Page is still loading. Please wait and try again.</div>';
                return;
            }
            const trySend = (attemptsLeft = 3) => {
                console.log(`Attempting to send message, attempts left: ${attemptsLeft}`);
                
                // First, check if we're on a supported email site
                const isSupportedSite = tab.url.includes('mail.google.com') || 
                                      tab.url.includes('outlook.live.com') || 
                                      tab.url.includes('outlook.office.com') || 
                                      tab.url.includes('mail.yahoo.com');
                
                if (!isSupportedSite) {
                    setBusy(false);
                    resultDiv.innerHTML = '<div class="small">Please navigate to Gmail, Outlook, or Yahoo Mail to scan emails.</div>';
                    return;
                }
                
                // Try to inject content script if it doesn't exist
                if (attemptsLeft === 3) {
                    statusText.textContent = 'Checking content script...';
                    chrome.scripting.executeScript({ 
                        target: { tabId: tab.id }, 
                        files: ['content.js'] 
                    }).then(() => {
                        console.log('Content script injected successfully');
                        setTimeout(() => trySend(attemptsLeft - 1), 1000);
                    }).catch((err) => {
                        console.log('Content script already exists or injection failed:', err);
                        setTimeout(() => trySend(attemptsLeft - 1), 500);
                    });
                    return;
                }
                
                chrome.tabs.sendMessage(tab.id, { type: 'scan_email' }, (response) => {
                    if (chrome.runtime.lastError) {
                        const msg = chrome.runtime.lastError.message || '';
                        console.warn('sendMessage failed:', msg);
                        
                        if (msg.includes('Receiving end does not exist') && attemptsLeft > 0) {
                            statusText.textContent = 'Retrying...';
                            console.log('Content script not ready, retrying...');
                            setTimeout(() => trySend(attemptsLeft - 1), 1000);
                        } else {
                            setBusy(false);
                            resultDiv.innerHTML = `<div class="small">Could not connect to content script. Please refresh the page and try again.</div>`;
                        }
                        return;
                    }
                    
                    // If no runtime.lastError, wait for content script to send result via runtime.sendMessage
                    console.log('Message sent successfully, waiting for response...');
                    statusText.textContent = 'Waiting for result...';
                });
            };
            trySend(3);
        });
    });

    // Receive results from content script
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        console.log('Received message:', message);
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
    
    // Add timeout for scan operation
    let scanTimeout;
    const originalSetBusy = setBusy;
    setBusy = (busy) => {
        if (busy) {
            scanTimeout = setTimeout(() => {
                setBusy(false);
                resultDiv.innerHTML = '<div class="small">Scan timeout. Please try again.</div>';
            }, 30000); // 30 second timeout
        } else {
            if (scanTimeout) {
                clearTimeout(scanTimeout);
                scanTimeout = null;
            }
        }
        originalSetBusy(busy);
    };

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