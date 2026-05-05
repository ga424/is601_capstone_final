"""
E2E tests for the additional calculation types:
  - Exponentiation (a ** b)
  - Modulus (a % b)
  - Average (mean of all inputs)

Requires the FastAPI app running at PLAYWRIGHT_BASE_URL.
Run with:
    python -m pytest -q -m e2e tests/test_e2e_calculations.py
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
    assert page.evaluate("window.localStorage.getItem('is601.jwt')")


# ---------------------------------------------------------------------------
# Positive scenarios
# ---------------------------------------------------------------------------


def test_dashboard_exponentiation_calculation(page):
    email = f"exp-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.get_by_role("heading", name="Calculation Dashboard")).to_be_visible()

    page.get_by_label("Type").select_option("exponentiation")
    page.get_by_label("Inputs").fill("2, 3")
    page.get_by_role("button", name="Create Calculation").click()

    expect(page.get_by_role("status")).to_contain_text("Calculation created: 8")
    expect(page.locator("[data-result-list]")).to_contain_text("exponentiation(2, 3) = 8")


def test_dashboard_modulus_calculation(page):
    email = f"mod-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.get_by_role("heading", name="Calculation Dashboard")).to_be_visible()

    page.get_by_label("Type").select_option("modulus")
    page.get_by_label("Inputs").fill("10, 3")
    page.get_by_role("button", name="Create Calculation").click()

    expect(page.get_by_role("status")).to_contain_text("Calculation created: 1")
    expect(page.locator("[data-result-list]")).to_contain_text("modulus(10, 3) = 1")


def test_dashboard_average_calculation(page):
    email = f"avg-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.get_by_role("heading", name="Calculation Dashboard")).to_be_visible()

    page.get_by_label("Type").select_option("average")
    page.get_by_label("Inputs").fill("10, 20, 30")
    page.get_by_role("button", name="Create Calculation").click()

    expect(page.get_by_role("status")).to_contain_text("Calculation created: 20")
    expect(page.locator("[data-result-list]")).to_contain_text("average(10, 20, 30) = 20")


def test_dashboard_exponentiation_chained(page):
    """Left-to-right chaining: (2 ** 3) ** 2 = 64."""
    email = f"expchain-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    page.get_by_label("Type").select_option("exponentiation")
    page.get_by_label("Inputs").fill("2, 3, 2")
    page.get_by_role("button", name="Create Calculation").click()

    expect(page.get_by_role("status")).to_contain_text("Calculation created: 64")


# ---------------------------------------------------------------------------
# Negative scenarios
# ---------------------------------------------------------------------------


def test_dashboard_modulus_by_zero_shows_error(page):
    """Modulus with divisor 0 is rejected by the Pydantic validator (HTTP 422)."""
    email = f"modzero-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    expect(page.get_by_role("heading", name="Calculation Dashboard")).to_be_visible()

    page.get_by_label("Type").select_option("modulus")
    page.get_by_label("Inputs").fill("10, 0")
    page.get_by_role("button", name="Create Calculation").click()

    expect(page.get_by_role("status")).to_contain_text(
        re.compile(r"Cannot compute modulus|Unable to create calculation", re.IGNORECASE)
    )


def test_new_types_appear_in_dropdown(page):
    """All three new operation types must be selectable in the dashboard dropdown."""
    email = f"dropdown-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    select = page.get_by_label("Type")

    for value in ("exponentiation", "modulus", "average"):
        select.select_option(value)
        assert page.locator(f'#calcType option[value="{value}"]').count() == 1
