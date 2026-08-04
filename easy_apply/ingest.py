from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import USER_AGENT
from .models import Education, Experience, Project, UserProfile
from .text_utils import dedupe, extract_email, extract_phone, extract_skill_matches, normalize_whitespace


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise RuntimeError("PDF parsing requires `pypdf`. Install it before ingesting PDF resumes.") from exc

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "DOCX parsing requires `python-docx`. Install it before ingesting DOCX resumes."
        ) from exc

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _read_docx(path)
    if suffix in {".txt", ".md", ".rtf"}:
        return _read_text_file(path)
    raise ValueError(f"Unsupported file format: {path.suffix}")


def scrape_public_profile(url: str, timeout: int = 20) -> str:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()

    title = soup.title.text.strip() if soup.title and soup.title.text else ""
    body_text = soup.get_text(separator="\n")
    return normalize_whitespace(f"{title}\n{body_text}")


def _extract_name_from_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:10]:
        if len(line.split()) in {2, 3} and all(part[:1].isalpha() for part in line.split()):
            return line
    return ""


SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "career history",
    ),
    "education": ("education", "academic background"),
    "projects": ("projects", "personal projects"),
    "certifications": ("certifications", "licenses"),
}


def _normalize_heading(line: str) -> str:
    return re.sub(r"[^a-z ]+", "", line.lower()).strip()


def _extract_sections(text: str) -> dict[str, list[str]]:
    sections = {key: [] for key in SECTION_PATTERNS}
    active_section: str | None = None
    lines = [line.rstrip() for line in text.splitlines()]

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        normalized = _normalize_heading(line)
        changed_section = False
        for section, patterns in SECTION_PATTERNS.items():
            if normalized in patterns:
                active_section = section
                changed_section = True
                break
        if changed_section:
            continue

        if active_section:
            sections[active_section].append(line)

    return sections


def _parse_experience(lines: list[str]) -> list[Experience]:
    if not lines:
        return []

    entries: list[Experience] = []
    current: Experience | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith(("-", "*", "•")):
            if current:
                current.highlights.append(stripped.lstrip("-*• ").strip())
            continue

        header_like = bool(re.search(r"\b(at|@)\b|\|", stripped)) or len(stripped.split()) <= 8
        if current is None or (header_like and (current.summary or current.highlights)):
            if current:
                entries.append(current)
            title, company = "", ""
            for sep in (" | ", " at ", " @ ", ", "):
                if sep in stripped:
                    left, right = stripped.split(sep, 1)
                    title, company = left.strip(), right.strip()
                    break
            if not title:
                title = stripped
            current = Experience(title=title, company=company)
            continue

        if current and not current.summary:
            current.summary = stripped
        elif current:
            current.highlights.append(stripped)

    if current:
        entries.append(current)
    return entries[:8]


def _parse_education(lines: list[str]) -> list[Education]:
    entries: list[Education] = []
    for line in lines:
        clean = line.lstrip("-*• ").strip()
        if not clean or len(clean) < 3:
            continue
        degree, institution = "", ""
        for sep in (",", " - ", " | "):
            if sep in clean:
                left, right = clean.split(sep, 1)
                degree, institution = left.strip(), right.strip()
                break
        if not degree:
            degree = clean
        entries.append(Education(degree=degree, institution=institution))
    return entries[:5]


def _parse_projects(lines: list[str]) -> list[Project]:
    projects: list[Project] = []
    current: Project | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("-", "*", "•")) and current:
            if current.description:
                current.description += " "
            current.description += stripped.lstrip("-*• ").strip()
            continue
        if current:
            projects.append(current)
        current = Project(name=stripped, description="")
    if current:
        projects.append(current)
    return projects[:6]


def _parse_certifications(lines: list[str]) -> list[str]:
    certs = [line.lstrip("-*• ").strip() for line in lines if line.strip()]
    return dedupe(certs)[:15]


def _merge_structured_resume_data(profile: UserProfile, text: str) -> None:
    sections = _extract_sections(text)

    parsed_experience = _parse_experience(sections.get("experience", []))
    parsed_education = _parse_education(sections.get("education", []))
    parsed_projects = _parse_projects(sections.get("projects", []))
    parsed_certs = _parse_certifications(sections.get("certifications", []))

    existing_exp_keys = {(item.title.lower(), item.company.lower()) for item in profile.experiences}
    for item in parsed_experience:
        key = (item.title.lower(), item.company.lower())
        if key not in existing_exp_keys and (item.title or item.company):
            profile.experiences.append(item)
            existing_exp_keys.add(key)

    existing_edu_keys = {(item.degree.lower(), item.institution.lower()) for item in profile.educations}
    for item in parsed_education:
        key = (item.degree.lower(), item.institution.lower())
        if key not in existing_edu_keys:
            profile.educations.append(item)
            existing_edu_keys.add(key)

    existing_project_names = {item.name.lower() for item in profile.projects}
    for item in parsed_projects:
        name_key = item.name.lower()
        if name_key and name_key not in existing_project_names:
            profile.projects.append(item)
            existing_project_names.add(name_key)

    profile.certifications = dedupe(profile.certifications + parsed_certs)


def _merge_profile_text(profile: UserProfile, text: str, source_label: str) -> None:
    email = extract_email(text)
    phone = extract_phone(text)
    skills = extract_skill_matches(text)
    guessed_name = _extract_name_from_text(text)

    if not profile.full_name and guessed_name:
        profile.full_name = guessed_name
    if not profile.email and email:
        profile.email = email
    if not profile.phone and phone:
        profile.phone = phone

    if not profile.summary:
        profile.summary = text[:800]

    profile.skills = dedupe(profile.skills + skills)
    profile.raw_sources = dedupe(profile.raw_sources + [source_label])


def ingest_sources(
    profile: UserProfile,
    profile_urls: list[str] | None = None,
    resume_paths: list[Path] | None = None,
    manual_fields: dict[str, str] | None = None,
) -> UserProfile:
    profile_urls = profile_urls or []
    resume_paths = resume_paths or []
    manual_fields = manual_fields or {}

    for url in profile_urls:
        scraped = scrape_public_profile(url)
        _merge_profile_text(profile, scraped, f"url:{url}")

        hostname = urlparse(url).netloc.lower()
        if "linkedin.com" in hostname:
            profile.linkedin_url = profile.linkedin_url or url
        if "github.com" in hostname:
            profile.github_url = profile.github_url or url

    for resume_path in resume_paths:
        text = extract_text_from_file(resume_path)
        _merge_profile_text(profile, text, f"resume:{resume_path}")
        _merge_structured_resume_data(profile, text)

    for key, value in manual_fields.items():
        cleaned = value.strip()
        if not cleaned:
            continue
        if key == "skills":
            profile.skills = dedupe(profile.skills + [v.strip() for v in cleaned.split(",") if v.strip()])
            continue
        if hasattr(profile, key):
            setattr(profile, key, cleaned)

    return profile
