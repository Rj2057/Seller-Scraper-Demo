import pytest
from unittest.mock import patch, MagicMock
from seller import scrape_amazon_seller

# --- Mock HTML Snippets for Seller-Specific Scenarios ---

# Scenario 1: A product where the seller data is present.
HTML_WITH_SELLER = """
<body>
    <div data-component-type="s-search-result">
        <a class="a-link-normal" href="/sample-product/dp/B0SAMPLE1">
            <span class="a-text-normal">Complete Product</span>
        </a>
        <span class="a-price-whole">1,999</span>
        <img class="s-image" src="image.jpg" />
        <div class="a-row a-size-base a-color-secondary">Sold by Test Seller</div>
    </div>
</body>
"""

# Scenario 2: A product where the seller information is missing.
HTML_NO_SELLER = """
<body>
    <div data-component-type="s-search-result">
        <a class="a-link-normal" href="/sample-product/dp/B0SAMPLE2">
            <span class="a-text-normal">Product Without Seller</span>
        </a>
        <span class="a-price-whole">2,499</span>
        <img class="s-image" src="image.jpg" />
    </div>
</body>
"""

# --- Pytest Unit Tests Focused Exclusively on the Seller Scraper ---

@patch('seller.get_driver')
def test_scrape_finds_seller_when_present(mock_get_driver):
    """
    Tests that the scraper correctly extracts the seller name when it is present in the HTML.
    This corresponds to the "happy path" for the seller feature.
    """
    mock_driver = MagicMock()
    mock_driver.page_source = HTML_WITH_SELLER
    mock_get_driver.return_value = mock_driver
    
    results = scrape_amazon_seller("test")
    
    # Assert that one product was found and its seller is correct.
    assert len(results) == 1
    product = results[0]
    assert product['seller'] == "Test Seller"

@patch('seller.get_driver')
def test_scrape_handles_missing_seller(mock_get_driver):
    """
    Tests the graceful handling (edge case) when the seller name is missing.
    The scraper should return a default value, not crash.
    """
    mock_driver = MagicMock()
    mock_driver.page_source = HTML_NO_SELLER
    mock_get_driver.return_value = mock_driver
    
    results = scrape_amazon_seller("test")
    
    # Assert that one product was found and the default seller name was assigned.
    assert len(results) == 1
    product = results[0]
    assert product['seller'] == "Amazon"

