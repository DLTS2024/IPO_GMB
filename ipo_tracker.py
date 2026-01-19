import os
import re
import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ofcngucvrrmzvihjgjvz.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    """Get Supabase client"""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable not set!")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def scrape_ipos():
    """Scrape IPO data from investorgain.com"""
    logger.info("Starting IPO data extraction")
    today = datetime.today().date()

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    logger.info("Launching Chrome WebDriver in headless mode")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    try:
        logger.info("Navigating to IPO GMP report page")
        driver.get("https://www.investorgain.com/report/live-ipo-gmp/331/all/")

        logger.info("Waiting for IPO table to load")
        table = wait.until(EC.presence_of_element_located((By.ID, "report_table")))
        rows = table.find_elements(By.TAG_NAME, "tr")

        ipo_data = []
        logger.info("Extracting IPO rows")

        for row in rows[1:]:  # skip header
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 8:
                name = cols[0].text.strip()
                gmp_text = cols[1].text.strip()
                price = cols[2].text.strip()
                sub = cols[3].text.strip()
                start = cols[7].text.strip()
                end = cols[8].text.strip()

                # Extract GMP percentage
                match = re.search(r"\(([\d\.]+)%\)", gmp_text)
                gmp_value = float(match.group(1)) if match else 0

                # Extract dates
                def extract_date(text):
                    match = re.search(r"\d{1,2}-[A-Za-z]{3}", text)
                    if match:
                        parsed = datetime.strptime(match.group(), "%d-%b").date()
                        # Handle year rollover
                        parsed = parsed.replace(year=today.year)
                        if parsed < today - timedelta(days=180):
                            parsed = parsed.replace(year=today.year + 1)
                        return parsed
                    return None

                start_date = extract_date(start)
                end_date = extract_date(end)

                if end_date:
                    ipo_data.append({
                        'name': name,
                        'gmp': gmp_value,
                        'price': price,
                        'subscription': sub,
                        'start_date': start_date,
                        'end_date': end_date
                    })

    finally:
        driver.quit()

    logger.info(f"IPO data extraction complete. Total IPOs found: {len(ipo_data)}")
    return ipo_data


def add_new_ipos_to_db(ipos):
    """Add new IPOs to database if closing date is >= 3 days from today"""
    supabase = get_supabase()
    today = datetime.today().date()
    min_end_date = today + timedelta(days=3)
    
    added_count = 0
    
    for ipo in ipos:
        # Only add if closing date is at least 3 days away
        if ipo['end_date'] >= min_end_date:
            try:
                # Check if already exists
                existing = supabase.table('ipos').select('id').eq('name', ipo['name']).eq('end_date', str(ipo['end_date'])).execute()
                
                if not existing.data:
                    # Insert new IPO
                    result = supabase.table('ipos').insert({
                        'name': ipo['name'],
                        'price': ipo['price'],
                        'start_date': str(ipo['start_date']) if ipo['start_date'] else None,
                        'end_date': str(ipo['end_date']),
                        'subscription': ipo['subscription'],
                        'status': 'tracking'
                    }).execute()
                    
                    logger.info(f"Added new IPO: {ipo['name']} (ends {ipo['end_date']})")
                    added_count += 1
                    
                    # Also record initial GMP
                    if result.data:
                        ipo_id = result.data[0]['id']
                        supabase.table('gmp_history').insert({
                            'ipo_id': ipo_id,
                            'gmp': ipo['gmp'],
                            'recorded_at': str(today)
                        }).execute()
                        
            except Exception as e:
                logger.error(f"Error adding IPO {ipo['name']}: {e}")
    
    logger.info(f"Added {added_count} new IPOs to database")
    return added_count


def main():
    """Main function to track new IPOs"""
    logger.info("=== IPO Tracker Started ===")
    
    # Scrape current IPOs
    ipos = scrape_ipos()
    
    if not ipos:
        logger.warning("No IPOs found!")
        return
    
    # Add qualifying IPOs to database
    add_new_ipos_to_db(ipos)
    
    logger.info("=== IPO Tracker Finished ===")


if __name__ == "__main__":
    main()
