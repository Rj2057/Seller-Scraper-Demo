from flask import Flask, jsonify, request
from concurrent.futures import ThreadPoolExecutor
import re
# Import the new, robust functions from your seller.py module
from seller import scrape_amazon_seller, scrape_flipkart_seller, clean_price

app = Flask(__name__)

def get_keywords(name):
    """Extracts significant keywords from a product name for matching."""
    return set(re.findall(r'\b\w+\b', name.lower()))

def compare_products(amazon_list, flipkart_list):
    """
    Compares products, finds best matches, and identifies the best deal.
    """
    comparisons = []
    flipkart_list_copy = list(flipkart_list)

    for amazon_item in amazon_list:
        best_match = None
        highest_similarity = 0.0
        amazon_keywords = get_keywords(amazon_item['name'])
        
        for flipkart_item in flipkart_list_copy:
            flipkart_keywords = get_keywords(flipkart_item['name'])
            intersection = len(amazon_keywords.intersection(flipkart_keywords))
            union = len(amazon_keywords.union(flipkart_keywords))
            similarity = intersection / union if union > 0 else 0
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = flipkart_item
        
        if best_match and highest_similarity > 0.2:
            amazon_price = clean_price(amazon_item['price'])
            flipkart_price = clean_price(best_match['price'])
            
            if amazon_price != float('inf') and flipkart_price != float('inf'):
                best_deal_source = "Both have the same price"
                if amazon_price < flipkart_price:
                    best_deal_source = 'Amazon'
                elif flipkart_price < amazon_price:
                    best_deal_source = 'Flipkart'

                comparisons.append({
                    'amazon_product': amazon_item,
                    'flipkart_product': best_match,
                    'price_difference': f"₹{abs(amazon_price - flipkart_price):,.2f}",
                    'best_deal': best_deal_source,
                })
                flipkart_list_copy.remove(best_match)

    return comparisons

@app.route('/')
def index():
    """Provides instructions on how to use the API."""
    return "<h1>Product Search API</h1><p>Use the /search endpoint with a product_name query. Example: /search?product_name=iphone+15</p>"

@app.route('/search')
def search():
    """Handles the search request, runs scrapers, and returns results."""
    product_name = request.args.get('product_name')
    if not product_name:
        return jsonify({"error": "A product name is required"}), 400

    with ThreadPoolExecutor(max_workers=2) as executor:
        amazon_future = executor.submit(scrape_amazon_seller, product_name)
        flipkart_future = executor.submit(scrape_flipkart_seller, product_name)
        amazon_results = amazon_future.result()
        flipkart_results = flipkart_future.result()
    
    comparison_results = compare_products(amazon_results, flipkart_results)

    # Sort individual lists by price (lowest first)
    amazon_results.sort(key=lambda x: clean_price(x.get('price', 'inf')))
    flipkart_results.sort(key=lambda x: clean_price(x.get('price', 'inf')))

    return jsonify({
        "amazon": amazon_results,
        "flipkart": flipkart_results,
        "comparisons": comparison_results
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

