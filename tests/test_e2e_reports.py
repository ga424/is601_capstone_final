"""
E2E tests for the Report/History feature.

Verifies the Usage Report panel on the dashboard:
  - Shows "No calculations yet" when empty
  - Reflects counts and totals after creating calculations
  - Updates automatically after create/delete
  - Requires authentication

Requires the FastAPI app running at PLAYWRIGHT_BASE_URL.
Run with:
    python -m pytest -q -m e2e tests/test_e2e_reports.py
"""

import re
import uuid

import pytest
from playwright.sync_api import expect


pytestmark = pytest.mark.e2e


def register_user(page, email: str, password: str):
    page.goto("/register")
    page.get_by_label("Email").fill(email)
    page.locator('input[name="password"]').fill(password)
    page.locator('input[name="confirmPassword"]').fill(password)
    page.get_by_role("button", name="Register").click()
    expect(page).to_have_url(re.compile(r".*/dashboard$"), timeout=10_000)


# ---------------------------------------------------------------------------
# Positive scenarios
# ---------------------------------------------------------------------------


def test_report_panel_visible_on_dashboard(page):
    email = f"report-visible-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.get_by_role("heading", name="Usage Report")).to_be_visible()


def test_report_shows_empty_state_initially(page):
    email = f"report-empty-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.locator("[data-report-list]")).to_contain_text("No calculations yet")


def test_report_updates_after_calculation_created(page):
    email = f"report-update-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")

    page.get_by_label("Type").select_option("addition")
    page.get_by_label("Inputs").fill("5, 3")
    page.get_by_role("button", name="Create Calculation").click()
    expect(page.get_by_role("status")).to_contain_text("Calculation created")

    report = page.locator("[data-report-list]")
    expect(report).to_contain_text("Total: 1")
    expect(report).to_contain_text("Most used: addition")
    expect(report).to_contain_text("addition: 1")


def test_report_shows_average_result(page):
    email = f"report-avg-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")

    page.get_by_label("Type").select_option("addition")
    page.get_by_label("Inputs").fill("10, 10")
    page.get_by_role("button", name="Create Calculation").click()
    expect(page.get_by_role("status")).to_contain_text("Calculation created")

    expect(page.locator("[data-report-list]")).to_contain_text("Average result:")


def test_report_counts_multiple_types(page):
    email = f"report-multi-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")

    for calc_type, inputs in [("addition", "1, 2"), ("addition", "3, 4"), ("subtraction", "10, 3")]:
        page.get_by_label("Type").select_option(calc_type)
        page.get_by_label("Inputs").fill(inputs)
        page.get_by_role("button", name="Create Calculation").click()
        expect(page.get_by_role("status")).to_contain_text("Calculation created")

    report = page.locator("[data-report-list]")
    expect(report).to_contain_text("Total: 3")
    expect(report).to_contain_text("Most used: addition")
    expect(report).to_contain_text("addition: 2")
    expect(report).to_contain_text("subtraction: 1")


def test_report_updates_after_delete(page):
    email = f"report-delete-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")

    page.get_by_label("Type").select_option("addition")
    page.get_by_label("Inputs").fill("1, 2")
    page.get_by_role("button", name="Create Calculation").click()
    expect(page.get_by_role("status")).to_contain_text("Calculation created")
    expect(page.locator("[data-report-list]")).to_contain_text("Total: 1")

    page.once("dialog", lambda d: d.accept())
    page.locator(".result-item").first.get_by_role("button", name="Delete").click()
    expect(page.get_by_role("status")).to_contain_text("deleted")

    expect(page.locator("[data-report-list]")).to_contain_text("No calculations yet")


def test_report_refresh_button_works(page):
    email = f"report-refresh-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.get_by_role("heading", name="Usage Report")).to_be_visible()
    page.get_by_role("button", name="Refresh", exact=False).nth(1).click()
    expect(page.locator("[data-report-list]")).to_be_visible()
