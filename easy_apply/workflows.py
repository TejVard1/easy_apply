from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .apply_bot import auto_apply
from .config import OUTPUTS_DIR
from .jobs import parse_job_file, parse_job_text, scrape_job_url
from .models import JobPosting, TailoredResume, UserProfile
from .storage import save_json
from .tailor import tailor_resume


def slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-") or "job"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def job_from_inputs(job_url: str = "", job_file: str | Path | None = None, job_text: str | None = None) -> JobPosting:
    provided = [bool(job_url), bool(job_file), bool(job_text)]
    if sum(provided) != 1:
        raise ValueError("Provide exactly one of job_url, job_file, or job_text")

    if job_url:
        return scrape_job_url(job_url)
    if job_file:
        return parse_job_file(Path(job_file))
    return parse_job_text(job_text or "")


def parse_job_to_json(job: JobPosting, out_path: Path | None = None) -> Path:
    slug = slugify(f"{job.company}-{job.title}")
    destination = out_path or OUTPUTS_DIR / f"job_{slug}_{timestamp()}.json"
    return save_json(destination, job.to_dict())


def generate_tailored_resume(
    profile: UserProfile,
    job: JobPosting,
    user_id: str,
    out_md: Path | None = None,
    out_json: Path | None = None,
) -> tuple[TailoredResume, Path, Path]:
    tailored = tailor_resume(profile, job)

    slug = slugify(f"{job.company}-{job.title}")
    ts = timestamp()
    md_path = out_md or OUTPUTS_DIR / f"resume_{user_id}_{slug}_{ts}.md"
    json_path = out_json or OUTPUTS_DIR / f"resume_{user_id}_{slug}_{ts}.json"

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(tailored.markdown, encoding="utf-8")
    save_json(json_path, tailored.to_dict())

    return tailored, md_path, json_path


def run_apply(
    profile: UserProfile,
    user_id: str,
    job_url: str,
    resume_path: Path | None = None,
    submit: bool = False,
    headless: bool = False,
    wait_login_seconds: int = 45,
    out_path: Path | None = None,
) -> tuple[dict[str, object], Path]:
    result = auto_apply(
        job_url=job_url,
        profile=profile,
        resume_path=resume_path,
        submit=submit,
        headless=headless,
        wait_login_seconds=wait_login_seconds,
    )

    destination = out_path or OUTPUTS_DIR / f"apply_{user_id}_{timestamp()}.json"
    save_json(destination, result)
    return result, destination
