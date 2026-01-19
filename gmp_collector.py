import os
import re
import logging
from datetime import datetime
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


def scrape_current_gmps():
    """Scrape current GMP values for all IPOs"""
    logger.info("Scraping current GMP values")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get("https://www.investorgain.com/report/live-ipo-gmp/331/all/")
        table = wait.until(EC.presence_of_element_located((By.ID, "report_table")))
        rows = table.find_elements(By.TAG_NAME, "tr")

        gmp_data = {}

        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 8:
                name = cols[0].text.strip()
                gmp_text = cols[1].text.strip()

                # Extract GMP percentage
                match = re.search(r"\(([\d\.]+)%\)", gmp_text)
                gmp_value = float(match.group(1)) if match else 0

                gmp_data[name] = gmp_value

    finally:
        driver.quit()

    logger.info(f"Collected GMP for {len(gmp_data)} IPOs")
    return gmp_data


def collect_daily_gmps():
    """Collect daily GMP for all tracked IPOs"""
    supabase = get_supabase()
    today = str(datetime.today().date())
    
    # Get all tracking IPOs
    result = supabase.table('ipos').select('id, name').eq('status', 'tracking').execute()
    
    if not result.data:
        logger.info("No IPOs currently being tracked")
        return
    
    tracked_ipos = {ipo['name']: ipo['id'] for ipo in result.data}
    logger.info(f"Found {len(tracked_ipos)} IPOs to track")
    
    # Scrape current GMPs
    current_gmps = scrape_current_gmps()
    
    # Record GMP for each tracked IPO
    recorded_count = 0
    for name, ipo_id in tracked_ipos.items():
        if name in current_gmps:
            try:
                # Check if already recorded today
                existing = supabase.table('gmp_history').select('id').eq('ipo_id', ipo_id).eq('recorded_at', today).execute()
                
                if not existing.data:
                    supabase.table('gmp_history').insert({
                        'ipo_id': ipo_id,
                        'gmp': current_gmps[name],
                        'recorded_at': today
                    }).execute()
                    logger.info(f"Recorded GMP {current_gmps[name]}% for {name}")
                    recorded_count += 1
                else:
                    # Update existing record
                    supabase.table('gmp_history').update({
                        'gmp': current_gmps[name]
                    }).eq('ipo_id', ipo_id).eq('recorded_at', today).execute()
                    logger.info(f"Updated GMP {current_gmps[name]}% for {name}")
                    
            except Exception as e:
                logger.error(f"Error recording GMP for {name}: {e}")
        else:
            logger.warning(f"GMP not found for tracked IPO: {name}")
    
    logger.info(f"Recorded GMP for {recorded_count} IPOs")


def main():
    """Main function to collect daily GMPs"""
    logger.info("=== GMP Collector Started ===")
    collect_daily_gmps()
    logger.info("=== GMP Collector Finished ===")


if __name__ == "__main__":
    main()
