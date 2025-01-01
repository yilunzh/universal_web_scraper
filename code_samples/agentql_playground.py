import logging
import random
import time

import agentql
from agentql.ext.playwright.sync_api import Page
from playwright.sync_api import sync_playwright
import pdb

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def key_press_end_scroll(page: Page):
    page.keyboard.press("End")


def mouse_wheel_scroll(page: Page):
    # Get the element's scroll position and dimensions using JavaScript
    scroll_info = page.evaluate("""
        () => {
            const element = document.querySelector('.sc-sANrS');
            return {
                scrollTop: element.scrollTop,
                scrollHeight: element.scrollHeight,
                clientHeight: element.clientHeight
            };
        }
    """)
    
    scroll_height = scroll_info['scrollTop']
    total_height = scroll_info['scrollHeight']
    viewport_height = scroll_info['clientHeight']
    
    while scroll_height < total_height - viewport_height:
        scroll_height += viewport_height
        # Use JavaScript to scroll the specific element
        page.evaluate("""
            (scrollAmount) => {
                const element = document.querySelector('.sc-sANrS');
                element.scrollBy({
                    top: scrollAmount,
                    behavior: 'smooth'
                });
            }
        """, viewport_height)
        time.sleep(random.uniform(0.05, 0.1))  # Small delay for smooth scrolling


if __name__ == "__main__":
    QUERY = """
    {
        results[]
    }
    """
    with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
        page = agentql.wrap(browser.new_page())

        log.info("Navigating to the page...")

        page.goto("https://digital.spielwarenmesse.de/showfloor#organization")
        page.wait_for_page_ready_state()

        mouse_wheel_scroll(page)

        # if exhibitor_list:

        #     num_extra_pages_to_load = 3

            # breakpoint()

            # for times in range(num_extra_pages_to_load):
            #     log.info(f"Scrolling to the bottom of the page... (num_times = {times+1})")

            #     exhibitor_list.scroll_into_view_if_needed()
            #     page.wait_for_page_ready_state()
            #     log.info("Content loaded!")

        log.info("Issuing AgentQL data query...")
        response = page.query_data(QUERY)

        log.info(f"AgentQL response: {response}")
