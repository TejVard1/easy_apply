from __future__ import annotations

import cgi
import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from .config import UPLOADS_DIR
from .ingest import ingest_sources
from .storage import ensure_dirs, load_user_profile, save_user_profile
from .workflows import generate_tailored_resume, job_from_inputs, parse_job_to_json, run_apply, timestamp


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("._")
    return cleaned or "upload.bin"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "submit"}


def _first(values: dict[str, list[str]], key: str, default: str = "") -> str:
    item = values.get(key, [])
    return item[0].strip() if item else default


def _split_lines_and_commas(text: str) -> list[str]:
    parts = []
    for line in text.splitlines():
        for chunk in line.split(","):
            cleaned = chunk.strip()
            if cleaned:
                parts.append(cleaned)
    return parts


def _save_uploads(user_id: str, uploads: list[cgi.FieldStorage]) -> list[Path]:
    if not uploads:
        return []

    user_dir = UPLOADS_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for upload in uploads:
        if not upload.filename or not upload.file:
            continue
        filename = _safe_filename(upload.filename)
        target = user_dir / f"{timestamp()}_{filename}"
        data = upload.file.read()
        target.write_bytes(data)
        saved_paths.append(target)

    return saved_paths


def _extract_form(handler: BaseHTTPRequestHandler) -> tuple[dict[str, list[str]], dict[str, list[cgi.FieldStorage]]]:
    content_type = handler.headers.get("Content-Type", "")
    values: dict[str, list[str]] = {}
    files: dict[str, list[cgi.FieldStorage]] = {}

    if "multipart/form-data" in content_type:
        form = cgi.FieldStorage(
            fp=handler.rfile,
            headers=handler.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
            keep_blank_values=True,
        )

        if not form.list:
            return values, files

        for item in form.list:
            if item.filename:
                files.setdefault(item.name, []).append(item)
            else:
                values.setdefault(item.name, []).append((item.value or "").strip())
        return values, files

    length = int(handler.headers.get("Content-Length", "0"))
    payload = handler.rfile.read(length).decode("utf-8", errors="ignore") if length else ""
    parsed = parse_qs(payload, keep_blank_values=True)
    values = {key: [v.strip() for v in vals] for key, vals in parsed.items()}
    return values, files


def _render_home(status: str = "", payload: dict[str, Any] | None = None, error: str = "") -> str:
    status_block = ""
    if error:
        status_block = f"<section class='notice error'><h3>Error</h3><p>{html.escape(error)}</p></section>"
    elif status:
        status_block = f"<section class='notice ok'><h3>Status</h3><p>{html.escape(status)}</p></section>"

    payload_block = ""
    if payload:
        pretty = html.escape(json.dumps(payload, indent=2, default=str))
        payload_block = f"<section class='result'><h3>Result</h3><pre>{pretty}</pre></section>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Easy Apply Dashboard</title>
  <style>
    :root {{
      --bg-0: #f6f7f1;
      --bg-1: #eef2de;
      --ink-0: #1d2a1f;
      --ink-1: #3d4d40;
      --brand: #0f766e;
      --brand-2: #ca8a04;
      --card: #ffffff;
      --border: #d8dcc9;
      --error: #b91c1c;
      --ok: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink-0);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: radial-gradient(circle at 10% 10%, var(--bg-1), var(--bg-0));
    }}
    .wrap {{ max-width: 1160px; margin: 0 auto; padding: 20px; }}
    header {{
      padding: 20px;
      border: 1px solid var(--border);
      border-radius: 16px;
      background: linear-gradient(135deg, #ffffff, #eef6ee);
      box-shadow: 0 10px 20px rgba(20, 40, 20, 0.06);
      margin-bottom: 16px;
    }}
    h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: -0.02em; }}
    .sub {{ color: var(--ink-1); margin: 0; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 14px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 8px 16px rgba(20, 40, 20, 0.04);
    }}
    h2 {{ margin-top: 0; font-size: 18px; }}
    label {{ display: block; margin: 8px 0 4px; font-size: 13px; color: var(--ink-1); }}
    input, textarea {{
      width: 100%;
      border: 1px solid #c5ccb8;
      border-radius: 10px;
      padding: 10px;
      font-size: 14px;
      background: #fbfdf7;
      color: var(--ink-0);
    }}
    textarea {{ min-height: 86px; resize: vertical; }}
    .actions {{ margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: transform .12s ease;
    }}
    button:hover {{ transform: translateY(-1px); }}
    .primary {{ background: var(--brand); color: #fff; }}
    .secondary {{ background: var(--brand-2); color: #161616; }}
    .hint {{ color: var(--ink-1); font-size: 12px; margin-top: 6px; }}
    .notice {{ border-radius: 12px; border: 1px solid var(--border); padding: 12px; margin-bottom: 14px; }}
    .notice.ok {{ border-color: #8cd7d1; background: #f0fdfa; }}
    .notice.error {{ border-color: #f5b0b0; background: #fef2f2; color: var(--error); }}
    .result {{
      margin-bottom: 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #0f172a;
      color: #e2e8f0;
      padding: 10px;
    }}
    pre {{ margin: 0; overflow-x: auto; font-size: 12px; }}
    .inline {{ display: flex; gap: 8px; }}
    .inline > div {{ flex: 1; }}
    .checkbox {{ display: flex; align-items: center; gap: 8px; margin-top: 8px; }}
    .checkbox input {{ width: auto; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <header>
      <h1>Easy Apply Dashboard</h1>
      <p class=\"sub\">Collect profile data, tailor ATS resumes, and run apply automation from one page.</p>
    </header>
    {status_block}
    {payload_block}
    <section class=\"grid\">
      <article class=\"card\">
        <h2>1) Save Profile</h2>
        <form method=\"post\" action=\"/profile/save\">
          <label>User ID</label><input name=\"user_id\" required placeholder=\"teja\" />
          <div class=\"inline\">
            <div><label>Full Name</label><input name=\"full_name\" /></div>
            <div><label>Email</label><input name=\"email\" /></div>
          </div>
          <div class=\"inline\">
            <div><label>Phone</label><input name=\"phone\" /></div>
            <div><label>Location</label><input name=\"location\" /></div>
          </div>
          <label>LinkedIn URL</label><input name=\"linkedin_url\" />
          <label>GitHub URL</label><input name=\"github_url\" />
          <label>Portfolio URL</label><input name=\"portfolio_url\" />
          <label>Summary</label><textarea name=\"summary\"></textarea>
          <label>Skills (comma-separated)</label><input name=\"skills\" placeholder=\"python, fastapi, aws\" />
          <div class=\"actions\"><button class=\"primary\" type=\"submit\">Save Profile</button></div>
        </form>
      </article>

      <article class=\"card\">
        <h2>2) Ingest URLs + Resumes</h2>
        <form method=\"post\" action=\"/profile/ingest\" enctype=\"multipart/form-data\">
          <label>User ID</label><input name=\"user_id\" required />
          <label>Profile URLs (one per line)</label>
          <textarea name=\"profile_urls\" placeholder=\"https://linkedin.com/in/...&#10;https://github.com/...\"></textarea>
          <label>Resume Uploads (multiple)</label>
          <input type=\"file\" name=\"resume_files\" multiple />
          <div class=\"actions\"><button class=\"secondary\" type=\"submit\">Ingest Data</button></div>
          <p class=\"hint\">Uploaded files are stored under data/uploads/&lt;user_id&gt;/</p>
        </form>
      </article>

      <article class=\"card\">
        <h2>3) Tailor Resume</h2>
        <form method=\"post\" action=\"/job/tailor\">
          <label>User ID</label><input name=\"user_id\" required />
          <label>Job URL</label><input name=\"job_url\" placeholder=\"https://company.com/careers/...\" />
          <label>Or Job Text</label><textarea name=\"job_text\" placeholder=\"Paste JD text if URL not available\"></textarea>
          <div class=\"actions\"><button class=\"primary\" type=\"submit\">Generate Tailored Resume</button></div>
        </form>
      </article>

      <article class=\"card\">
        <h2>4) Auto Apply</h2>
        <form method=\"post\" action=\"/job/apply\" enctype=\"multipart/form-data\">
          <label>User ID</label><input name=\"user_id\" required />
          <label>Application URL</label><input name=\"job_url\" required />
          <label>Resume upload (optional)</label><input type=\"file\" name=\"resume_file\" />
          <label>Or resume path on server (optional)</label><input name=\"resume_path\" placeholder=\"/abs/path/resume.pdf\" />
          <div class=\"inline\">
            <div><label>Wait Login Seconds</label><input name=\"wait_login_seconds\" value=\"45\" /></div>
            <div><label>Headless (true/false)</label><input name=\"headless\" value=\"false\" /></div>
          </div>
          <div class=\"checkbox\"><input type=\"checkbox\" name=\"submit\" value=\"true\" /><span>Actually submit the application</span></div>
          <div class=\"actions\"><button class=\"secondary\" type=\"submit\">Run Apply Flow</button></div>
          <p class=\"hint\">Keep submit unchecked while validating behavior.</p>
        </form>
      </article>
    </section>
  </div>
</body>
</html>
"""


class EasyApplyHandler(BaseHTTPRequestHandler):
    server_version = "EasyApplyHTTP/0.1"

    def log_message(self, format: str, *args: object) -> None:
        # Keep logs concise for interactive local runs.
        print("[web] " + format % args)

    def _write_html(self, body: str, status_code: int = 200) -> None:
        payload = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/":
            self._write_html(_render_home(error="Route not found"), status_code=404)
            return
        self._write_html(_render_home())

    def do_POST(self) -> None:  # noqa: N802
        values, files = _extract_form(self)

        try:
            if self.path == "/profile/save":
                message, payload = self._handle_profile_save(values)
            elif self.path == "/profile/ingest":
                message, payload = self._handle_profile_ingest(values, files)
            elif self.path == "/job/tailor":
                message, payload = self._handle_job_tailor(values)
            elif self.path == "/job/apply":
                message, payload = self._handle_job_apply(values, files)
            else:
                self._write_html(_render_home(error="Route not found"), status_code=404)
                return
        except Exception as exc:  # pylint: disable=broad-except
            self._write_html(_render_home(error=str(exc)), status_code=400)
            return

        self._write_html(_render_home(status=message, payload=payload), status_code=200)

    def _handle_profile_save(self, values: dict[str, list[str]]) -> tuple[str, dict[str, Any]]:
        user_id = _first(values, "user_id")
        if not user_id:
            raise ValueError("user_id is required")

        profile = load_user_profile(user_id)
        mapping = {
            "full_name": "full_name",
            "email": "email",
            "phone": "phone",
            "location": "location",
            "linkedin_url": "linkedin_url",
            "github_url": "github_url",
            "portfolio_url": "portfolio_url",
            "summary": "summary",
        }

        for field_name, attr in mapping.items():
            value = _first(values, field_name)
            if value:
                setattr(profile, attr, value)

        skill_text = _first(values, "skills")
        if skill_text:
            existing = {item.lower() for item in profile.skills}
            for skill in _split_lines_and_commas(skill_text):
                if skill.lower() not in existing:
                    profile.skills.append(skill)
                    existing.add(skill.lower())

        profile_path = save_user_profile(profile)
        payload: dict[str, Any] = {
            "user_id": user_id,
            "profile_path": str(profile_path),
            "skills_count": len(profile.skills),
        }
        return "Profile saved", payload

    def _handle_profile_ingest(
        self,
        values: dict[str, list[str]],
        files: dict[str, list[cgi.FieldStorage]],
    ) -> tuple[str, dict[str, Any]]:
        user_id = _first(values, "user_id")
        if not user_id:
            raise ValueError("user_id is required")

        profile_urls = _split_lines_and_commas(_first(values, "profile_urls"))
        resume_uploads = files.get("resume_files", [])
        resume_paths = _save_uploads(user_id, resume_uploads)

        profile = load_user_profile(user_id)
        updated = ingest_sources(
            profile=profile,
            profile_urls=profile_urls,
            resume_paths=resume_paths,
            manual_fields={},
        )
        profile_path = save_user_profile(updated)

        payload: dict[str, Any] = {
            "user_id": user_id,
            "profile_path": str(profile_path),
            "profile_urls_ingested": profile_urls,
            "resume_files_saved": [str(path) for path in resume_paths],
            "skills_count": len(updated.skills),
            "experiences_count": len(updated.experiences),
        }
        return "Ingestion complete", payload

    def _handle_job_tailor(self, values: dict[str, list[str]]) -> tuple[str, dict[str, Any]]:
        user_id = _first(values, "user_id")
        if not user_id:
            raise ValueError("user_id is required")

        job_url = _first(values, "job_url")
        job_text = _first(values, "job_text")

        profile = load_user_profile(user_id)
        job = job_from_inputs(job_url=job_url, job_text=job_text)
        job_json_path = parse_job_to_json(job)
        tailored, md_path, ats_path = generate_tailored_resume(profile=profile, job=job, user_id=user_id)

        payload: dict[str, Any] = {
            "user_id": user_id,
            "job_title": job.title,
            "company": job.company,
            "job_json": str(job_json_path),
            "resume_markdown": str(md_path),
            "ats_report": str(ats_path),
            "ats_score": tailored.ats_score,
            "matched_keywords": tailored.matched_keywords[:20],
            "missing_keywords": tailored.missing_keywords[:20],
        }
        return "Tailored resume generated", payload

    def _handle_job_apply(
        self,
        values: dict[str, list[str]],
        files: dict[str, list[cgi.FieldStorage]],
    ) -> tuple[str, dict[str, Any]]:
        user_id = _first(values, "user_id")
        job_url = _first(values, "job_url")
        if not user_id or not job_url:
            raise ValueError("user_id and job_url are required")

        uploaded = _save_uploads(user_id, files.get("resume_file", []))
        resume_path_value = _first(values, "resume_path")

        resume_path: Path | None = None
        if uploaded:
            resume_path = uploaded[0]
        elif resume_path_value:
            resume_path = Path(resume_path_value)

        wait_login_text = _first(values, "wait_login_seconds", "45")
        try:
            wait_login_seconds = max(5, min(300, int(wait_login_text)))
        except ValueError:
            wait_login_seconds = 45

        submit = _truthy(_first(values, "submit", ""))
        headless = _truthy(_first(values, "headless", "false"))

        profile = load_user_profile(user_id)
        result, out_path = run_apply(
            profile=profile,
            user_id=user_id,
            job_url=job_url,
            resume_path=resume_path,
            submit=submit,
            headless=headless,
            wait_login_seconds=wait_login_seconds,
        )

        payload: dict[str, Any] = {
            "result_path": str(out_path),
            "resume_path": str(resume_path) if resume_path else "",
            "flow": result.get("flow", "unknown"),
            "adapter": result.get("adapter", "unknown"),
            "filled_fields": result.get("filled_fields", 0),
            "submitted": result.get("submitted", False),
            "error": result.get("error", ""),
        }
        return "Apply flow completed", payload


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    ensure_dirs()
    httpd = ThreadingHTTPServer((host, port), EasyApplyHandler)
    print(f"Easy Apply dashboard running on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
