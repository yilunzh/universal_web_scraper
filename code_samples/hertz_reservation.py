from playwright.sync_api import sync_playwright
import agentql
import time
from datetime import datetime, timedelta

def make_hertz_reservation():
    # Proxy configuration
    proxy_config = {
        "server": "us.smartproxy.com:10001",
        "username": "sp4i2f0p3a",
        "password": "Cb0ags0arr9o_d7AAY"
    }

    try:
        with sync_playwright() as playwright:
            # Launch browser with more realistic settings
            browser = playwright.chromium.launch(
                headless=False,
                proxy=proxy_config,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                ]
            )
            
            # Create context with specific viewport and locale
            context = browser.new_context(
                viewport={'width': 1600, 'height': 800},
                locale='en-US',
                timezone_id='America/Los_Angeles',
                geolocation={'latitude': 37.7749, 'longitude': -122.4194},  # San Francisco coordinates
                permissions=['geolocation']
            )
            
            # Create page with AgentQL wrapper
            page = agentql.wrap(context.new_page())
            
            try:
                print("Navigating to Hertz.com...")
                # Add initial delay to avoid immediate navigation
                page.wait_for_timeout(2000)
                
                # Navigate with more options
                response = page.goto(
                    "https://www.hertz.com/rentacar/reservation/",
                    wait_until="networkidle",
                    timeout=60000
                )
                
                if response.status != 200:
                    print(f"Page load failed with status: {response.status}")
                    return
                
                # Handle cookie consent
                QUERY = """
                {
                    cookies_form {
                        reject_btn
                    }
                }
                """

                page.wait_for_timeout(20000)
                
                print("Handling cookie consent...")
                try:
                    response = page.query_elements(QUERY)

                     # Check if there is a cookie-rejection button on the page
                    if response.cookies_form.reject_btn != None:
                        # If so, click the close button to reject cookies
                        response.cookies_form.reject_btn.click()
                        print("Rejected cookies")
                    page.wait_for_timeout(10000)
                except Exception as e:
                    print("No cookie consent popup found")
                
                # Set up dates for the reservation
                pickup_date = datetime.now() + timedelta(days=7)  # 1 week from now
                return_date = pickup_date + timedelta(days=3)     # 3 day rental
                
                # Query for form elements
                QUERY = """
                {
                    pickup_location,
                    date_picker {
                        pickup_date_input,
                        return_date_input,
                        calendar
                    },
                    time_selector {
                        pickup_time,
                        return_time
                    },
                    search_button
                }
                """
                
                print("Finding form elements...")
                result = page.query_elements(QUERY)
                
                # Test location input and selection
                try:
                    print("\nTesting pickup location...")
                    # Type in search box
                    result.pickup_location.fill("SFO")
                    page.wait_for_timeout(2000)  # Wait for dropdown
                    
                    # Select from dropdown
                    try:
                        dropdown = page.locator('.location-dropdown-item').first
                        dropdown.click()
                        print("✓ Location selected from dropdown")
                    except Exception as e:
                        print(f"✗ Error selecting from dropdown: {str(e)}")

                except Exception as e:
                    print(f"✗ Error with location search: {str(e)}")
                
                # Test date selection
                try:
                    print("\nTesting date selection...")
                    # Click pickup date to open calendar
                    result.date_picker.pickup_date_input.click()
                    page.wait_for_timeout(1000)
                    
                    # Select pickup date from calendar
                    pickup_date_str = pickup_date.strftime("%Y-%m-%d")
                    calendar_day = page.locator(f'[data-date="{pickup_date_str}"]').first
                    calendar_day.click()
                    print("✓ Pickup date selected")
                    
                    # Select return date from calendar
                    return_date_str = return_date.strftime("%Y-%m-%d")
                    calendar_day = page.locator(f'[data-date="{return_date_str}"]').first
                    calendar_day.click()
                    print("✓ Return date selected")
                    
                except Exception as e:
                    print(f"✗ Error with date selection: {str(e)}")
                
                # Test time selection
                try:
                    print("\nTesting time selection...")
                    # Select pickup time
                    result.time_selector.pickup_time.select_option({
                        'label': '12:00 PM'  # or use value if known
                    })
                    print("✓ Pickup time selected")
                    
                    # Select return time
                    result.time_selector.return_time.select_option({
                        'label': '12:00 PM'  # or use value if known
                    })
                    print("✓ Return time selected")
                    
                except Exception as e:
                    print(f"✗ Error with time selection: {str(e)}")
                
                # Test search button
                try:
                    print("\nTesting search button...")
                    result.search_button.click()
                    print("✓ Search button clicked")
                except Exception as e:
                    print(f"✗ Error with search button: {str(e)}")
                
                # Fill in the form
                print("Filling reservation form...")
                
                # Location
                try:
                    print("\nTesting each form element individually...")
                    
                    # Test location input
                    try:
                        print("\nTesting pickup location...")
                        result.pickup_location.fill("SFO")
                        print("✓ Pickup location field found and filled")
                    except Exception as e:
                        print(f"✗ Error with pickup location: {str(e)}")
                        print("HTML:", result.pickup_location.inner_html() if hasattr(result.pickup_location, 'inner_html') else "Not found")
                    
                    # Test pickup date
                    try:
                        print("\nTesting pickup date...")
                        result.pickup_date.fill(pickup_date.strftime("%m/%d/%Y"))
                        print("✓ Pickup date field found and filled")
                    except Exception as e:
                        print(f"✗ Error with pickup date: {str(e)}")
                        print("HTML:", result.pickup_date.inner_html() if hasattr(result.pickup_date, 'inner_html') else "Not found")
                    
                    # Test pickup time
                    try:
                        print("\nTesting pickup time...")
                        result.pickup_time.select_option("1200")
                        print("✓ Pickup time field found and selected")
                    except Exception as e:
                        print(f"✗ Error with pickup time: {str(e)}")
                        print("HTML:", result.pickup_time.inner_html() if hasattr(result.pickup_time, 'inner_html') else "Not found")
                    
                    # Test return date
                    try:
                        print("\nTesting return date...")
                        result.return_date.fill(return_date.strftime("%m/%d/%Y"))
                        print("✓ Return date field found and filled")
                    except Exception as e:
                        print(f"✗ Error with return date: {str(e)}")
                        print("HTML:", result.return_date.inner_html() if hasattr(result.return_date, 'inner_html') else "Not found")
                    
                    # Test return time
                    try:
                        print("\nTesting return time...")
                        result.return_time.select_option("1200")
                        print("✓ Return time field found and selected")
                    except Exception as e:
                        print(f"✗ Error with return time: {str(e)}")
                        print("HTML:", result.return_time.inner_html() if hasattr(result.return_time, 'inner_html') else "Not found")
                    
                    # Test submit button
                    try:
                        print("\nTesting submit button...")
                        print("Button properties:", result.view_vehicles)
                        print("✓ Submit button found")
                    except Exception as e:
                        print(f"✗ Error with submit button: {str(e)}")
                        print("HTML:", result.view_vehicles.inner_html() if hasattr(result.view_vehicles, 'inner_html') else "Not found")

                    # Keep browser open for inspection
                    print("\nTests complete. Browser will stay open for inspection.")
                    input("Press Enter to close browser...")

                except Exception as e:
                    print(f"\nError during testing: {str(e)}")
                
                # Submit form
                print("Submitting form...")
                result.view_vehicles.click()
                
                # Wait for results page
                print("Waiting for results...")
                page.wait_for_timeout(5000)
                
                # # Query for vehicle options
                # VEHICLES_QUERY = """
                # {
                #     vehicles {
                #         name
                #         price
                #         features
                #         select_button
                #     }
                # }
                # """
                
                # vehicles = page.query_elements(VEHICLES_QUERY)
                # if vehicles:
                #     print("\nAvailable vehicles:")
                #     for vehicle in vehicles:
                #         print(f"- {vehicle.name}: {vehicle.price}")
                
                # # Keep browser open for review
                # print("\nReservation process complete. Browser will close in 30 seconds...")
                # page.wait_for_timeout(30000)
                
                # page.wait_for_timeout(5000)  # Wait for page to stabilize
                
                print("Page loaded successfully")
                # Keep browser open for inspection
                input("Press Enter to close the browser...")
                
            except Exception as e:
                print(f"Error during reservation process: {e}")
            
            # finally:
            #     context.close()
            #     browser.close()
                
    except Exception as e:
        print(f"Error setting up browser: {e}")

if __name__ == "__main__":
    make_hertz_reservation() 