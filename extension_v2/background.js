chrome.runtime.onMessage.addListener(
    function(request, sender, sendResponse) {
        if (request.type === "phishing_result" || request.type === "phishing_error") {
            chrome.runtime.sendMessage(request);
        }
        return true;
    }
);