import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL addresses
CURRENCY_URL = "https://www.tgju.org/currency"
GOLD_URL = "https://www.tgju.org/gold-chart"
COIN_URL = "https://www.tgju.org/coin"

def setup_driver(headless=True):
    """
    Set up the Selenium webdriver
    """
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Error setting up Selenium driver: {str(e)}")
        raise

def get_currency_prices(headless=True):
    """
    Get currency prices from the currency page
    """
    driver = None
    try:
        logger.info("Getting currency prices...")
        driver = setup_driver(headless=headless)
        
        # Open currency page
        driver.get(CURRENCY_URL)
        logger.info(f"Currency page opened: {CURRENCY_URL}")
        
        # Wait for the page to load completely
        time.sleep(5)
        
        currencies = {}
        
        # Method 1: Try to find currencies directly with ID
        try:
            # For dollar
            dollar_element = driver.find_element(By.ID, "l-price_dollar_rl")
            if dollar_element:
                price_text = dollar_element.text.strip()
                if price_text:
                    logger.info(f"Dollar price with ID: {price_text}")
                    # Extract only the price number using regex
                    import re
                    # Search for numeric pattern with commas
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                    if price_match:
                        clean_price = price_match.group(1)
                        logger.info(f"Cleaned dollar price: {clean_price}")
                        currencies['dollar'] = clean_price
                    else:
                        currencies['dollar'] = price_text
                    
            # For euro
            euro_element = driver.find_element(By.ID, "l-price_eur")
            if euro_element:
                price_text = euro_element.text.strip()
                if price_text:
                    logger.info(f"Euro price with ID: {price_text}")
                    # Extract only the price number using regex
                    import re
                    # Search for numeric pattern with commas
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                    if price_match:
                        clean_price = price_match.group(1)
                        logger.info(f"Cleaned euro price: {clean_price}")
                        currencies['euro'] = clean_price
                    else:
                        currencies['euro'] = price_text
        except Exception as e:
            logger.warning(f"Error finding currencies with ID: {str(e)}")
        
        # Method 2: Search in tables
        if 'dollar' not in currencies or 'euro' not in currencies:
            # Find all market-table tables
            tables = driver.find_elements(By.CSS_SELECTOR, "table.market-table")
            logger.info(f"Number of tables found: {len(tables)}")
            
            # Save page HTML for debugging
            page_source = driver.page_source
            with open("page_debug.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            logger.info("Page HTML saved for debugging")
            
            # For each table, check rows
            for table_idx, table in enumerate(tables):
                logger.info(f"Checking table number {table_idx+1}")
                rows = table.find_elements(By.TAG_NAME, "tr")
                logger.info(f"Number of rows in table {table_idx+1}: {len(rows)}")
                
                # Traverse table rows
                for row_idx, row in enumerate(rows):
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 2:
                            continue
                        
                        # Check currency name
                        name_cell = cells[0]
                        currency_name = name_cell.text.strip()
                        logger.info(f"Currency name in row {row_idx+1}: {currency_name}")
                        
                        # Column 2: Live price
                        price_cell = cells[1]
                        price_text = price_cell.text.strip()
                        logger.info(f"Raw price text: {price_text}")
                        
                        # Extract only the price number using regex
                        import re
                        # Search for numeric pattern with commas
                        price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                        if price_match:
                            clean_price = price_match.group(1)
                            logger.info(f"Cleaned price from table: {clean_price}")
                            
                            # Check if this currency is dollar or euro
                            if "دلار" in currency_name and 'dollar' not in currencies:
                                logger.info(f"Dollar price from table (cleaned): {clean_price}")
                                currencies['dollar'] = clean_price
                            
                            if "یورو" in currency_name and 'euro' not in currencies:
                                logger.info(f"Euro price from table (cleaned): {clean_price}")
                                currencies['euro'] = clean_price
                        else:
                            # Remove parentheses and content inside
                            price_text = re.sub(r'\([^)]*\)', '', price_text).strip()
                            
                            # Check if this currency is dollar or euro
                            if "دلار" in currency_name and len(price_text) > 0 and 'dollar' not in currencies:
                                logger.info(f"Dollar price from table: {price_text}")
                                currencies['dollar'] = price_text
                            
                            if "یورو" in currency_name and len(price_text) > 0 and 'euro' not in currencies:
                                logger.info(f"Euro price from table: {price_text}")
                                currencies['euro'] = price_text
                        
                        # If both currencies found, exit loop
                        if 'dollar' in currencies and 'euro' in currencies:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error processing row {row_idx+1}: {str(e)}")
                        continue
                        
                # If both currencies found, exit loop
                if 'dollar' in currencies and 'euro' in currencies:
                    break
        
        # Method 3: Use alternative selectors
        if 'dollar' not in currencies or 'euro' not in currencies:
            # Search with more specific selector
            rows = driver.find_elements(By.CSS_SELECTOR, ".market-table-row")
            logger.info(f"Number of rows found with direct selector: {len(rows)}")
            
            for row in rows:
                try:
                    name_element = row.find_element(By.CSS_SELECTOR, ".market-name")
                    price_element = row.find_element(By.CSS_SELECTOR, ".market-price")
                    
                    currency_name = name_element.text.strip()
                    price_text = price_element.text.strip()
                    
                    # Extract only the price number using regex
                    import re
                    # Search for numeric pattern with commas
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                    if price_match:
                        clean_price = price_match.group(1)
                        
                        if "دلار" in currency_name and 'dollar' not in currencies:
                            logger.info(f"Dollar price with specific selector (cleaned): {clean_price}")
                            currencies['dollar'] = clean_price
                        
                        if "یورو" in currency_name and 'euro' not in currencies:
                            logger.info(f"Euro price with specific selector (cleaned): {clean_price}")
                            currencies['euro'] = clean_price
                    else:
                        price_text = re.sub(r'\([^)]*\)', '', price_text).strip()
                        
                        if "دلار" in currency_name and len(price_text) > 0 and 'dollar' not in currencies:
                            logger.info(f"Dollar price with specific selector: {price_text}")
                            currencies['dollar'] = price_text
                        
                        if "یورو" in currency_name and len(price_text) > 0 and 'euro' not in currencies:
                            logger.info(f"Euro price with specific selector: {price_text}")
                            currencies['euro'] = price_text
                        
                except Exception as e:
                    logger.warning(f"Error in specific selector: {str(e)}")
                    continue
        
        # Final check
        if 'dollar' not in currencies:
            logger.error("Dollar price not found")
        if 'euro' not in currencies:
            logger.error("Euro price not found")
            
        if not currencies:
            logger.error("No currency prices found")
            return None
            
        # Convert dictionary keys to farsi for consistency with the rest of the code
        farsi_currencies = {}
        if 'dollar' in currencies:
            farsi_currencies['دلار'] = currencies['dollar']
        if 'euro' in currencies:
            farsi_currencies['یورو'] = currencies['euro']
        
        return farsi_currencies
            
    except Exception as e:
        logger.error(f"Error getting currency prices: {str(e)}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Selenium driver closed")
            except Exception as e:
                logger.warning(f"Error closing Selenium driver: {str(e)}")

def get_gold_prices(headless=True):
    """
    Get gold prices from the gold page
    """
    driver = None
    try:
        logger.info("Getting gold prices...")
        driver = setup_driver(headless=headless)
        
        # Open gold page
        driver.get(GOLD_URL)
        logger.info(f"Gold page opened: {GOLD_URL}")
        
        # Wait for the page to load completely
        time.sleep(5)
        
        gold_prices = {}
        
        # Try to find 18-karat gold price with ID
        try:
            gold_element = driver.find_element(By.ID, "l-geram18")
            if gold_element:
                price_text = gold_element.text.strip()
                if price_text:
                    logger.info(f"18-karat gold price with ID: {price_text}")
                    # Extract only the price number using regex
                    import re
                    # Search for numeric pattern with commas - more precise
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                    if price_match:
                        clean_price = price_match.group(1)
                        logger.info(f"Cleaned 18-karat gold price: {clean_price}")
                        gold_prices['18k_gold'] = clean_price
                    else:
                        gold_prices['18k_gold'] = price_text
        except Exception as e:
            logger.warning(f"Error finding 18-karat gold with ID: {str(e)}")
        
        # If not found with ID method, try other methods
        if '18k_gold' not in gold_prices:
            # Search in tables
            tables = driver.find_elements(By.CSS_SELECTOR, "table.market-table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 2:
                            continue
                        
                        name_cell = cells[0]
                        gold_name = name_cell.text.strip()
                        
                        if "طلای 18 عیار" in gold_name or "یک گرم طلای 18 عیار" in gold_name:
                            price_cell = cells[1]
                            price_text = price_cell.text.strip()
                            # Extract only the price number using regex
                            import re
                            # Search for numeric pattern with commas - more precise
                            price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                            if price_match:
                                clean_price = price_match.group(1)
                                logger.info(f"18-karat gold price from table (cleaned): {clean_price}")
                                gold_prices['18k_gold'] = clean_price
                            else:
                                # Remove parentheses and content inside
                                price_text = re.sub(r'\([^)]*\)', '', price_text).strip()
                                logger.info(f"18-karat gold price from table: {price_text}")
                                gold_prices['18k_gold'] = price_text
                            break
                    except Exception as e:
                        logger.warning(f"Error processing gold table row: {str(e)}")
                        continue
        
        # Final check
        if '18k_gold' not in gold_prices:
            logger.error("18-karat gold price not found")
        
        # Convert dictionary keys to farsi for consistency with the rest of the code
        farsi_gold = {}
        if '18k_gold' in gold_prices:
            farsi_gold['طلای 18 عیار'] = gold_prices['18k_gold']
            
        return farsi_gold
            
    except Exception as e:
        logger.error(f"Error getting gold prices: {str(e)}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Gold page Selenium driver closed")
            except Exception as e:
                logger.warning(f"Error closing gold page Selenium driver: {str(e)}")

def get_coin_prices(headless=True):
    """
    Get coin prices from the coin page
    """
    driver = None
    try:
        logger.info("Getting coin prices...")
        driver = setup_driver(headless=headless)
        
        # Open coin page
        driver.get(COIN_URL)
        logger.info(f"Coin page opened: {COIN_URL}")
        
        # Wait for the page to load completely
        time.sleep(5)
        
        coin_prices = {}
        
        # Try to find Emami coin price with ID
        try:
            coin_element = driver.find_element(By.ID, "l-sekee")
            if coin_element:
                price_text = coin_element.text.strip()
                if price_text:
                    logger.info(f"Emami coin price with ID: {price_text}")
                    # Extract only the price number using regex
                    import re
                    # Search for numeric pattern with commas - more precise
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                    if price_match:
                        clean_price = price_match.group(1)
                        logger.info(f"Cleaned Emami coin price: {clean_price}")
                        coin_prices['emami_coin'] = clean_price
                    else:
                        coin_prices['emami_coin'] = price_text
        except Exception as e:
            logger.warning(f"Error finding Emami coin with ID: {str(e)}")
        
        # If not found with ID method, try other methods
        if 'emami_coin' not in coin_prices:
            # Search in tables
            tables = driver.find_elements(By.CSS_SELECTOR, "table.market-table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 2:
                            continue
                        
                        name_cell = cells[0]
                        coin_name = name_cell.text.strip()
                        
                        if "سکه امامی" in coin_name or "سکه طرح امامی" in coin_name:
                            price_cell = cells[1]
                            price_text = price_cell.text.strip()
                            # Extract only the price number using regex
                            import re
                            # Search for numeric pattern with commas - more precise
                            price_match = re.search(r'(\d{1,3}(?:,\d{3})+)', price_text)
                            if price_match:
                                clean_price = price_match.group(1)
                                logger.info(f"Emami coin price from table (cleaned): {clean_price}")
                                coin_prices['emami_coin'] = clean_price
                            else:
                                # Remove parentheses and content inside
                                price_text = re.sub(r'\([^)]*\)', '', price_text).strip()
                                logger.info(f"Emami coin price from table: {price_text}")
                                coin_prices['emami_coin'] = price_text
                            break
                    except Exception as e:
                        logger.warning(f"Error processing coin table row: {str(e)}")
                        continue
        
        # Final check
        if 'emami_coin' not in coin_prices:
            logger.error("Emami coin price not found")
            
        # Convert dictionary keys to farsi for consistency with the rest of the code
        farsi_coin = {}
        if 'emami_coin' in coin_prices:
            farsi_coin['سکه امامی'] = coin_prices['emami_coin']
            
        return farsi_coin
            
    except Exception as e:
        logger.error(f"Error getting coin prices: {str(e)}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Coin page Selenium driver closed")
            except Exception as e:
                logger.warning(f"Error closing coin page Selenium driver: {str(e)}")

def format_price(price_text, is_gold_or_coin=False):
    """
    Convert price text to appropriate format and convert rials to tomans
    """
    if not price_text:
        return ""
    
    # Remove all non-numeric characters except commas and periods
    price_text = re.sub(r'[^\d,.]', '', price_text)
    
    try:
        # Convert to number
        price_num = int(price_text.replace(',', '').replace('.', ''))
        
        # Check if the price is extremely large (over 10 million)
        # This catches case where an extra set of digits was added accidentally
        if price_num > 10000000000:  # If greater than 10 billion
            logger.warning(f"Very large price detected: {price_num}, adjusting...")
            # Divide by 10 million to get a reasonable number
            price_num = price_num // 10000000
        
        # Convert rials to tomans (divide by 10)
        price_num = price_num // 10
        
        # Format number
        return f"{price_num:,}"
    except Exception as e:
        logger.error(f"Error converting price: {price_text}, error: {str(e)}")
        return price_text  # Return original text if conversion fails

def get_all_prices(headless=True):
    """
    Get all prices (currency, gold, coin) for use in the Telegram bot
    """
    try:
        # Create dictionary to store all prices
        all_prices = {}
        
        # Get currency prices
        currency_prices = get_currency_prices(headless=headless)
        if currency_prices:
            formatted_currencies = {}
            for currency_name, price_text in currency_prices.items():
                formatted_price = format_price(price_text, is_gold_or_coin=False)
                formatted_currencies[currency_name] = {
                    "price": formatted_price,
                    "original_text": price_text
                }
            all_prices['currencies'] = formatted_currencies
        
        # Get gold prices
        gold_prices = get_gold_prices(headless=headless)
        if gold_prices:
            formatted_gold = {}
            for gold_name, price_text in gold_prices.items():
                formatted_price = format_price(price_text, is_gold_or_coin=False)
                formatted_gold[gold_name] = {
                    "price": formatted_price,
                    "original_text": price_text
                }
            all_prices['gold'] = formatted_gold
        
        # Get coin prices
        coin_prices = get_coin_prices(headless=headless)
        if coin_prices:
            formatted_coin = {}
            for coin_name, price_text in coin_prices.items():
                formatted_price = format_price(price_text, is_gold_or_coin=False)
                formatted_coin[coin_name] = {
                    "price": formatted_price,
                    "original_text": price_text
                }
            all_prices['coin'] = formatted_coin
        
        return all_prices
    except Exception as e:
        logger.error(f"Error getting all prices: {str(e)}")
        return None

if __name__ == "__main__":
    # Run in non-headless mode for debugging
    prices = get_currency_prices(headless=False)
    if prices:
        print("\n===== Currency Prices =====")
        if 'دلار' in prices:
            formatted_price = format_price(prices['دلار'])
            print(f"Dollar: {formatted_price} Tomans")
        if 'یورو' in prices:
            formatted_price = format_price(prices['یورو'])
            print(f"Euro: {formatted_price} Tomans")
    else:
        print("Failed to get prices") 