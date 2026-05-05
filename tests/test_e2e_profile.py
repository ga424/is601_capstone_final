"""
E2E tests for the User Profile feature:
  - View profile info
  - Update email → re-login with new email
  - Change password → re-login with new password
  - Negative: wrong current password shows error

Requires the FastAPI app running at PLAYWRIGHT_BASE_URL.
Run with:
    python -m pytest -q -m e2e tests/test_e2e_profile.py
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


def test_profile_page_displays_email(page):
    email = f"profile-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/profile")
    expect(page.get_by_role("heading", name="Your Profile")).to_be_visible()
    expect(page.locator("[data-profile-email]")).to_contain_text(email)


def test_dashboard_has_profile_link(page):
    email = f"dashlink-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/dashboard")
    profile_link = page.get_by_role("link", name="Profile")
    expect(profile_link).to_be_visible()
    profile_link.click()
    expect(page).to_have_url(re.compile(r".*/profile$"), timeout=10_000)


def test_update_email_and_re_login(page):
    old_email = f"old-{uuid.uuid4().hex[:8]}@example.com"
    new_email = f"new-{uuid.uuid4().hex[:8]}@example.com"
    password = "strongpassword123"

    register_user(page, old_email, password)
    page.goto("/profile")

    page.get_by_label("New Email").fill(new_email)
    page.get_by_role("button", name="Update Email").click()

    expect(page.get_by_role("status")).to_contain_text("Email updated successfully")
    expect(page.locator("[data-profile-email]")).to_contain_text(new_email)

    # re-login with new email
    page.evaluate("window.localStorage.removeItem('is601.jwt')")
    page.goto("/login")
    page.get_by_label("Email").fill(new_email)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url(re.compile(r".*/dashboard$"), timeout=10_000)


def test_change_password_and_re_login(page):
    email = f"pwchange-{uuid.uuid4().hex[:8]}@example.com"
    old_password = "strongpassword123"
    new_password = "newstrongpassword456"

    register_user(page, email, old_password)
    page.goto("/profile")

    page.get_by_label("Current Password").fill(old_password)
    page.get_by_label("New Password").fill(new_password)
    with page.expect_response(lambda r: "/profile/password" in r.url and r.request.method == "PATCH", timeout=30_000):
        page.get_by_role("button", name="Change Password").click()

    expect(page.get_by_role("status")).to_contain_text("Password changed successfully")

    # re-login with new password
    page.evaluate("window.localStorage.removeItem('is601.jwt')")
    page.goto("/login")
    page.get_by_label("Email").fill(email)
    page.locator('input[name="password"]').fill(new_password)
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url(re.compile(r".*/dashboard$"), timeout=10_000)


# ---------------------------------------------------------------------------
# Negative scenarios
# ---------------------------------------------------------------------------


def test_wrong_current_password_shows_error(page):
    email = f"pwwrong-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/profile")
    page.get_by_label("Current Password").fill("completelywrongpassword")
    page.get_by_label("New Password").fill("newstrongpassword456")
    page.get_by_role("button", name="Change Password").click()

    expect(page.get_by_role("status")).to_contain_text("Current password is incorrect")


def test_profile_redirects_without_token(page):
    page.goto("/login")
    page.evaluate("window.localStorage.removeItem('is601.jwt')")
    page.goto("/profile")
    expect(page).to_have_url(re.compile(r".*/login$"), timeout=5_000)


def test_update_email_rejects_invalid_format(page):
    email = f"invalidemail-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/profile")
    page.get_by_label("New Email").fill("notanemail")
    page.get_by_role("button", name="Update Email").click()

    expect(page.get_by_role("status")).to_contain_text("valid email")


def test_short_new_password_shows_error(page):
    email = f"shortpw-{uuid.uuid4().hex[:8]}@example.com"
    register_user(page, email, "strongpassword123")

    page.goto("/profile")
    page.get_by_label("Current Password").fill("strongpassword123")
    page.get_by_label("New Password").fill("short")
    page.get_by_role("button", name="Change Password").click()

    expect(page.get_by_role("status")).to_contain_text("at least 8 characters")
