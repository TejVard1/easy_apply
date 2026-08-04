# easy_apply

`easy_apply` is a job-application automation toolkit with both CLI and local web dashboard.

It can:
- collect candidate data from public links and multiple resumes,
- merge and structure profile data,
- parse job descriptions from URLs/text/files,
- generate a tailored resume with ATS keyword coverage,
- auto-fill application forms with portal-specific adapters.

## Current adapters

- LinkedIn Easy Apply
- Workday (common flows)
- Greenhouse (common flows)
- Lever (common flows)
- Generic fallback for other sites

## Project structure

- `easy_apply/cli.py`: CLI entrypoint
- `easy_apply/web_ui.py`: browser dashboard (`serve` command)
- `easy_apply/ingest.py`: profile + resume ingestion
- `easy_apply/jobs.py`: job parsing
- `easy_apply/tailor.py`: tailored resume + ATS score
- `easy_apply/apply_bot.py`: Playwright auto-apply engine with adapters
- `easy_apply/workflows.py`: shared pipeline helpers

## Installation

### Fast local setup (recommended)

```bash
./scripts/setup_local.sh
```

This creates `.venv` and installs base dependencies.

### Full automation setup (PDF/DOCX parsing + Playwright)

```bash
./scripts/setup_local.sh --with-automation
```

## Run

### Start dashboard UI

```bash
./scripts/start_dashboard.sh
```

Open `http://127.0.0.1:8765`.

### CLI help

```bash
python3 -m easy_apply --help
```

## CLI commands

```bash
python3 -m easy_apply init-user --help
python3 -m easy_apply ingest --help
python3 -m easy_apply parse-job --help
python3 -m easy_apply tailor --help
python3 -m easy_apply apply --help
python3 -m easy_apply pipeline --help
python3 -m easy_apply serve --help
```

## Typical workflow

1. Save profile once (`init-user` or dashboard form).
2. Ingest links and resumes (`ingest` or dashboard upload).
3. For each job link, generate tailored resume (`tailor`).
4. Run auto-apply with `submit` off first, then turn on once validated.

## Data files

- `data/users/<user_id>.json`: merged candidate profile
- `data/uploads/<user_id>/`: uploaded resumes from dashboard
- `outputs/job_*.json`: parsed job metadata
- `outputs/resume_*.md`: tailored resume markdown
- `outputs/resume_*.json`: ATS report
- `outputs/apply_*.json`: apply automation result

## Local vs hosted

### Option A: Local run (best for your use case)

Use this when one person is applying aggressively and wants minimum friction.

Pros:
- easiest to start,
- safer (credentials/login stay on her machine),
- fewer CAPTCHA/login/session issues,
- uploads use local files directly.

### Option B: Hosted web link

Possible, but requires infrastructure:
- deploy app server (Docker/VPS/Render/etc),
- secure auth layer (at least password + HTTPS),
- persistent storage for profile and uploaded resumes,
- remote browser/runtime support for Playwright,
- stricter handling of account credentials/session tokens.

For full auto-apply, local is usually more reliable than hosted.

## Docker (hosted/dashboard baseline)

Build and run dashboard:

```bash
docker build -t easy-apply .
docker run --rm -p 8765:8765 easy-apply
```

To build a lighter image without Playwright automation dependencies:

```bash
docker build --build-arg INSTALL_FULL=0 -t easy-apply:lite .
```

## Important limits

- Use only where automation is allowed by site policy and applicable law.
- Keep submit disabled until flow behavior is validated per site.
- Dynamic questions, CAPTCHAs, and anti-bot checks may still need manual input.
