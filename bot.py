import os
import re
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- FETCH IPO DATA ----------------

def get_ipos():
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

                try:
                    def extract_date(text, today):
                        match = re.search(r"\d{1,2}-[A-Za-z]{3}", text)
                        if match:
                            return datetime.strptime(match.group(), "%d-%b").date().replace(year=today.year)
                        return None

                    start_date = extract_date(start, today)
                    end_date = extract_date(end, today)

                except Exception as e:
                    logger.error(f"Date extraction failed: {e}")
                    start_date = None
                    end_date = None

                ipo_data.append({
                    'name': name,
                    'gmp': gmp_value,
                    'gmp_text': gmp_text,
                    'price': price,
                    'subscription': sub,
                    'start': start_date,
                    'end': end_date,
                    'start_raw': start,
                    'end_raw': end
                })

    finally:
        driver.quit()

    logger.info(f"IPO data extraction complete. Total IPOs found: {len(ipo_data)}")
    return ipo_data


def filter_ipos_by_gmp(ipos, gmp_range):
    """Filter IPOs based on GMP percentage range"""
    if gmp_range == "low":
        # 0-30% GMP
        return [ipo for ipo in ipos if 0 <= ipo['gmp'] <= 30]
    elif gmp_range == "high":
        # Above 30% GMP
        return [ipo for ipo in ipos if ipo['gmp'] > 30]
    return ipos


def format_ipo_message(ipo):
    """Format a single IPO as a readable message"""
    return (
        f"📊 *{ipo['name']}*\n"
        f"├ GMP: {ipo['gmp']}%\n"
        f"├ Price: {ipo['price']}\n"
        f"├ Subscription: {ipo['subscription']}\n"
        f"├ Start: {ipo['start_raw']}\n"
        f"└ End: {ipo['end_raw']}\n"
    )


# ---------------- TELEGRAM BOT HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show GMP filter buttons"""
    keyboard = [
        [
            InlineKeyboardButton("📉 0-30% GMP", callback_data="gmp_low"),
            InlineKeyboardButton("📈 Above 30% GMP", callback_data="gmp_high"),
        ],
        [
            InlineKeyboardButton("📋 All IPOs", callback_data="gmp_all"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🚀 *IPO GMP Tracker*\n\n"
        "Select your GMP preference to view IPOs:\n\n"
        "• *0-30% GMP* - Lower risk IPOs\n"
        "• *Above 30% GMP* - High potential IPOs",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()  # Acknowledge the button click
    
    # Show loading message
    await query.edit_message_text("⏳ Fetching IPO data... Please wait...")
    
    try:
        # Fetch IPO data
        ipos = get_ipos()
        
        if not ipos:
            await query.edit_message_text("❌ No IPO data found. Please try again later.")
            return
        
        # Filter based on selection
        if query.data == "gmp_low":
            filtered_ipos = filter_ipos_by_gmp(ipos, "low")
            title = "📉 *IPOs with 0-30% GMP*\n\n"
        elif query.data == "gmp_high":
            filtered_ipos = filter_ipos_by_gmp(ipos, "high")
            title = "📈 *IPOs with Above 30% GMP*\n\n"
        else:  # gmp_all
            filtered_ipos = ipos
            title = "📋 *All Current IPOs*\n\n"
        
        if not filtered_ipos:
            await query.edit_message_text(
                f"{title}No IPOs found in this category.\n\n"
                "Use /start to select a different filter.",
                parse_mode='Markdown'
            )
            return
        
        # Build response message
        message = title
        for ipo in filtered_ipos[:10]:  # Limit to 10 IPOs to avoid message too long
            message += format_ipo_message(ipo) + "\n"
        
        if len(filtered_ipos) > 10:
            message += f"\n_...and {len(filtered_ipos) - 10} more IPOs_\n"
        
        message += "\n\nUse /start to filter again."
        
        await query.edit_message_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error fetching IPO data: {e}")
        await query.edit_message_text(
            "❌ Error fetching IPO data. Please try again later.\n\n"
            f"Error: {str(e)}"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "🤖 *IPO GMP Tracker Bot*\n\n"
        "*Commands:*\n"
        "/start - Show GMP filter buttons\n"
        "/help - Show this help message\n\n"
        "*What is GMP?*\n"
        "Grey Market Premium (GMP) indicates the expected listing gain.\n"
        "Higher GMP = Higher expected profit.\n\n"
        "*Tips:*\n"
        "• IPOs with >30% GMP are considered high potential\n"
        "• Always check subscription rates too",
        parse_mode='Markdown'
    )


# ---------------- MAIN ----------------

def main():
    """Start the bot"""
    # Get token from environment variable
    TELEGRAM_TOKEN = os.getenv("TG_BOT_TOKEN")
    
    if not TELEGRAM_TOKEN:
        logger.error("TG_BOT_TOKEN environment variable not set!")
        return
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
