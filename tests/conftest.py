import os

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("PLAYWRIGHT_BASE_URL", "http://127.0.0.1:8015")


@pytest.fixture(scope="session")
def playwright_driver():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_driver):
    browser = playwright_driver.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    yield page
    context.close()
