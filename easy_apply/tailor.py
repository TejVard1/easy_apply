from __future__ import annotations

from typing import Iterable

from .models import JobPosting, TailoredResume, UserProfile
from .text_utils import dedupe


def _normalize_keyword_set(items: Iterable[str]) -> set[str]:
    return {item.strip().lower() for item in items if item and item.strip()}


def _rank_skills(profile_skills: list[str], job_keywords: list[str], limit: int = 16) -> list[str]:
    keyword_set = _normalize_keyword_set(job_keywords)

    in_job = [skill for skill in profile_skills if skill.strip().lower() in keyword_set]
    overflow = [skill for skill in profile_skills if skill.strip().lower() not in keyword_set]
    ranked = dedupe(in_job + overflow)
    return ranked[:limit]


def _tailored_summary(profile: UserProfile, job: JobPosting, matched_keywords: list[str]) -> str:
    base = profile.summary.strip()
    if not base:
        base = (
            f"Results-oriented professional targeting {job.title or 'this role'} positions"
            f" with a strong track record in delivery, ownership, and cross-functional execution."
        )

    top_matches = ", ".join(matched_keywords[:7])
    focus = []
    if job.title:
        focus.append(job.title)
    if job.company:
        focus.append(f"at {job.company}")
    focus_line = " ".join(focus).strip()

    if top_matches:
        return (
            f"{base} Tailored for {focus_line or 'the target role'}, highlighting proven work in {top_matches}."
        )
    return f"{base} Tailored for {focus_line or 'the target role'}."


def _ats_score(job_keywords: list[str], matched_keywords: list[str]) -> float:
    if not job_keywords:
        return 0.0
    coverage = len(matched_keywords) / len(job_keywords)
    return round(min(100.0, coverage * 100), 2)


def _build_markdown(profile: UserProfile, summary: str, ranked_skills: list[str]) -> str:
    lines: list[str] = []

    lines.append(f"# {profile.full_name or profile.user_id}")
    contact_fields = [profile.email, profile.phone, profile.location, profile.linkedin_url, profile.github_url]
    contact_line = " | ".join([field for field in contact_fields if field])
    if contact_line:
        lines.append(contact_line)
    lines.append("")

    lines.append("## Professional Summary")
    lines.append(summary)
    lines.append("")

    if ranked_skills:
        lines.append("## Core Skills")
        for skill in ranked_skills:
            lines.append(f"- {skill}")
        lines.append("")

    if profile.experiences:
        lines.append("## Experience")
        for exp in profile.experiences:
            heading = exp.title
            if exp.company:
                heading += f" - {exp.company}" if heading else exp.company
            if heading:
                lines.append(f"### {heading}")
            date_line = ""
            if exp.start_date:
                date_line = exp.start_date
            if exp.end_date:
                date_line = f"{date_line} - {exp.end_date}" if date_line else exp.end_date
            if date_line:
                lines.append(date_line)
            if exp.summary:
                lines.append(exp.summary)
            for bullet in exp.highlights:
                lines.append(f"- {bullet}")
            lines.append("")

    if profile.projects:
        lines.append("## Projects")
        for project in profile.projects:
            if project.name:
                lines.append(f"### {project.name}")
            if project.description:
                lines.append(project.description)
            if project.technologies:
                lines.append(f"Tech: {', '.join(project.technologies)}")
            lines.append("")

    if profile.educations:
        lines.append("## Education")
        for edu in profile.educations:
            line = edu.degree
            if edu.institution:
                line = f"{line}, {edu.institution}" if line else edu.institution
            if edu.end_date:
                line = f"{line} ({edu.end_date})"
            lines.append(f"- {line}")
        lines.append("")

    if profile.certifications:
        lines.append("## Certifications")
        for cert in profile.certifications:
            lines.append(f"- {cert}")
        lines.append("")

    return "\n".join(lines).strip()


def tailor_resume(profile: UserProfile, job: JobPosting) -> TailoredResume:
    job_keywords = dedupe([kw.lower() for kw in job.keywords if len(kw) > 1])[:30]
    profile_keywords = _normalize_keyword_set(profile.skills)

    matched = [kw for kw in job_keywords if kw in profile_keywords]
    missing = [kw for kw in job_keywords if kw not in profile_keywords]

    ranked_skills = _rank_skills(profile.skills, job_keywords)
    summary = _tailored_summary(profile, job, matched)
    markdown = _build_markdown(profile=profile, summary=summary, ranked_skills=ranked_skills)

    return TailoredResume(
        user_id=profile.user_id,
        job_title=job.title,
        company=job.company,
        ats_score=_ats_score(job_keywords, matched),
        matched_keywords=matched,
        missing_keywords=missing,
        markdown=markdown,
    )
