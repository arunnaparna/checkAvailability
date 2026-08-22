import os
import requests
from playwright.sync_api import sync_playwright

# Example using Telegram for free push notifications to your phone
# (Replace with Pushover, Twilio, or Slack Webhook)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_alert(message):
    print(f"[ALERT] {message}")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def run_check():
    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to HSSV appointment page
        page.goto("https://www.hssv.org/spay-neuter-appointment/", wait_until="networkidle")
        page.wait_for_timeout(3000)
        
        # Locate and switch into the embedded iframe if present
        iframe_element = page.query_selector("iframe")
        frame = iframe_element.content_frame() if iframe_element else page
        
        # Select Dropdowns for Large Dog Neuter
        # Adjust selector names depending on the live widget form elements
        try:
            # Example: Select Neuter and Weight options
            frame.select_option("select[name='service_type']", label="Neuter")
            frame.select_option("select[name='weight']", label="51-75 lbs")  # Or 76-100 lbs
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Direct selection skipped or managed by default view: {e}")

        # Check DOM content for open dates
        page_text = frame.inner_text("body")
        
        # Trigger conditions
        no_availability_phrases = ["no appointments available", "fully booked", "no open slots"]
        has_no_slots = any(phrase in page_text.lower() for phrase in no_availability_phrases)

        if not has_no_slots or "select time" in page_text.lower():
            send_alert("🚨 HSSV Spay/Neuter Appointment Available! Book now: https://www.hssv.org/spay-neuter-appointment/")
        else:
            print("No appointments available for large dogs at this time.")

        browser.close()

if __name__ == "__main__":
    run_check()
