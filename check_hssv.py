import os
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    print(f"[ALERT] {message}")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, json=payload)
            print("Telegram response status:", res.status_code)
        except Exception as e:
            print("Failed to send Telegram message:", e)

def run_checker():
    hssv_url = "https://www.hssv.org/spay-neuter-appointment/"
    available_found = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Intercept backend API calls from Vetter Software
        def handle_response(response):
            nonlocal available_found
            if "timetable" in response.url and response.status == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        available_found = True
                    elif isinstance(data, dict) and data.get("slots"):
                        available_found = True
                except Exception:
                    pass

        page.on("response", handle_response)

        print("Navigating to HSSV spay/neuter portal...")
        page.goto(hssv_url, wait_until="networkidle")
        page.wait_for_timeout(5000)

        body_text = page.inner_text("body").lower()
        
        if available_found or ("select time" in body_text and "no appointments available" not in body_text):
            msg = (
                "🐶 *HSSV Neuter Appointment Available!*\n\n"
                "An open slot was detected for large dog spay/neuter.\n"
                "👉 [Book Immediately on HSSV](https://www.hssv.org/spay-neuter-appointment/)"
            )
            send_telegram_alert(msg)
        else:
            print("No open appointments found at this time.")

        browser.close()

if __name__ == "__main__":
    run_checker()
