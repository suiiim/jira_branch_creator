#!/usr/bin/env python3
"""
Jira Branch Creator Skill - 유효성 검증 테스트
Agent Skills 스펙에 맞는지 검증합니다.

Python 3.12+ 필요

Usage: python scripts/test_validate.py
"""

import os
import sys
import re
import json

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = 0
FAIL = 0


def check_python_version() -> None:
    if sys.version_info < (3, 12):
        print(f"❌ Python 3.12 이상이 필요합니다. 현재 버전: {sys.version}")
        sys.exit(1)


def test(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def make_branch_name_test(issue_type: str, summary: str) -> str:
    """브랜치명 생성 로직 (match-case 사용)"""
    match issue_type.lower():
        case "bug":
            prefix = "bugfix"
        case "story":
            prefix = "feature"
        case "task":
            prefix = "task"
        case "epic":
            prefix = "epic"
        case "subtask" | "sub-task":
            prefix = "feature"
        case _:
            prefix = "feature"

    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")[:50]
    key = "TEST-001"
    return f"{prefix}/{key}-{slug}" if slug else f"{prefix}/{key}"


def main() -> None:
    global PASS, FAIL

    check_python_version()

    print("========================================")
    print("  Agent Skill Validation Test")
    print("========================================")
    print(f"  Skill root : {SKILL_ROOT}")
    print(f"  Python     : {sys.version.split()[0]}")
    print()

    # ─── 1. 디렉토리 구조 검증 ───────────────────────────────────────────
    print("📁 Directory Structure")
    skill_md = os.path.join(SKILL_ROOT, "SKILL.md")
    test("SKILL.md exists", os.path.isfile(skill_md))
    test("scripts/ exists", os.path.isdir(os.path.join(SKILL_ROOT, "scripts")))
    test("references/ exists", os.path.isdir(os.path.join(SKILL_ROOT, "references")))
    test("assets/ exists", os.path.isdir(os.path.join(SKILL_ROOT, "assets")))

    for f in [
        "scripts/create_branch_from_jira.sh",
        "scripts/watch_jira.py",
        "scripts/setup.sh",
        "references/BRANCH_NAMING.md",
        "assets/config.template.json",
    ]:
        test(f"{f} exists", os.path.isfile(os.path.join(SKILL_ROOT, f)))
    print()

    # ─── 2. SKILL.md Frontmatter 검증 ────────────────────────────────────
    print("📋 SKILL.md Frontmatter")
    with open(skill_md, encoding="utf-8") as fh:
        content = fh.read()

    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    test("Frontmatter exists (--- delimiters)", fm_match is not None)

    if fm_match:
        fm = fm_match.group(1)

        name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        test("'name' field exists", name_match is not None)
        if name_match:
            name = name_match.group(1).strip()
            test("name is lowercase with hyphens only",
                 bool(re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", name)), f"got: '{name}'")
            test("name <= 64 chars", len(name) <= 64, f"got: {len(name)}")
            test("name has no consecutive hyphens", "--" not in name)

            dir_name = os.path.basename(SKILL_ROOT)
            if name == dir_name:
                test("name matches directory name", True)
            else:
                test("name matches directory name (underscore→hyphen allowed)",
                     name == dir_name.replace("_", "-"),
                     f"name='{name}', dir='{dir_name}'")

        desc_match = re.search(r"^description:\s*(.+?)(?=\n\w|\n---|\Z)", fm, re.MULTILINE | re.DOTALL)
        test("'description' field exists", desc_match is not None)
        if desc_match:
            desc = desc_match.group(1).strip()
            test("description is non-empty", len(desc) > 0)
            test("description <= 1024 chars", len(desc) <= 1024, f"got: {len(desc)}")
    print()

    # ─── 3. Python 버전 및 구문 검증 ─────────────────────────────────────
    print("🐍 Python Syntax & Version Check")
    for pf in ["scripts/watch_jira.py", "scripts/test_validate.py"]:
        path = os.path.join(SKILL_ROOT, pf)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            compile(source, path, "exec")
            test(f"{pf} syntax OK", True)

            # Python 3.12 기능 사용 여부 체크 (match-case)
            test(f"{pf} uses match-case (Python 3.10+)", "match " in source)
        except SyntaxError as e:
            test(f"{pf} syntax OK", False, str(e))
    print()

    # ─── 4. JSON 설정 파일 검증 ──────────────────────────────────────────
    print("📄 JSON Config Validation")
    config_path = os.path.join(SKILL_ROOT, "assets", "config.template.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as fh:
                data = json.load(fh)
            test("config.template.json is valid JSON", True)
            test("config has 'jira' section", "jira" in data)
            test("config has 'git' section", "git" in data)
            test("config has 'branch_naming' section", "branch_naming" in data)
        except json.JSONDecodeError as e:
            test("config.template.json is valid JSON", False, str(e))
    print()

    # ─── 5. 브랜치명 생성 로직 단위 테스트 ───────────────────────────────
    print("🌿 Branch Name Generation Tests")
    cases: list[tuple[str, str, str]] = [
        ("Bug", "Fix login error", "bugfix/TEST-001-fix-login-error"),
        ("Story", "Add user profile page", "feature/TEST-001-add-user-profile-page"),
        ("Task", "Update CI/CD pipeline", "task/TEST-001-update-ci-cd-pipeline"),
        ("Epic", "Payment system", "epic/TEST-001-payment-system"),
        ("Story", "로그인 기능 구현", "feature/TEST-001"),  # 한글만
        ("Story", "Add OAuth2 로그인", "feature/TEST-001-add-oauth2"),  # 혼합
        ("Bug", "Fix   multiple   spaces!!!", "bugfix/TEST-001-fix-multiple-spaces"),
    ]

    for itype, summary, expected in cases:
        result = make_branch_name_test(itype, summary)
        test(f'[{itype}] "{summary}" → {expected}', result == expected, f"got: {result}")
    print()

    # ─── 6. SKILL.md 크기 검증 ───────────────────────────────────────────
    print("📏 SKILL.md Size Check")
    lines = content.split("\n")
    test("SKILL.md under 500 lines (recommended)", len(lines) <= 500, f"got: {len(lines)} lines")
    test("SKILL.md under 5000 tokens (~20KB)", len(content) < 20000, f"got: {len(content)} chars")
    print()

    # ─── 결과 요약 ───────────────────────────────────────────────────────
    total = PASS + FAIL
    print("========================================")
    print(f"  Results: {PASS}/{total} passed", end="")
    print(f", {FAIL} failed" if FAIL else " 🎉")
    print("========================================")

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
