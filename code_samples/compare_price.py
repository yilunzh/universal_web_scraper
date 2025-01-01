"""This example demonstrates how to compare product prices across websites with query_data() method."""

import agentql
from playwright.sync_api import sync_playwright

# Set the URL to the desired website
JBHIFI_URL = "https://www.jbhifi.com.au/products/nintendo-switch-console-neon-1"
BIGW_URL = "https://www.bigw.com.au/product/nintendo-switch-console-neon/p/60525?store=101"
TARGET_URL = "https://www.target.com.au/p/nintendo-switch-console-neon/67583256?utm_source=google&utm_medium=organic&utm_campaign=free_listings&srsltid=AfmBOor72bFe7s2IQsUk2ibGG4q4Ag9mTifY2vgFcH1JkjKlX18HGNle6cA&region_id=102000"
OFFICE_WORK_URL = "https://www.officeworks.com.au/shop/officeworks/p/nintendo-switch-neon-nscnslneon?istCompanyId=0403b0ba-0671-498f-aeb7-e2ff71b61924&istFeedId=ea709c9a-279e-40be-951f-2668243ec753&istItemId=mqmaparxq&istBid=t&region_id=GTYP2H"
GAMESMAN_URL = "https://www.gamesmen.com.au/nintendo-switch-neon-joy-con-console-2019#Penshurst"

# Define the queries to get the product price
PRODUCT_INFO_QUERY = """
{
    nintendo_switch_price(the lowest price available for nintendo switch)
}
"""


def main():
    with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
        page = agentql.wrap(browser.new_page())
        
        urls = {
            "JB Hifi": JBHIFI_URL,
            "Big W": BIGW_URL,
            "Target": TARGET_URL,
            "Office Works": OFFICE_WORK_URL,
            "Gamesman": GAMESMAN_URL
        }

        for store_name, url in urls.items():
            try:
                page.goto(url)
                response = page.query_data(PRODUCT_INFO_QUERY)
                print(f"Price at {store_name}: {response['nintendo_switch_price']}")
            except Exception as e:
                print(f"Error fetching price from {store_name}: {str(e)}")
                continue


if __name__ == "__main__":
    main()