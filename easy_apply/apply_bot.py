from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - dependency optional until apply flow is used
    PlaywrightError = Exception  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment]
    sync_playwright = None

from .models import UserProfile


def _first_name(full_name: str) -> str:
    return full_name.split()[0] if full_name.strip() else ""


def _last_name(full_name: str) -> str:
    parts = full_name.split()
    return parts[-1] if len(parts) > 1 else ""


def _profile_field_values(profile: UserProfile) -> dict[str, str]:
    return {
        "first name": _first_name(profile.full_name),
        "firstname": _first_name(profile.full_name),
        "given name": _first_name(profile.full_name),
        "last name": _last_name(profile.full_name),
        "lastname": _last_name(profile.full_name),
        "family name": _last_name(profile.full_name),
        "name": profile.full_name,
        "full name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "mobile": profile.phone,
        "city": profile.location,
        "location": profile.location,
        "linkedin": profile.linkedin_url,
        "github": profile.github_url,
        "portfolio": profile.portfolio_url,
        "website": profile.portfolio_url,
        "summary": profile.summary,
        "about": profile.summary,
        "skills": ", ".join(profile.skills),
    }


def _best_match_value(combined_descriptor: str, field_values: dict[str, str]) -> str:
    text = combined_descriptor.lower()
    for key, value in field_values.items():
        if key in text and value:
            return value
    return ""


def _safe_text(element, default: str = "") -> str:
    try:
        text = element.text_content(timeout=300)
        return text.strip() if text else default
    except PlaywrightError:
        return default


def _fill_visible_form_fields(page, profile: UserProfile) -> int:
    field_values = _profile_field_values(profile)
    total_filled = 0

    elements = page.locator("input, textarea, select")
    count = elements.count()

    for idx in range(count):
        element = elements.nth(idx)
        try:
            if not element.is_visible(timeout=200):
                continue
            if element.is_disabled(timeout=200):
                continue
        except PlaywrightError:
            continue

        tag = (element.evaluate("(el) => el.tagName") or "").lower()
        input_type = (element.get_attribute("type") or "").lower()

        if input_type in {"hidden", "checkbox", "radio", "file", "submit", "button", "password"}:
            continue

        name = element.get_attribute("name") or ""
        field_id = element.get_attribute("id") or ""
        placeholder = element.get_attribute("placeholder") or ""
        aria_label = element.get_attribute("aria-label") or ""

        label_text = ""
        if field_id:
            label = page.locator(f"label[for='{field_id}']").first
            label_text = _safe_text(label)

        descriptor = " | ".join([name, field_id, placeholder, aria_label, label_text])
        value = _best_match_value(descriptor, field_values)

        if not value:
            continue

        try:
            if tag == "select":
                select_ok = False
                try:
                    element.select_option(label=value)
                    select_ok = True
                except PlaywrightError:
                    pass
                if not select_ok:
                    try:
                        element.select_option(value=value)
                        select_ok = True
                    except PlaywrightError:
                        pass
                if select_ok:
                    total_filled += 1
                continue

            element.fill(value, timeout=700)
            total_filled += 1
        except PlaywrightError:
            continue

    return total_filled


def _upload_resume_if_present(page, resume_path: Path | None) -> bool:
    if not resume_path:
        return False
    if not resume_path.exists():
        return False

    try:
        file_inputs = page.locator("input[type='file']")
        if file_inputs.count() == 0:
            return False
        file_inputs.first.set_input_files(str(resume_path))
        return True
    except PlaywrightError:
        return False


def _click_if_exists(page, selectors: list[str]) -> bool:
    for selector in selectors:
        button = page.locator(selector).first
        try:
            if button.count() > 0 and button.is_visible(timeout=700):
                button.click(timeout=1500)
                return True
        except PlaywrightError:
            continue
    return False


def _exists_visible(page, selectors: list[str]) -> bool:
    for selector in selectors:
        node = page.locator(selector).first
        try:
            if node.count() > 0 and node.is_visible(timeout=600):
                return True
        except PlaywrightError:
            continue
    return False


def _run_multi_step_flow(
    page,
    profile: UserProfile,
    resume_path: Path | None,
    submit: bool,
    *,
    flow_name: str,
    open_selectors: list[str],
    next_selectors: list[str],
    submit_selectors: list[str],
    max_steps: int,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "flow": flow_name,
        "steps": 0,
        "filled_fields": 0,
        "resume_uploaded": False,
        "submitted": False,
    }

    if open_selectors:
        _click_if_exists(page, open_selectors)

    for _ in range(max_steps):
        state["steps"] += 1
        state["filled_fields"] += _fill_visible_form_fields(page, profile)

        if not state["resume_uploaded"]:
            state["resume_uploaded"] = _upload_resume_if_present(page, resume_path)

        submit_available = _exists_visible(page, submit_selectors)
        if submit_available:
            if submit:
                state["submitted"] = _click_if_exists(page, submit_selectors)
            return state

        progressed = _click_if_exists(page, next_selectors)
        if not progressed:
            break

    return state


def _linkedin_easy_apply(page, profile: UserProfile, resume_path: Path | None, submit: bool) -> dict[str, Any]:
    open_selectors = [
        "button:has-text('Easy Apply')",
        "button[aria-label*='Easy Apply']",
        "button.jobs-apply-button",
    ]
    next_selectors = [
        "button:has-text('Next')",
        "button:has-text('Review')",
        "button[aria-label*='Continue to next step']",
    ]
    submit_selectors = [
        "button:has-text('Submit application')",
        "button[aria-label*='Submit application']",
    ]

    state = _run_multi_step_flow(
        page,
        profile,
        resume_path,
        submit,
        flow_name="linkedin_easy_apply",
        open_selectors=open_selectors,
        next_selectors=next_selectors,
        submit_selectors=submit_selectors,
        max_steps=20,
    )

    if state["steps"] == 0:
        state["error"] = "Easy Apply flow did not start"
    return state


def _workday_apply(page, profile: UserProfile, resume_path: Path | None, submit: bool) -> dict[str, Any]:
    open_selectors = [
        "button:has-text('Apply')",
        "a:has-text('Apply')",
        "button[data-automation-id='adventureButton']",
        "button[data-automation-id='applyButton']",
    ]
    next_selectors = [
        "button:has-text('Next')",
        "button:has-text('Continue')",
        "button:has-text('Review')",
        "button[data-automation-id='pageFooterNextButton']",
        "button[data-automation-id='bottom-navigation-next-button']",
    ]
    submit_selectors = [
        "button:has-text('Submit')",
        "button:has-text('Submit Application')",
        "button[data-automation-id='pageFooterSubmitButton']",
        "button[data-automation-id='bottom-navigation-submit-button']",
    ]

    return _run_multi_step_flow(
        page,
        profile,
        resume_path,
        submit,
        flow_name="workday",
        open_selectors=open_selectors,
        next_selectors=next_selectors,
        submit_selectors=submit_selectors,
        max_steps=25,
    )


def _greenhouse_apply(page, profile: UserProfile, resume_path: Path | None, submit: bool) -> dict[str, Any]:
    open_selectors = [
        "a:has-text('Apply for this job')",
        "button:has-text('Apply for this job')",
    ]
    next_selectors = [
        "button:has-text('Continue')",
        "button:has-text('Next')",
    ]
    submit_selectors = [
        "button:has-text('Submit Application')",
        "button#submit_app",
        "button[type='submit']",
    ]

    return _run_multi_step_flow(
        page,
        profile,
        resume_path,
        submit,
        flow_name="greenhouse",
        open_selectors=open_selectors,
        next_selectors=next_selectors,
        submit_selectors=submit_selectors,
        max_steps=8,
    )


def _lever_apply(page, profile: UserProfile, resume_path: Path | None, submit: bool) -> dict[str, Any]:
    open_selectors = [
        "a:has-text('Apply')",
        "button:has-text('Apply')",
        "a:has-text('Apply for this job')",
    ]
    next_selectors = [
        "button:has-text('Next')",
        "button:has-text('Continue')",
    ]
    submit_selectors = [
        "button:has-text('Submit Application')",
        "button:has-text('Apply')",
        "button[type='submit']",
    ]

    return _run_multi_step_flow(
        page,
        profile,
        resume_path,
        submit,
        flow_name="lever",
        open_selectors=open_selectors,
        next_selectors=next_selectors,
        submit_selectors=submit_selectors,
        max_steps=10,
    )


def _generic_apply_flow(page, profile: UserProfile, resume_path: Path | None, submit: bool) -> dict[str, Any]:
    filled_fields = _fill_visible_form_fields(page, profile)
    resume_uploaded = _upload_resume_if_present(page, resume_path)

    submit_selectors = [
        "button:has-text('Submit')",
        "button:has-text('Apply')",
        "button[type='submit']",
        "input[type='submit']",
    ]

    submitted = False
    if submit:
        submitted = _click_if_exists(page, submit_selectors)

    return {
        "flow": "generic",
        "filled_fields": filled_fields,
        "resume_uploaded": resume_uploaded,
        "submitted": submitted,
    }


def _pick_adapter(domain: str):
    if "linkedin.com" in domain:
        return "linkedin", _linkedin_easy_apply
    if "myworkdayjobs.com" in domain or "workday" in domain:
        return "workday", _workday_apply
    if "greenhouse.io" in domain or "greenhouse" in domain:
        return "greenhouse", _greenhouse_apply
    if "lever.co" in domain or "lever" in domain:
        return "lever", _lever_apply
    return "generic", _generic_apply_flow


def auto_apply(
    job_url: str,
    profile: UserProfile,
    resume_path: Path | None,
    submit: bool = False,
    headless: bool = False,
    wait_login_seconds: int = 60,
) -> dict[str, Any]:
    if sync_playwright is None:
        raise RuntimeError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    parsed = urlparse(job_url)
    domain = parsed.netloc.lower()
    adapter_name, adapter_fn = _pick_adapter(domain)

    result: dict[str, Any] = {
        "job_url": job_url,
        "domain": domain,
        "submit_mode": submit,
        "adapter": adapter_name,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            result["error"] = "Navigation timeout"
            browser.close()
            return result

        if wait_login_seconds > 0:
            page.wait_for_timeout(wait_login_seconds * 1000)

        flow_result = adapter_fn(page, profile, resume_path, submit)
        result.update(flow_result)

        browser.close()

    return result
