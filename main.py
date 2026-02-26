#!/usr/bin/env python3
"""Jira Branch Creator - CLI 진입점.

사용법:
    python main.py branch SSCVE-123              # 이슈에서 브랜치 생성
    python main.py create "이슈 제목" --type Bug  # 이슈 생성 + 브랜치 생성
    python main.py transition SSCVE-123 "진행 중" # 이슈 상태 전환
    python main.py preview SSCVE-123              # 브랜치명 미리보기
    python main.py transitions SSCVE-123          # 가능한 상태 전환 조회
"""

from __future__ import annotations

import argparse
import logging
import sys

from jira_branch_creator.config import load_config
from jira_branch_creator.exceptions import JiraBranchCreatorError
from jira_branch_creator.facades.workflow_facade import WorkflowFacade


def _setup_logging(verbose: bool) -> None:
    """로깅을 설정합니다."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _print_result(result) -> None:
    """워크플로우 결과를 출력합니다."""
    print()
    print("========================================")
    print(f"  ✅ {result.message}")
    print("========================================")
    print(f"  이슈 키  : {result.issue.key}")
    print(f"  이슈 타입: {result.issue.issue_type}")
    print(f"  요약     : {result.issue.summary}")
    print(f"  상태     : {result.issue.status}")
    if result.branch:
        print(f"  브랜치   : {result.branch.name}")
        print(f"  기준     : {result.branch.ref}")
        if result.branch.web_url:
            print(f"  URL      : {result.branch.web_url}")
    print("========================================")


# ─── 서브커맨드 핸들러 ────────────────────────────────────────────────────


def _handle_branch(facade: WorkflowFacade, args: argparse.Namespace) -> None:
    """기존 이슈에서 브랜치 생성."""
    result = facade.create_branch_from_issue(
        issue_key=args.issue_key,
        ref=args.ref,
    )
    _print_result(result)


def _handle_create(facade: WorkflowFacade, args: argparse.Namespace) -> None:
    """이슈 생성 + 브랜치 생성."""
    result = facade.create_issue_and_branch(
        summary=args.summary,
        issue_type=args.type,
        description=args.description or "",
        labels=args.labels or [],
        transition_to=args.transition,
        ref=args.ref,
    )
    _print_result(result)


def _handle_transition(facade: WorkflowFacade, args: argparse.Namespace) -> None:
    """이슈 상태 전환."""
    result = facade.transition_issue(
        issue_key=args.issue_key,
        target_status=args.status,
    )
    _print_result(result)


def _handle_preview(facade: WorkflowFacade, args: argparse.Namespace) -> None:
    """브랜치명 미리보기."""
    branch_name = facade.preview_branch_name(args.issue_key)
    print(f"\n🌿 브랜치명: {branch_name}")


def _handle_transitions(facade: WorkflowFacade, args: argparse.Namespace) -> None:
    """가능한 상태 전환 조회."""
    names = facade.get_available_transitions(args.issue_key)
    print(f"\n📋 이슈 {args.issue_key}에서 가능한 상태 전환:")
    if names:
        for name in names:
            print(f"  → {name}")
    else:
        print("  (전환 가능한 상태 없음)")


# ─── CLI 파서 ────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 구성합니다."""
    parser = argparse.ArgumentParser(
        prog="jira-branch-creator",
        description="Jira 이슈 관리 및 GitLab 브랜치 자동 생성 도구",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # branch
    p_branch = sub.add_parser("branch", help="기존 이슈에서 브랜치 생성")
    p_branch.add_argument("issue_key", help="Jira 이슈 키 (예: SSCVE-123)")
    p_branch.add_argument("--ref", default=None, help="기준 브랜치 (기본: 설정값)")

    # create
    p_create = sub.add_parser("create", help="이슈 생성 + 브랜치 생성")
    p_create.add_argument("summary", help="이슈 제목")
    p_create.add_argument("--type", default="Task", help="이슈 타입 (기본: Task)")
    p_create.add_argument("--description", "-d", default="", help="이슈 설명")
    p_create.add_argument("--labels", "-l", nargs="*", help="레이블 목록")
    p_create.add_argument("--transition", "-t", default=None, help="생성 후 전환할 상태")
    p_create.add_argument("--ref", default=None, help="기준 브랜치 (기본: 설정값)")

    # transition
    p_transition = sub.add_parser("transition", help="이슈 상태 전환")
    p_transition.add_argument("issue_key", help="Jira 이슈 키")
    p_transition.add_argument("status", help="전환할 상태명")

    # preview
    p_preview = sub.add_parser("preview", help="브랜치명 미리보기")
    p_preview.add_argument("issue_key", help="Jira 이슈 키")

    # transitions
    p_transitions = sub.add_parser("transitions", help="가능한 상태 전환 조회")
    p_transitions.add_argument("issue_key", help="Jira 이슈 키")

    return parser


# ─── 메인 ────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI 메인 함수."""
    parser = _build_parser()
    args = parser.parse_args()
    _setup_logging(args.verbose)

    try:
        config = load_config()
        facade = WorkflowFacade(config)

        handlers = {
            "branch": _handle_branch,
            "create": _handle_create,
            "transition": _handle_transition,
            "preview": _handle_preview,
            "transitions": _handle_transitions,
        }

        handler = handlers[args.command]
        handler(facade, args)

    except JiraBranchCreatorError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 중단되었습니다.")
        sys.exit(130)


if __name__ == "__main__":
    main()
