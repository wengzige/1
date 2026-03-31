#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = Path(__file__).resolve().parents[1]


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def normalize_image_src(src: str) -> str:
    normalized = src.replace("\\", "/").lstrip("./")
    if normalized.startswith(("http://", "https://")):
        return normalized
    if normalized.startswith("assets/"):
        return normalized
    pure = PurePosixPath(normalized)
    if len(pure.parts) == 1:
        return f"assets/{pure.name}"
    return normalized


def run_json_command(command: list[str]) -> tuple[object | None, str | None]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception as exc:
        return None, str(exc)

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    raw = stdout or stderr
    if completed.returncode != 0:
        return None, raw or f"command failed: {' '.join(command)}"

    try:
        return json.loads(raw), None
    except Exception as exc:
        return None, f"invalid json output: {exc}; raw={raw[:500]}"


def make_check(name: str, status: str, detail: str, *, data: object | None = None) -> dict:
    check = {"name": name, "status": status, "detail": detail}
    if data is not None:
        check["data"] = data
    return check


def add_check(checks: list[dict], name: str, status: str, detail: str, *, data: object | None = None) -> None:
    checks.append(make_check(name, status, detail, data=data))


def summarize(checks: list[dict]) -> dict:
    return {
        "pass": sum(1 for item in checks if item["status"] == "pass"),
        "warn": sum(1 for item in checks if item["status"] == "warn"),
        "fail": sum(1 for item in checks if item["status"] == "fail"),
        "skip": sum(1 for item in checks if item["status"] == "skip"),
    }


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Run mandatory WeWrite quality gates for a template article.")
    parser.add_argument("--article-dir", required=True)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any gate fails.")
    args = parser.parse_args()

    article_dir = Path(args.article_dir).resolve()
    generated_dir = article_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    report_path = generated_dir / "quality-gates.json"
    diagnose_path = generated_dir / "diagnose-report.json"
    doctor_path = generated_dir / "article-doctor-report.json"
    seo_path = generated_dir / "seo-report.json"

    checks: list[dict] = []
    artifacts: dict[str, object] = {
        "diagnose_report": str(diagnose_path),
        "article_doctor_report": str(doctor_path),
        "seo_report": str(seo_path),
    }

    article_path = article_dir / "article.md"
    metadata_path = article_dir / "draft-metadata.json"
    html_path = article_dir / "article-body.template.html"
    preview_path = article_dir / "preview.html"
    humanness_path = generated_dir / "humanness-report.json"
    image_prompts_path = generated_dir / "image-prompts.md"

    metadata: dict[str, object] = {}
    article_markdown = ""
    html = ""

    if not article_dir.exists():
        add_check(checks, "article_dir", "fail", f"article dir not found: {article_dir}")
    else:
        add_check(checks, "article_dir", "pass", f"article dir found: {article_dir}")

    for path, name in [
        (article_path, "article_md"),
        (metadata_path, "draft_metadata"),
        (html_path, "html_template"),
        (preview_path, "preview_html"),
        (humanness_path, "humanness_report"),
        (image_prompts_path, "image_prompts"),
    ]:
        status = "pass" if path.exists() else "fail"
        add_check(checks, name, status, f"{name} {'found' if path.exists() else 'missing'}: {path}")

    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            add_check(checks, "draft_metadata_json", "fail", f"draft-metadata.json invalid: {exc}")
    if article_path.exists():
        try:
            article_markdown = article_path.read_text(encoding="utf-8")
        except Exception as exc:
            add_check(checks, "article_md_utf8", "fail", f"article.md unreadable as UTF-8: {exc}")
    if html_path.exists():
        try:
            html = html_path.read_text(encoding="utf-8")
        except Exception as exc:
            add_check(checks, "html_template_utf8", "fail", f"article-body.template.html unreadable as UTF-8: {exc}")

    title = str(metadata.get("title") or "").strip()
    digest = str(metadata.get("digest") or "").strip()

    if title:
        title_bytes = utf8_len(title)
        title_status = "pass" if 5 <= title_bytes <= 64 else "fail"
        add_check(checks, "metadata_title_length", title_status, f"title bytes={title_bytes} (need 5-64)")
    else:
        add_check(checks, "metadata_title_length", "fail", "title is empty")

    if digest:
        digest_bytes = utf8_len(digest)
        digest_status = "pass" if digest_bytes <= 120 else "fail"
        add_check(checks, "metadata_digest_length", digest_status, f"digest bytes={digest_bytes} (need <=120)")
    else:
        add_check(checks, "metadata_digest_length", "fail", "digest is empty")

    if article_markdown:
        char_count = len(strip := re.sub(r"\s+", "", article_markdown))
        status = "pass" if char_count >= 200 else "warn"
        add_check(checks, "article_char_count", status, f"正文字符数={char_count} (建议 >=200)")

        image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", article_markdown)
        local_images = [normalize_image_src(item) for item in image_refs if not item.startswith(("http://", "https://"))]
        image_count_status = "pass" if len(local_images) <= 10 else "fail"
        add_check(checks, "image_count", image_count_status, f"正文图片数={len(local_images)} (need <=10)", data=local_images)

        missing_images = []
        for ref in local_images:
            candidate = article_dir / ref.replace("/", "\\")
            if not candidate.exists():
                missing_images.append(ref)
        if missing_images:
            add_check(checks, "image_assets", "fail", f"缺少正文图片文件: {', '.join(missing_images[:10])}")
        else:
            add_check(checks, "image_assets", "pass", "正文图片文件均存在")
    else:
        add_check(checks, "article_char_count", "fail", "article.md is empty or unreadable")

    cover_image = str(metadata.get("cover_image") or "assets/cover-wide.jpg").strip() or "assets/cover-wide.jpg"
    cover_path = article_dir / cover_image.replace("/", "\\")
    cover_square_path = article_dir / "assets" / "cover-square.jpg"
    add_check(checks, "cover_image", "pass" if cover_path.exists() else "fail", f"cover image: {cover_path}")
    add_check(
        checks,
        "cover_square_image",
        "pass" if cover_square_path.exists() else "fail",
        f"square cover image: {cover_square_path}",
    )

    if humanness_path.exists():
        try:
            humanness = json.loads(humanness_path.read_text(encoding="utf-8"))
            failed_checks = humanness.get("summary", {}).get("failed_checks", []) or []
            artifacts["humanness_summary"] = humanness.get("summary")
            add_check(
                checks,
                "humanness_summary",
                "warn" if failed_checks else "pass",
                f"humanness composite={humanness.get('composite_score')} failed_checks={failed_checks}",
                data=humanness.get("summary"),
            )
        except Exception as exc:
            add_check(checks, "humanness_summary", "fail", f"humanness-report.json invalid: {exc}")

    diagnose_result, diagnose_error = run_json_command([sys.executable, str(REPO_ROOT / "scripts" / "diagnose.py"), "--json"])
    if diagnose_result is None:
        add_check(checks, "diagnose", "fail", f"diagnose.py failed: {diagnose_error}")
    else:
        diagnose_path.write_text(json.dumps(diagnose_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        diagnose_summary = diagnose_result.get("summary", {})
        if diagnose_summary.get("failures", 0) > 0:
            status = "fail"
        elif diagnose_summary.get("warnings", 0) > 0:
            status = "warn"
        else:
            status = "pass"
        add_check(checks, "diagnose", status, f"diagnose summary={diagnose_summary}", data=diagnose_summary)

    doctor_result, doctor_error = run_json_command([
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(WORKFLOW_ROOT / "scripts" / "project-doctor.ps1"),
        "-ArticleDir",
        str(article_dir),
    ])
    if doctor_result is None:
        add_check(checks, "article_doctor", "fail", f"project-doctor failed: {doctor_error}")
    else:
        doctor_path.write_text(json.dumps(doctor_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        doctor_articles = doctor_result.get("articles", [])
        doctor_errors = sum(len(item.get("errors", [])) for item in doctor_articles)
        doctor_warnings = sum(len(item.get("warnings", [])) for item in doctor_articles)
        if doctor_errors > 0:
            status = "fail"
        elif doctor_warnings > 0:
            status = "warn"
        else:
            status = "pass"
        add_check(
            checks,
            "article_doctor",
            status,
            f"project-doctor errors={doctor_errors} warnings={doctor_warnings}",
            data={"errors": doctor_errors, "warnings": doctor_warnings},
        )

    if title:
        seo_result, seo_error = run_json_command([sys.executable, str(REPO_ROOT / "scripts" / "seo_keywords.py"), "--json", title])
        if seo_result is None:
            add_check(checks, "seo_keywords", "warn", f"seo_keywords.py failed: {seo_error}")
        else:
            seo_path.write_text(json.dumps(seo_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            primary = seo_result[0] if seo_result else {}
            seo_score = primary.get("seo_score", 0)
            status = "pass" if seo_score >= 1 else "warn"
            add_check(checks, "seo_keywords", status, f"title seo_score={seo_score}", data=primary)
    else:
        add_check(checks, "seo_keywords", "fail", "title missing, cannot run seo_keywords.py")

    report = {
        "article_dir": str(article_dir),
        "strict": bool(args.strict),
        "checks": checks,
        "summary": summarize(checks),
        "artifacts": artifacts,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.strict and report["summary"]["fail"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
