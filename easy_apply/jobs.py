from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .config import USER_AGENT
from .models import JobPosting
from .text_utils import dedupe, lines_after_heading, normalize_whitespace, top_keywords


def _from_json_ld(soup: BeautifulSoup) -> tuple[str, str, str]:
    title = ""
    company = ""
    location = ""

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        entries = payload if isinstance(payload, list) else [payload]
        for item in entries:
            if not isinstance(item, dict):
                continue
            typ = str(item.get("@type", "")).lower()
            if "jobposting" not in typ:
                continue
            title = item.get("title", title) or title
            hiring_org = item.get("hiringOrganization", {})
            if isinstance(hiring_org, dict):
                company = hiring_org.get("name", company) or company
            location_obj = item.get("jobLocation", {})
            if isinstance(location_obj, dict):
                address = location_obj.get("address", {})
                if isinstance(address, dict):
                    city = address.get("addressLocality", "")
                    region = address.get("addressRegion", "")
                    location = ", ".join([part for part in [city, region] if part]) or location
    return title, company, location


def scrape_job_url(url: str, timeout: int = 20) -> JobPosting:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for bad in soup(["script", "style", "noscript"]):
        if bad.get("type") == "application/ld+json":
            continue
        bad.decompose()

    title_ld, company_ld, location_ld = _from_json_ld(soup)

    title = title_ld
    if not title:
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
    if not title and soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)

    company = company_ld
    if not company:
        company_meta = soup.find("meta", attrs={"property": "og:site_name"})
        if company_meta and company_meta.get("content"):
            company = company_meta["content"].strip()

    raw_text = soup.get_text(separator="\n")
    body_text = normalize_whitespace(raw_text)
    requirements = lines_after_heading(raw_text, r"requirements|qualifications|what you need", max_lines=14)
    responsibilities = lines_after_heading(raw_text, r"responsibilities|what you.?ll do|duties", max_lines=14)

    if not location_ld:
        loc_match = re.search(r"(Remote|Hybrid|Onsite|[A-Z][a-z]+,\s*[A-Z]{2})", raw_text)
        location = loc_match.group(0) if loc_match else ""
    else:
        location = location_ld

    keywords = dedupe(top_keywords(body_text, limit=50))

    return JobPosting(
        source_url=url,
        title=title,
        company=company,
        location=location,
        description=body_text,
        requirements=requirements,
        responsibilities=responsibilities,
        keywords=keywords,
    )


def parse_job_text(text: str, source_url: str = "") -> JobPosting:
    clean_text = normalize_whitespace(text)
    requirements = lines_after_heading(text, r"requirements|qualifications|what you need", max_lines=14)
    responsibilities = lines_after_heading(text, r"responsibilities|what you.?ll do|duties", max_lines=14)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else ""
    company = lines[1] if len(lines) > 1 else ""

    return JobPosting(
        source_url=source_url,
        title=title,
        company=company,
        description=clean_text,
        requirements=requirements,
        responsibilities=responsibilities,
        keywords=dedupe(top_keywords(clean_text, limit=50)),
    )


def parse_job_file(path: Path) -> JobPosting:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return parse_job_text(text, source_url=str(path))
