"""
seller.py
---------
Responsible for scraping detailed product data including seller information
from Amazon and Flipkart.

Uses Selenium + BeautifulSoup with multiple fallback selectors to ensure
robustness against layout changes.
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


# --- CSS Selectors Configuration ---
AMAZON_SELECTORS = {
    "product_card": ['[data-component-type="s-search-result"]'],
    "name": ['span.a-text-normal'],
    "price": ['span.a-price-whole'],
    "seller": ['div.a-row.a-size-base.a-color-secondary'],
    "image": ['img.s-image'],
    "link": ['a.a-link-normal'],
}

FLIPKART_SELECTORS = {
    "product_card": ['._1AtVbE', '.cPHDOP', '._1xHGtK'],
    "name": ['._4rR01T', '.s1Q9rs'],
    "price": ['._30jeq3'],
    "image": ['._396cs4'],
    "link": ['._1fQZEK', 'a._2UzuFa'],
}


# --- Helper Functions ---
def get_driver():
    """Sets up and returns a headless Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def find_with_fallbacks(element, selectors):
    """Tries multiple selectors, returns the first matching element."""
    for selector in selectors:
        try:
            found = element.select_one(selector)
            if found:
                return found
        except Exception:
            continue
    return None


# --- Core Scraper Functions ---
def scrape_amazon_seller(product_name):
    """Scrapes Amazon for product details including seller name."""
    search_query = product_name.replace(' ', '+')
    url = f"https://www.amazon.in/s?k={search_query}"
    driver = get_driver()
    if not driver:
        return []

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, AMAZON_SELECTORS["product_card"][0]))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_cards = soup.select(AMAZON_SELECTORS["product_card"][0])
        results = []

        for card in product_cards:
            name_el = find_with_fallbacks(card, AMAZON_SELECTORS["name"])
            price_el = find_with_fallbacks(card, AMAZON_SELECTORS["price"])
            seller_el = find_with_fallbacks(card, AMAZON_SELECTORS["seller"])
            image_el = find_with_fallbacks(card, AMAZON_SELECTORS["image"])
            link_el = find_with_fallbacks(card, AMAZON_SELECTORS["link"])

            name = name_el.get_text(strip=True) if name_el else "N/A"
            price = f"₹{price_el.get_text(strip=True)}" if price_el else "N/A"
            seller = seller_el.get_text(strip=True).replace('Sold by ', '') if seller_el and 'Sold by' in seller_el.get_text() else "Amazon"
            image_url = image_el.get('src') if image_el else "N/A"
            product_url = "https://www.amazon.in" + link_el['href'] if link_el and link_el.has_attr('href') else "N/A"

            if name != "N/A" and product_url != "N/A":
                results.append({
                    'name': name,
                    'price': price,
                    'seller': seller,
                    'image_url': image_url,
                    'product_url': product_url,
                    'source': 'Amazon'
                })
        return results
    except (TimeoutException, NoSuchElementException):
        driver.save_screenshot('amazon_error.png')
        return []
    finally:
        driver.quit()


def scrape_flipkart_seller(product_name):
    """Scrapes Flipkart for product details."""
    search_query = product_name.replace(' ', '%20')
    url = f"https://www.flipkart.com/search?q={search_query}"
    driver = get_driver()
    if not driver:
        return []

    try:
        driver.get(url)
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_cards = []

        for selector in FLIPKART_SELECTORS["product_card"]:
            product_cards.extend(soup.select(selector))

        results = []
        for card in product_cards:
            name_el = find_with_fallbacks(card, FLIPKART_SELECTORS["name"])
            price_el = find_with_fallbacks(card, FLIPKART_SELECTORS["price"])
            image_el = find_with_fallbacks(card, FLIPKART_SELECTORS["image"])
            link_el = find_with_fallbacks(card, FLIPKART_SELECTORS["link"])

            name = name_el.get_text(strip=True) if name_el else "N/A"
            price = f"₹{price_el.get_text(strip=True)}" if price_el else "N/A"
            image_url = image_el.get('src') if image_el else "N/A"
            product_url = "https://www.flipkart.com" + link_el['href'] if link_el and link_el.has_attr('href') else "N/A"

            if name != "N/A" and product_url != "N/A":
                results.append({
                    'name': name,
                    'price': price,
                    'seller': "Flipkart",
                    'image_url': image_url,
                    'product_url': product_url,
                    'source': 'Flipkart'
                })
        return results
    except (TimeoutException, NoSuchElementException):
        driver.save_screenshot('flipkart_error.png')
        return []
    finally:
        driver.quit()


def clean_price(price_str):
    """Converts a price string to a float."""
    if not isinstance(price_str, str) or price_str == "N/A":
        return float('inf')
    cleaned_price = re.sub(r'[₹,A-Za-z]', '', price_str).strip()
    try:
        return float(cleaned_price)
    except (ValueError, TypeError):
        return float('inf')
