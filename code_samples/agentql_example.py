from playwright.sync_api import sync_playwright
import agentql

def main():
    try:
        with sync_playwright() as playwright:
            # Launch browser with specific options
            browser = playwright.chromium.launch(
                headless=False,  # Set to True if you don't need to see the browser
                args=['--ignore-certificate-errors']  # Ignore SSL certificate issues
            )
            
            # Create a new page with AgentQL wrapper
            page = agentql.wrap(browser.new_page())
            
            # Navigate to the page with error handling
            try:
                page.goto(
                    "https://scrapeme.live/shop/",
                    wait_until="domcontentloaded",
                    timeout=30000  # 30 seconds timeout
                )
                
                # Use AgentQL query to find and interact with elements
                QUERY = """
                {
                    search_box
                    products {
                        title
                        price
                    }
                }
                """
                
                # Execute the query
                result = page.query_elements(QUERY)
                
                # Interact with elements
                if result.search_box:
                    result.search_box.fill("fish")
                    page.keyboard.press("Enter")
                
                # Wait to see results (for demo)
                page.wait_for_timeout(5000)
                
            except Exception as e:
                print(f"Error during page interaction: {e}")
            
            finally:
                # Clean up
                page.close()
                browser.close()
                
    except Exception as e:
        print(f"Error setting up browser: {e}")

if __name__ == "__main__":
    main()