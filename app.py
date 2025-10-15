from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import re

# Import the new seller-based scrapers
from seller import scrape_amazon_seller, scrape_flipkart_seller, clean_price

app = Flask(__name__)

# --- Utility Functions ---
def get_keywords(name):
    """Extracts significant keywords from a product name for comparison."""
    return set(re.findall(r'\b\w+\b', name.lower()))


def compare_products(amazon_list, flipkart_list):
    """
    Compares Amazon and Flipkart products based on name similarity.
    Determines which platform offers the best deal.
    """
    comparisons = []
    flipkart_list_copy = list(flipkart_list)

    for amazon_item in amazon_list:
        best_match = None
        highest_similarity = 0.0
        amazon_keywords = get_keywords(amazon_item['name'])

        # Find the best matching product from Flipkart
        for flipkart_item in flipkart_list_copy:
            flipkart_keywords = get_keywords(flipkart_item['name'])
            intersection = len(amazon_keywords.intersection(flipkart_keywords))
            union = len(amazon_keywords.union(flipkart_keywords))
            similarity = intersection / union if union > 0 else 0

            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = flipkart_item

        # Only compare if at least 20% keyword overlap
        if best_match and highest_similarity > 0.2:
            amazon_price = clean_price(amazon_item.get('price', 'N/A'))
            flipkart_price = clean_price(best_match.get('price', 'N/A'))

            if amazon_price != float('inf') and flipkart_price != float('inf'):
                if amazon_price < flipkart_price:
                    best_deal = 'Amazon'
                elif flipkart_price < amazon_price:
                    best_deal = 'Flipkart'
                else:
                    best_deal = 'Both have the same price'

                comparisons.append({
                    'amazon_product': amazon_item,
                    'flipkart_product': best_match,
                    'price_difference': f"₹{abs(amazon_price - flipkart_price):,.2f}",
                    'best_deal': best_deal,
                })

                # Remove matched Flipkart item to avoid duplicates
                flipkart_list_copy.remove(best_match)

    print(f"Found {len(comparisons)} matching product pairs for comparison.")
    return comparisons


# --- Flask Routes ---
@app.route('/')
def index():
    """Renders the main search page."""
    return render_template('index.html')


@app.route('/search')
def search():
    """
    Handles a product search request.
    Runs both Amazon and Flipkart scrapers concurrently
    and returns structured comparison results.
    """
    product_name = request.args.get('product_name')
    if not product_name:
        return jsonify({"error": "A product name is required"}), 400

    print(f"🔍 Starting concurrent search for: {product_name}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        amazon_future = executor.submit(scrape_amazon_seller, product_name)
        flipkart_future = executor.submit(scrape_flipkart_seller, product_name)
        amazon_results = amazon_future.result()
        flipkart_results = flipkart_future.result()

    comparison_results = compare_products(amazon_results, flipkart_results)

    # Remove duplicate URLs to ensure unique entries
    unique_amazon = list({p['product_url']: p for p in amazon_results if 'product_url' in p}.values())
    unique_flipkart = list({p['product_url']: p for p in flipkart_results if 'product_url' in p}.values())

    final_results = {
        "amazon": unique_amazon,
        "flipkart": unique_flipkart,
        "comparisons": comparison_results
    }

    print("✅ Search complete. Returning results.")
    return jsonify(final_results)


# --- Main Entry Point ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
