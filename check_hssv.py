import os
import time
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram environment variables not set. Alert skipped.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Telegram alert sent successfully!")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def check_availability_on_page(page, week_num):
    """Inspects the page for available appointment slots."""
    # Method 1: Check for clickable time slot buttons or links
    # Common selectors used in booking systems like DaySmart / Vetter
    slot_selectors = [
        "a.appointment-slot",
        ".available-slot",
        "button.slot",
        "td.available",
        ".timetable-slot:not(.disabled)",
        "a[href*='book']"
    ]
    
    found_slots = []
    for selector in slot_selectors:
        elements = page.query_selector_all(selector)
        if elements:
            found_slots.extend([e.text_content().strip() for e in elements if e.text_content().strip()])

    # Method 2: DOM Text fallback
    page_text = page.content().lower()
    no_appt_keywords = [
        "no open appointments",
        "no available appointments",
        "no slots available",
        "fully booked"
    ]
    
    has_no_appt_text = any(keyword in page_text for keyword in no_appt_keywords)

    if found_slots:
        print(f"Week {week_num}: OPEN APPOINTMENTS FOUND! ({', '.join(found_slots[:5])})")
        return True, f"Found slots in Week {week_num}: {', '.join(found_slots[:5])}"
    elif not has_no_appt_text:
        # If the 'no appointments' banner isn't explicitly present, log potential slot detection
        print(f"Week {week_num}: Potential availability detected (No 'fully booked' message).")
        return True, f"Potential open slot detected during Week {week_num} check!"
    else:
        print(f"Week {week_num}: No open appointments found.")
        return False, None

def run():
    print("Navigating to HSSV spay/neuter portal...")
    
    # Target URL for HSSV portal
    url = "https://www.hssv.org/services/spay-neuter/" # Update if using a direct booking URL
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        time.sleep(3)

        # Handle iFrame if the booking calendar is embedded inside one
        frames = page.frames
        target_page = page
        for frame in frames:
            if "vettersoftware.com" in frame.url or "booking" in frame.url:
                target_page = frame
                break

        overall_availability = []

        # Check current week (Week 1) + 4 next weeks (Total 5 weeks)
        for week in range(1, 5):
            print(f"\n--- Checking Week {week} ---")
            is_available, alert_msg = check_availability_on_page(target_page, week)
            
            if is_available:
                overall_availability.append(alert_msg)

            # Click the 'Next' button to advance to the next week
            if week < 5:
                # Selector strategy for calendar Next button (arrows / buttons)
                next_button_selectors = [
                    "button:has-text('Next')",
                    "a:has-text('Next')",
                    ".fa-chevron-right",
                    ".fa-angle-right",
                    "button.next-week",
                    "a.next",
                    "[aria-label='Next week']",
                    "[title='Next']"
                ]
                
                clicked = False
                for btn_selector in next_button_selectors:
                    btn = target_page.query_selector(btn_selector)
                    if btn and btn.is_visible():
                        print(f"Clicking 'Next Week' button using selector: {btn_selector}")
                        btn.click()
                        time.sleep(3)  # Wait for calendar content to reload
                        clicked = True
                        break
                
                if not clicked:
                    print("Could not find 'Next Week' button on calendar. Ending week iteration.")
                    break

        # Send alert if any slots were found in any of the 4 weeks
        if overall_availability:
            summary_msg = "🚨 HSSV Appointment Alert! 🚨\n\n" + "\n".join(overall_availability) + "\n\nBook immediately!"
            send_telegram_alert(summary_msg)
        else:
            print("\nFinished checking 4 weeks ahead: No appointments available across all weeks.")

        browser.close()

if __name__ == "__main__":
    run()
