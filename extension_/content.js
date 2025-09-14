console.log("Phishing Detector content script โหลดแล้ว.");
function extractEmailContent() {
    console.log("Starting email content extraction...");
    console.log("Current URL:", window.location.href);
    console.log("Page title:", document.title);
    
    let emailBody = null;
    let gmailBodyElements = document.querySelectorAll('div.a3s.aiL, div.gmail_default');
    console.log("Found Gmail elements:", gmailBodyElements.length);
    for (let elem of gmailBodyElements) {
        if (elem.innerText && elem.innerText.length > 100) { 
            emailBody = elem.innerText;
            console.log("Extracted email content from Gmail.");
            return emailBody;
        }
    }
    // Outlook selectors - try multiple selectors for different versions
    let outlookSelectors = [
        '.ReadMsgBody',
        '._rp_r_q',
        '[data-testid="message-body"]',
        '.message-body',
        '.email-body',
        '.mail-message-body',
        '.message-content',
        '[role="main"] .message-body',
        '.mail-message-content',
        'div[data-testid="message-body"]',
        '.message-text',
        '.email-content',
        // Additional Outlook selectors
        '.mail-message-text',
        '.message-view-body',
        '.email-message-body',
        '[data-testid="message-view-body"]',
        '.message-body-content',
        '.email-content-body',
        'div[class*="message-body"]',
        'div[class*="email-body"]',
        'div[class*="mail-body"]',
        // Generic selectors for Outlook
        'div[data-testid*="message"]',
        'div[data-testid*="body"]',
        'div[class*="Message"]',
        'div[class*="Body"]',
        // Outlook specific selectors
        '.ms-MessageBody',
        '.ms-MessageBody-content',
        '.ms-MessageBody-text',
        '.ms-MessageBody-textContainer',
        '.ms-MessageBody-textContainer > div',
        '.ms-MessageBody-textContainer > p',
        '.ms-MessageBody-textContainer > span',
        // Additional Outlook web selectors
        '[data-automation-id="message-body"]',
        '[data-automation-id="message-content"]',
        '.ms-MessageBody-textContainer div',
        '.ms-MessageBody-textContainer p',
        '.ms-MessageBody-textContainer span'
    ];
    
    console.log("Trying Outlook selectors...");
    for (let selector of outlookSelectors) {
        let outlookMailBody = document.querySelector(selector);
        console.log(`Outlook selector "${selector}": found ${outlookMailBody ? 1 : 0} elements`);
        if (outlookMailBody && outlookMailBody.innerText && outlookMailBody.innerText.length > 100) {
            emailBody = outlookMailBody.innerText;
            console.log(`Extracted email content from Outlook using selector: ${selector}`);
            return emailBody;
        }
    }
    
    // Fallback: try to find any div with substantial text content in Outlook
    console.log("Trying Outlook fallback method...");
    let outlookFallbackElements = document.querySelectorAll('div[class*="message"], div[class*="body"], div[class*="content"]');
    console.log("Found Outlook fallback elements:", outlookFallbackElements.length);
    for (let elem of outlookFallbackElements) {
        if (elem.innerText && elem.innerText.length > 100 && 
            !elem.querySelector('div[class*="message"], div[class*="body"], div[class*="content"]')) {
            emailBody = elem.innerText;
            console.log("Extracted email content from Outlook using fallback method.");
            return emailBody;
        }
    }
    
    // Additional fallback: try to find any element with substantial text in Outlook
    console.log("Trying additional Outlook fallback...");
    let allOutlookDivs = document.querySelectorAll('div');
    console.log("Total divs found in Outlook:", allOutlookDivs.length);
    for (let elem of allOutlookDivs) {
        if (elem.innerText && elem.innerText.length > 200 && 
            elem.innerText.length < 50000 && // Avoid very large elements
            !elem.querySelector('div') && // Avoid parent containers
            (window.location.href.includes('outlook.live.com') || window.location.href.includes('outlook.office.com'))) {
            emailBody = elem.innerText;
            console.log("Extracted email content from Outlook using additional fallback method.");
            return emailBody;
        }
    }
    
    // Special Outlook web app selectors
    console.log("Trying Outlook web app specific selectors...");
    let outlookWebSelectors = [
        '.ms-MessageBody-textContainer',
        '.ms-MessageBody-textContainer > div',
        '.ms-MessageBody-textContainer > p',
        '.ms-MessageBody-textContainer > span',
        '[data-automation-id="message-body"]',
        '[data-automation-id="message-content"]',
        '.ms-MessageBody-textContainer div',
        '.ms-MessageBody-textContainer p',
        '.ms-MessageBody-textContainer span',
        // Additional Outlook web selectors
        '.ms-MessageBody-textContainer > *',
        '.ms-MessageBody-textContainer *',
        '[data-automation-id*="message"]',
        '[data-automation-id*="body"]',
        '[data-automation-id*="content"]'
    ];
    
    for (let selector of outlookWebSelectors) {
        let outlookWebBody = document.querySelector(selector);
        console.log(`Outlook web selector "${selector}": found ${outlookWebBody ? 1 : 0} elements`);
        if (outlookWebBody && outlookWebBody.innerText && outlookWebBody.innerText.length > 100) {
            emailBody = outlookWebBody.innerText;
            console.log(`Extracted email content from Outlook web using selector: ${selector}`);
            return emailBody;
        }
    }
    
    // Final Outlook fallback: try to find any element with substantial text
    console.log("Trying final Outlook fallback...");
    let allOutlookElements = document.querySelectorAll('*');
    console.log("Total elements found in Outlook:", allOutlookElements.length);
    for (let elem of allOutlookElements) {
        if (elem.innerText && elem.innerText.length > 200 && 
            elem.innerText.length < 50000 && // Avoid very large elements
            !elem.querySelector('*') && // Avoid parent containers
            (window.location.href.includes('outlook.live.com') || window.location.href.includes('outlook.office.com'))) {
            emailBody = elem.innerText;
            console.log("Extracted email content from Outlook using final fallback method.");
            return emailBody;
        }
    }
    // Yahoo Mail selectors - try multiple selectors for different versions
    let yahooSelectors = [
        '.yui_3_16_0_1_1623867650893_2508 > div',
        '._e_n.moz-txt-dir',
        '[data-test-id="message-body"]',
        '.message-body',
        '.email-body',
        '.mail-message-body',
        '.message-content',
        '[role="main"] .message-body',
        '.mail-message-content',
        'div[data-testid="message-body"]',
        '.message-text',
        '.email-content',
        // Additional Yahoo Mail selectors
        '.mail-message-text',
        '.message-view-body',
        '.email-message-body',
        '[data-testid="message-view-body"]',
        '.message-body-content',
        '.email-content-body',
        'div[class*="message-body"]',
        'div[class*="email-body"]',
        'div[class*="mail-body"]',
        // Generic selectors for Yahoo Mail
        'div[data-testid*="message"]',
        'div[data-testid*="body"]',
        'div[class*="Message"]',
        'div[class*="Body"]'
    ];
    
    console.log("Trying Yahoo Mail selectors...");
    for (let selector of yahooSelectors) {
        let yahooMailBody = document.querySelector(selector);
        console.log(`Selector "${selector}": found ${yahooMailBody ? 1 : 0} elements`);
        if (yahooMailBody && yahooMailBody.innerText && yahooMailBody.innerText.length > 100) {
            emailBody = yahooMailBody.innerText;
            console.log(`Extracted email content from Yahoo Mail using selector: ${selector}`);
            return emailBody;
        }
    }
    
    // Fallback: try to find any div with substantial text content in Yahoo Mail
    console.log("Trying Yahoo Mail fallback method...");
    let yahooFallbackElements = document.querySelectorAll('div[class*="message"], div[class*="body"], div[class*="content"]');
    console.log("Found fallback elements:", yahooFallbackElements.length);
    for (let elem of yahooFallbackElements) {
        if (elem.innerText && elem.innerText.length > 100 && 
            !elem.querySelector('div[class*="message"], div[class*="body"], div[class*="content"]')) {
            emailBody = elem.innerText;
            console.log("Extracted email content from Yahoo Mail using fallback method.");
            return emailBody;
        }
    }
    
    // Additional fallback: try to find any element with substantial text in Yahoo Mail
    console.log("Trying additional Yahoo Mail fallback...");
    let allDivs = document.querySelectorAll('div');
    console.log("Total divs found:", allDivs.length);
    for (let elem of allDivs) {
        if (elem.innerText && elem.innerText.length > 200 && 
            elem.innerText.length < 50000 && // Avoid very large elements
            !elem.querySelector('div') && // Avoid parent containers
            window.location.href.includes('mail.yahoo.com')) {
            emailBody = elem.innerText;
            console.log("Extracted email content from Yahoo Mail using additional fallback method.");
            return emailBody;
        }
    }


    console.warn("ไม่สามารถหาเนื้อหาอีเมลได้. โปรดตรวจสอบ selector ใน content.js และโครงสร้าง HTML ของเว็บอีเมล.");
    return null;
}

async function sendEmailToAPI(emailContent) {
    if (!emailContent) {
        console.error("ไม่มีเนื้อหาอีเมลที่จะส่ง.");
        chrome.runtime.sendMessage({ type: "phishing_result", result: { prediction: "Error", message: "ไม่สามารถแยกเนื้อหาอีเมลได้." } });
        return;
    }

const API_URL = "https://web-production-e189e.up.railway.app/predict_phishing"; 

    try {
        console.log("Sending request to:", API_URL);
        console.log("Email content:", emailContent.substring(0, 100) + "...");
        
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email_content: emailContent })
        });

        console.log("Response status:", response.status);
        console.log("Response headers:", response.headers);

        if (!response.ok) {
            const errorDetail = await response.text().catch(() => "Unknown error message.");
            console.error("API Error Detail:", errorDetail);
            throw new Error(`HTTP Error! Status: ${response.status}. Detail: ${errorDetail}`);
        }

        const data = await response.json();
        console.log("การตอบกลับจาก API:", data);
        chrome.runtime.sendMessage({ type: "phishing_result", result: data });

    } catch (error) {
        console.error("เกิดข้อผิดพลาดในการส่งเนื้อหาอีเมลไปยัง API:", error);
        chrome.runtime.sendMessage({ type: "phishing_error", error: error.message });
    }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "scan_email") {
        console.log("ได้รับคำสั่ง 'scan_email' จาก popup.");
        const content = extractEmailContent();
        if (content) {
            sendEmailToAPI(content);
            sendResponse({ status: "scanning" }); // Send response immediately
        } else {
            chrome.runtime.sendMessage({ type: "phishing_result", result: { prediction: "Error", message: "ไม่สามารถแยกเนื้อหาอีเมลได้จากหน้าเว็บปัจจุบัน." } });
            sendResponse({ status: "error", message: "No email content found" });
        }
        return false; // Don't keep message channel open
    }
});