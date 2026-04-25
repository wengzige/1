#!/usr/bin/env python3
"""
Diagnose which anti-AI measures are active in this WeWrite installation.

Checks: Python deps, config.yaml, style.yaml, enhancement files, dimension variance.
Outputs a human-readable report or structured JSON.

Usage:
    python3 scripts/diagnose.py              # text report
    python3 scripts/diagnose.py --json       # JSON for agent consumption
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent

# Modules to check (import_name, package_name_for_pip)
REQUIRED_MODULES = [
    ("markdown", "markdown"),
    ("bs4", "beautifulsoup4"),
    ("cssutils", "cssutils"),
    ("requests", "requests"),
    ("yaml", "pyyaml"),
    ("pygments", "Pygments"),
    ("PIL", "Pillow"),
]

# Anti-AI weight per check (0 = no anti-AI impact, higher = more important)
WEIGHTS = {
    "style_file": 3,
    "writing_persona": 3,
    "persona_file": 2,
    "writing_config": 1,
    "playbook": 2,
    "history_articles": 1,
    "dimension_variance": 1,
    # These have 0 weight (no anti-AI impact)
    "python_packages": 0,
    "config_file": 0,
    "wechat_credentials": 0,
    "image_api_key": 0,
}

MAX_ANTI_AI_SCORE = sum(v for v in WEIGHTS.values() if v > 0)  # 13


def make_check(group, name, status, detail=None, impact=None):
    """Create a check result dict."""
    c = {"group": group, "name": name, "status": status}
    if detail is not None:
        c["detail"] = detail
    if impact is not None:
        c["impact"] = impact
    return c


def check_dependencies():
    """Group 1: Check Python package imports."""
    missing = []
    for mod_name, pip_name in REQUIRED_MODULES:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return [make_check("dependencies", "python_packages", "pass", "all installed")]
    return [make_check(
        "dependencies", "python_packages", "fail",
        f"missing: {', '.join(missing)}. Run: pip install {' '.join(missing)}",
    )]


def check_config():
    """Group 2: Check config.yaml and its fields."""
    checks = []
    config_path = SKILL_ROOT / "config.yaml"

    if not config_path.exists():
        checks.append(make_check(
            "config", "config_file", "warn",
            "not found → publish and image generation disabled",
            impact="skip_publish,skip_image_gen",
        ))
        # Can't check fields if file missing
        checks.append(make_check("config", "wechat_credentials", "warn", "no config.yaml", impact="skip_publish"))
        checks.append(make_check("config", "image_api_key", "warn", "no config.yaml", impact="skip_image_gen"))
        return checks

    checks.append(make_check("config", "config_file", "pass", "found"))

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # WeChat credentials
    wechat = cfg.get("wechat", {})
    if wechat.get("appid") and wechat.get("secret"):
        checks.append(make_check("config", "wechat_credentials", "pass", "configured"))
    else:
        checks.append(make_check("config", "wechat_credentials", "warn", "missing appid/secret", impact="skip_publish"))

    # Image API key
    image = cfg.get("image", {})
    if image.get("api_key"):
        checks.append(make_check("config", "image_api_key", "pass", "configured"))
    else:
        checks.append(make_check("config", "image_api_key", "warn", "missing → image generation will be skipped", impact="skip_image_gen"))

    return checks


def check_style():
    """Group 3: Check style.yaml and persona configuration."""
    checks = []
    style_path = SKILL_ROOT / "style.yaml"

    if not style_path.exists():
        checks.append(make_check("style", "style_file", "fail", "not found → run onboard first"))
        return checks

    checks.append(make_check("style", "style_file", "pass", "found"))

    with open(style_path, "r", encoding="utf-8") as f:
        style = yaml.safe_load(f) or {}

    # writing_persona field
    persona_name = style.get("writing_persona")
    if persona_name:
        checks.append(make_check("style", "writing_persona", "pass", persona_name))
    else:
        persona_name = "midnight-friend"
        checks.append(make_check("style", "writing_persona", "warn", "not set → defaults to midnight-friend"))

    # Persona file exists
    persona_path = SKILL_ROOT / "personas" / f"{persona_name}.yaml"
    if persona_path.exists():
        checks.append(make_check("style", "persona_file", "pass", str(persona_path.relative_to(SKILL_ROOT))))
    else:
        checks.append(make_check("style", "persona_file", "fail", f"{persona_name}.yaml not found in personas/"))

    return checks


def check_enhancements():
    """Group 4: Check writing-config, playbook, history."""
    checks = []

    # writing-config.yaml
    if (SKILL_ROOT / "writing-config.yaml").exists():
        checks.append(make_check("enhancement", "writing_config", "pass", "found"))
    else:
        checks.append(make_check(
            "enhancement", "writing_config", "warn",
            "not found → using defaults (run optimize_loop.py to tune)",
        ))

    # playbook.md
    if (SKILL_ROOT / "playbook.md").exists():
        checks.append(make_check("enhancement", "playbook", "pass", "found"))
    else:
        checks.append(make_check(
            "enhancement", "playbook", "warn",
            'not found → no learned style (say "学习我的修改" after editing)',
        ))

    # history.yaml
    history_path = SKILL_ROOT / "history.yaml"
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        articles = data if isinstance(data, list) else (data or {}).get("articles", [])
        if articles:
            checks.append(make_check("enhancement", "history_articles", "pass", f"{len(articles)} articles"))
        else:
            checks.append(make_check("enhancement", "history_articles", "warn", "file exists but empty"))
    else:
        checks.append(make_check("enhancement", "history_articles", "warn", "not found → no dedup, no dimension tracking"))

    return checks


def check_dimensions():
    """Group 5: Check dimension diversity across recent articles."""
    history_path = SKILL_ROOT / "history.yaml"
    if not history_path.exists():
        return [make_check("dimensions", "dimension_variance", "skip", "no history.yaml")]

    with open(history_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    articles = data if isinstance(data, list) else (data or {}).get("articles", [])
    # Get last 3 articles that have dimensions
    recent = [a for a in articles if a.get("dimensions")][-3:]

    if len(recent) < 3:
        return [make_check("dimensions", "dimension_variance", "skip", f"only {len(recent)} articles with dimensions (need 3)")]

    # Compare dimension sets — stringify and check uniqueness
    dim_sets = [tuple(sorted(a["dimensions"])) for a in recent]
    if len(set(dim_sets)) == len(dim_sets):
        return [make_check("dimensions", "dimension_variance", "pass", "last 3 articles have distinct dimensions")]

    return [make_check("dimensions", "dimension_variance", "warn", "dimension overlap in recent articles → cross-article fingerprint risk")]


def compute_summary(checks):
    """Compute pass/warn/fail counts, anti-AI score, and recommendations."""
    passed = sum(1 for c in checks if c["status"] == "pass")
    warnings = sum(1 for c in checks if c["status"] == "warn")
    failures = sum(1 for c in checks if c["status"] == "fail")
    skipped = sum(1 for c in checks if c["status"] == "skip")

    score = sum(WEIGHTS.get(c["name"], 0) for c in checks if c["status"] == "pass")
    pct = score / MAX_ANTI_AI_SCORE if MAX_ANTI_AI_SCORE else 0
    if pct >= 0.76:
        level = "HIGH"
    elif pct >= 0.41:
        level = "MODERATE"
    else:
        level = "LOW"

    # Build recommendations ordered by weight (highest first)
    recs = []
    non_pass = [c for c in checks if c["status"] in ("warn", "fail") and WEIGHTS.get(c["name"], 0) > 0]
    non_pass.sort(key=lambda c: WEIGHTS.get(c["name"], 0), reverse=True)
    for c in non_pass:
        name = c["name"]
        if name == "style_file":
            recs.append('Run the skill once to trigger onboard, or copy style.example.yaml to style.yaml')
        elif name == "writing_persona":
            recs.append('Add writing_persona: "midnight-friend" to style.yaml (best anti-AI detection rate)')
        elif name == "persona_file":
            recs.append(f'Persona file missing — check personas/ directory')
        elif name == "playbook":
            recs.append('Edit a generated article, then say "学习我的修改" to build playbook.md')
        elif name == "writing_config":
            recs.append('Run: python3 scripts/optimize_loop.py --topic "your topic" --iterations 10')
        elif name == "history_articles":
            recs.append("Generate your first article to start building history")
        elif name == "dimension_variance":
            recs.append("Recent articles reuse same dimensions — the pipeline will auto-fix on next run")

    return {
        "passed": passed,
        "warnings": warnings,
        "failures": failures,
        "skipped": skipped,
        "anti_ai_score": score,
        "anti_ai_max": MAX_ANTI_AI_SCORE,
        "anti_ai_level": level,
    }, recs


def file_status_map(checks):
    """Build a quick file-existence map for agent use."""
    # Extract persona name from checks instead of re-reading style.yaml
    persona_name = "midnight-friend"
    for c in checks:
        if c["name"] == "writing_persona" and c["status"] == "pass" and c.get("detail"):
            persona_name = c["detail"]
            break

    return {
        "config_yaml": (SKILL_ROOT / "config.yaml").exists(),
        "style_yaml": (SKILL_ROOT / "style.yaml").exists(),
        "writing_config_yaml": (SKILL_ROOT / "writing-config.yaml").exists(),
        "playbook_md": (SKILL_ROOT / "playbook.md").exists(),
        "history_yaml": (SKILL_ROOT / "history.yaml").exists(),
        "persona_file": f"personas/{persona_name}.yaml",
    }


def format_text(checks, summary, recs):
    """Format human-readable text report."""
    lines = ["WeWrite Anti-AI Diagnostic", "=" * 26, ""]

    current_group = None
    group_labels = {
        "dependencies": "Dependencies",
        "config": "Config",
        "style": "Style",
        "enhancement": "Enhancement",
        "dimensions": "Dimension Variance",
    }
    for c in checks:
        if c["group"] != current_group:
            if current_group is not None:
                lines.append("")
            current_group = c["group"]
            lines.append(group_labels.get(current_group, current_group))
        tag = c["status"].upper()
        label = c["name"].replace("_", " ").title()
        detail = f": {c['detail']}" if c.get("detail") else ""
        lines.append(f"  [{tag:4s}] {label}{detail}")
    lines.append("")

    p, w, f_ = summary["passed"], summary["warnings"], summary["failures"]
    sk = summary.get("skipped", 0)
    skipped_part = f", {sk} skipped" if sk > 0 else ""
    lines.append(f"Summary: {p} passed, {w} warnings, {f_} failures{skipped_part}")

    score = summary["anti_ai_score"]
    mx = summary["anti_ai_max"]
    filled = round(score / mx * 12) if mx else 0
    bar = "\u2588" * filled + "\u2591" * (12 - filled)
    lines.append(f"Anti-AI level: {bar} {summary['anti_ai_level']} ({score}/{mx})")

    if recs:
        lines.append("")
        lines.append("Top recommendations:")
        for i, r in enumerate(recs, 1):
            lines.append(f"  {i}. {r}")

    return "\n".join(lines)


def format_json(checks, summary, recs):
    """Format JSON output."""
    return json.dumps({
        "checks": checks,
        "summary": summary,
        "recommendations": recs,
        "files": file_status_map(checks),
    }, ensure_ascii=False, indent=2)


def run_all_checks():
    """Run all check groups and return combined list."""
    checks = []
    checks.extend(check_dependencies())
    checks.extend(check_config())
    checks.extend(check_style())
    checks.extend(check_enhancements())
    checks.extend(check_dimensions())
    return checks


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose which anti-AI measures are active in this WeWrite installation.",
    )
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    args = parser.parse_args()

    checks = run_all_checks()
    summary, recs = compute_summary(checks)

    if args.json:
        print(format_json(checks, summary, recs))
    else:
        print(format_text(checks, summary, recs))

    # Zero-tolerance mode: warnings are non-pass because they create hidden
    # downgrades in the publishing pipeline.
    sys.exit(1 if summary["failures"] > 0 or summary["warnings"] > 0 else 0)


if __name__ == "__main__":
    main()
