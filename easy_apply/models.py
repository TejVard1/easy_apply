from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Experience:
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    summary: str = ""
    highlights: list[str] = field(default_factory=list)


@dataclass
class Education:
    institution: str = ""
    degree: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass
class Project:
    name: str = ""
    description: str = ""
    technologies: list[str] = field(default_factory=list)


@dataclass
class UserProfile:
    user_id: str
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    experiences: list[Experience] = field(default_factory=list)
    educations: list[Education] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    raw_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfile":
        experiences = [Experience(**item) for item in data.get("experiences", [])]
        educations = [Education(**item) for item in data.get("educations", [])]
        projects = [Project(**item) for item in data.get("projects", [])]
        return cls(
            user_id=data["user_id"],
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            linkedin_url=data.get("linkedin_url", ""),
            github_url=data.get("github_url", ""),
            portfolio_url=data.get("portfolio_url", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", []),
            certifications=data.get("certifications", []),
            experiences=experiences,
            educations=educations,
            projects=projects,
            raw_sources=data.get("raw_sources", []),
        )


@dataclass
class JobPosting:
    source_url: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    requirements: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobPosting":
        return cls(
            source_url=data.get("source_url", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            description=data.get("description", ""),
            requirements=data.get("requirements", []),
            responsibilities=data.get("responsibilities", []),
            keywords=data.get("keywords", []),
        )


@dataclass
class TailoredResume:
    user_id: str
    job_title: str
    company: str
    ats_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
