console.log("Phishing Detector content script โหลดแล้ว.");
function extractEmailContent() {
    let emailBody = null;
    let gmailBodyElements = document.querySelectorAll('div.a3s.aiL, div.gmail_default');
    for (let elem of gmailBodyElements) {
        if (elem.innerText && elem.innerText.length > 100) { 
            emailBody = elem.innerText;
            console.log("Extracted email content from Gmail.");
            return emailBody;
        }
    }
    let outlookBodyElements = document.querySelectorAll('.ReadMsgBody, ._rp_r_q');
    for (let elem of outlookBodyElements) {
        if (elem.innerText && elem.innerText.length > 100) {
            emailBody = elem.innerText;
            console.log("Extracted email content from Outlook.");
            return emailBody;
        }
    }
    let yahooMailBody = document.querySelector('.yui_3_16_0_1_1623867650893_2508 > div, ._e_n.moz-txt-dir');
    if (yahooMailBody && yahooMailBody.innerText && yahooMailBody.innerText.length > 100) {
        emailBody = yahooMailBody.innerText;
        console.log("Extracted email content from Yahoo Mail.");
        return emailBody;
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