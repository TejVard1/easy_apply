from __future__ import annotations

import argparse
from pathlib import Path

from .storage import ensure_dirs, load_json, load_user_profile, save_user_profile
from .web_ui import run_server
from .workflows import (
    generate_tailored_resume,
    job_from_inputs,
    parse_job_to_json,
    run_apply,
)


def _print(text: str) -> None:
    print(text)


def cmd_init_user(args: argparse.Namespace) -> int:
    ensure_dirs()

    profile = load_user_profile(args.user_id)
    if args.full_name:
        profile.full_name = args.full_name
    if args.email:
        profile.email = args.email
    if args.phone:
        profile.phone = args.phone
    if args.location:
        profile.location = args.location
    if args.linkedin_url:
        profile.linkedin_url = args.linkedin_url
    if args.github_url:
        profile.github_url = args.github_url
    if args.portfolio_url:
        profile.portfolio_url = args.portfolio_url
    if args.summary:
        profile.summary = args.summary
    if args.skills:
        existing = {skill.lower() for skill in profile.skills}
        for skill in args.skills.split(","):
            candidate = skill.strip()
            if candidate and candidate.lower() not in existing:
                profile.skills.append(candidate)
                existing.add(candidate.lower())

    path = save_user_profile(profile)
    _print(f"Saved profile -> {path}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    ensure_dirs()

    from .ingest import ingest_sources

    profile = load_user_profile(args.user_id)
    manual_fields = {
        "full_name": args.full_name,
        "email": args.email,
        "phone": args.phone,
        "location": args.location,
        "linkedin_url": args.linkedin_url,
        "github_url": args.github_url,
        "portfolio_url": args.portfolio_url,
        "summary": args.summary,
        "skills": args.skills,
    }

    resume_paths = [Path(path) for path in (args.resume or [])]
    updated = ingest_sources(
        profile=profile,
        profile_urls=args.profile_url or [],
        resume_paths=resume_paths,
        manual_fields=manual_fields,
    )

    path = save_user_profile(updated)
    _print(f"Ingestion complete -> {path}")
    _print(f"Skills captured: {len(updated.skills)}")
    _print(f"Experience entries: {len(updated.experiences)}")
    return 0


def cmd_parse_job(args: argparse.Namespace) -> int:
    ensure_dirs()

    job = job_from_inputs(job_url=args.job_url, job_file=args.job_file, job_text=args.job_text)
    out_path = parse_job_to_json(job, Path(args.out) if args.out else None)

    _print(f"Parsed job -> {out_path}")
    _print(f"Title: {job.title}")
    _print(f"Company: {job.company}")
    _print(f"Keywords extracted: {len(job.keywords)}")
    return 0


def _load_job_for_tailoring(args: argparse.Namespace):
    from .models import JobPosting

    if args.job_json:
        return JobPosting.from_dict(load_json(Path(args.job_json)))
    return job_from_inputs(job_url=args.job_url, job_file=args.job_file, job_text=args.job_text)


def cmd_tailor(args: argparse.Namespace) -> int:
    ensure_dirs()

    profile = load_user_profile(args.user_id)
    job = _load_job_for_tailoring(args)

    tailored, md_path, json_path = generate_tailored_resume(
        profile=profile,
        job=job,
        user_id=args.user_id,
        out_md=Path(args.out_md) if args.out_md else None,
        out_json=Path(args.out_json) if args.out_json else None,
    )

    _print(f"Tailored resume markdown -> {md_path}")
    _print(f"ATS report -> {json_path}")
    _print(f"ATS score: {tailored.ats_score}")
    if tailored.missing_keywords:
        _print(f"Missing keywords (top 10): {', '.join(tailored.missing_keywords[:10])}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    ensure_dirs()

    profile = load_user_profile(args.user_id)
    resume_path = Path(args.resume_file) if args.resume_file else None
    out_path = Path(args.out) if args.out else None

    result, saved_path = run_apply(
        profile=profile,
        user_id=args.user_id,
        job_url=args.job_url,
        resume_path=resume_path,
        submit=args.submit,
        headless=args.headless,
        wait_login_seconds=args.wait_login_seconds,
        out_path=out_path,
    )

    _print(f"Application flow result -> {saved_path}")
    _print(f"Adapter: {result.get('adapter', 'unknown')}")
    _print(f"Flow: {result.get('flow', 'unknown')}")
    _print(f"Filled fields: {result.get('filled_fields', 0)}")
    _print(f"Resume uploaded: {result.get('resume_uploaded', False)}")
    _print(f"Submitted: {result.get('submitted', False)}")
    if result.get("error"):
        _print(f"Error: {result['error']}")
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    ensure_dirs()

    profile = load_user_profile(args.user_id)
    job = job_from_inputs(job_url=args.job_url)

    _, out_md, out_json = generate_tailored_resume(profile=profile, job=job, user_id=args.user_id)

    resume_path = Path(args.resume_file) if args.resume_file else None
    result, out_apply = run_apply(
        profile=profile,
        user_id=args.user_id,
        job_url=args.job_url,
        resume_path=resume_path,
        submit=args.submit,
        headless=args.headless,
        wait_login_seconds=45,
    )

    _print(f"Resume generated -> {out_md}")
    _print(f"ATS report -> {out_json}")
    _print(f"Application result -> {out_apply}")
    _print(f"Adapter: {result.get('adapter', 'unknown')}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    run_server(host=args.host, port=args.port)
    return 0


def _add_common_profile_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--full-name", default="", help="Manual override")
    parser.add_argument("--email", default="", help="Manual override")
    parser.add_argument("--phone", default="", help="Manual override")
    parser.add_argument("--location", default="", help="Manual override")
    parser.add_argument("--linkedin-url", default="", help="Manual override")
    parser.add_argument("--github-url", default="", help="Manual override")
    parser.add_argument("--portfolio-url", default="", help="Manual override")
    parser.add_argument("--summary", default="", help="Manual override")
    parser.add_argument("--skills", default="", help="Comma separated skills")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-apply",
        description="Automate profile ingestion, resume tailoring, and application form filling",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-user", help="Create/update a user profile")
    p_init.add_argument("user_id", help="Stable profile id")
    _add_common_profile_fields(p_init)
    p_init.set_defaults(handler=cmd_init_user)

    p_ingest = subparsers.add_parser("ingest", help="Ingest profile URLs and resumes")
    p_ingest.add_argument("user_id", help="Profile id")
    p_ingest.add_argument("--profile-url", action="append", default=[], help="Public profile URL (repeatable)")
    p_ingest.add_argument("--resume", action="append", default=[], help="Resume path (repeatable)")
    _add_common_profile_fields(p_ingest)
    p_ingest.set_defaults(handler=cmd_ingest)

    p_job = subparsers.add_parser("parse-job", help="Parse job posting")
    p_job.add_argument("--job-url", default="", help="Job URL")
    p_job.add_argument("--job-file", default=None, help="Local job description file")
    p_job.add_argument("--job-text", default=None, help="Raw job description text")
    p_job.add_argument("--out", default=None, help="Output JSON path")
    p_job.set_defaults(handler=cmd_parse_job)

    p_tailor = subparsers.add_parser("tailor", help="Generate tailored resume for a job")
    p_tailor.add_argument("user_id", help="Profile id")
    p_tailor.add_argument("--job-url", default="", help="Job URL")
    p_tailor.add_argument("--job-file", default=None, help="Local job description text file")
    p_tailor.add_argument("--job-text", default=None, help="Raw job description")
    p_tailor.add_argument("--job-json", default=None, help="Parsed job JSON from parse-job")
    p_tailor.add_argument("--out-md", default=None, help="Output resume markdown")
    p_tailor.add_argument("--out-json", default=None, help="Output ATS metadata JSON")
    p_tailor.set_defaults(handler=cmd_tailor)

    p_apply = subparsers.add_parser("apply", help="Auto-fill/apply on application page")
    p_apply.add_argument("user_id", help="Profile id")
    p_apply.add_argument("--job-url", required=True, help="Direct application URL")
    p_apply.add_argument("--resume-file", default=None, help="Resume file to upload")
    p_apply.add_argument("--submit", action="store_true", help="Actually submit")
    p_apply.add_argument("--headless", action="store_true", help="Run browser headless")
    p_apply.add_argument("--wait-login-seconds", type=int, default=45, help="Wait time for login/MFA")
    p_apply.add_argument("--out", default=None, help="Output result JSON")
    p_apply.set_defaults(handler=cmd_apply)

    p_pipe = subparsers.add_parser("pipeline", help="Parse + tailor + auto-apply")
    p_pipe.add_argument("user_id", help="Profile id")
    p_pipe.add_argument("--job-url", required=True, help="Job/application URL")
    p_pipe.add_argument("--resume-file", default=None, help="Resume file for upload")
    p_pipe.add_argument("--submit", action="store_true", help="Actually submit")
    p_pipe.add_argument("--headless", action="store_true", help="Run browser headless")
    p_pipe.set_defaults(handler=cmd_pipeline)

    p_serve = subparsers.add_parser("serve", help="Run local web dashboard")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host bind address")
    p_serve.add_argument("--port", type=int, default=8765, help="Port")
    p_serve.set_defaults(handler=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        handler = getattr(args, "handler")
        return handler(args)
    except Exception as exc:  # pylint: disable=broad-except
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
