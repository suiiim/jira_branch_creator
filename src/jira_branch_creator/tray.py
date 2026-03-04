"""시스템 트레이 모듈.

pystray를 사용하여 시스템 트레이에서 Jira 이슈 감시 및 브랜치 자동 생성을 수행합니다.

Usage:
    jira-branch-tray          # entry point
    python -m jira_branch_creator.tray
"""

from __future__ import annotations

import logging
import threading
import time
from io import BytesIO

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError as e:
    raise ImportError(
        "pystray와 Pillow가 필요합니다.\n"
        "  pip install pystray Pillow\n"
        "  또는: pip install jira-branch-creator[tray]"
    ) from e

from jira_branch_creator.config import AppConfig, load_config
from jira_branch_creator.exceptions import JiraBranchCreatorError
from jira_branch_creator.facades.workflow_facade import WorkflowFacade
from jira_branch_creator.services.jira_service import JiraService

logger = logging.getLogger(__name__)


# ─── 아이콘 생성 ─────────────────────────────────────────────────────────


def _create_icon_image(color: str = "#4A90D9", size: int = 64) -> Image.Image:
    """트레이 아이콘 이미지를 동적으로 생성합니다."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=10,
        fill=color,
    )
    # 'J' 텍스트 (Jira)
    cx, cy = size // 2, size // 2
    draw.text(
        (cx, cy),
        "J",
        fill="white",
        anchor="mm",
    )
    return img


def _create_idle_icon() -> Image.Image:
    return _create_icon_image(color="#4A90D9")


def _create_watching_icon() -> Image.Image:
    return _create_icon_image(color="#36B37E")


def _create_error_icon() -> Image.Image:
    return _create_icon_image(color="#FF5630")


# ─── 트레이 앱 ───────────────────────────────────────────────────────────


class TrayApp:
    """시스템 트레이 애플리케이션."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._facade = WorkflowFacade(config)
        self._jira = JiraService(config.jira)
        self._watching = False
        self._watch_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._seen_keys: set[str] = set()
        self._icon: pystray.Icon | None = None

    # ─── 감시 로직 ───────────────────────────────────────────────────

    def _poll_and_create(self) -> None:
        """Jira 이슈를 폴링하고 새 이슈에 대해 브랜치를 생성합니다."""
        project_key = self._config.jira.project_key
        interval = self._config.tray.poll_interval

        # 초기: 기존 이슈 수집 (브랜치 생성 안 함)
        try:
            existing = self._jira.search_recent_issues(project_key, minutes=5)
            self._seen_keys.update(issue.key for issue in existing)
            logger.info("기존 이슈 %d개 스킵", len(self._seen_keys))
        except JiraBranchCreatorError as e:
            logger.error("초기 이슈 조회 실패: %s", e)

        while not self._stop_event.is_set():
            try:
                issues = self._jira.search_recent_issues(project_key, minutes=2)
                for issue in issues:
                    if issue.key not in self._seen_keys:
                        self._seen_keys.add(issue.key)
                        logger.info("새 이슈 감지: %s - %s", issue.key, issue.summary)
                        try:
                            result = self._facade.create_branch_from_issue(issue.key)
                            logger.info("브랜치 생성 완료: %s", result.branch.name if result.branch else "N/A")
                            if self._config.tray.notify_on_create:
                                self._notify(
                                    "브랜치 생성 완료",
                                    f"{issue.key}: {result.branch.name}" if result.branch else issue.key,
                                )
                        except JiraBranchCreatorError as e:
                            logger.error("브랜치 생성 실패 (%s): %s", issue.key, e)
                            self._notify("브랜치 생성 실패", f"{issue.key}: {e}")

            except JiraBranchCreatorError as e:
                logger.error("폴링 오류: %s", e)
                self._update_icon("error")

            self._stop_event.wait(interval)

    def _notify(self, title: str, message: str) -> None:
        """시스템 알림을 전송합니다."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                logger.debug("알림 전송 실패 (지원되지 않는 플랫폼일 수 있음)")

    def _update_icon(self, state: str = "idle") -> None:
        """트레이 아이콘 상태를 업데이트합니다."""
        if not self._icon:
            return
        match state:
            case "watching":
                self._icon.icon = _create_watching_icon()
            case "error":
                self._icon.icon = _create_error_icon()
            case _:
                self._icon.icon = _create_idle_icon()

    # ─── 메뉴 액션 ──────────────────────────────────────────────────

    def _start_watching(self) -> None:
        """감시 시작."""
        if self._watching:
            return
        self._watching = True
        self._stop_event.clear()
        self._watch_thread = threading.Thread(
            target=self._poll_and_create,
            daemon=True,
            name="jira-watcher",
        )
        self._watch_thread.start()
        self._update_icon("watching")
        logger.info("감시 시작 (interval=%ds)", self._config.tray.poll_interval)

    def _stop_watching(self) -> None:
        """감시 중지."""
        if not self._watching:
            return
        self._watching = False
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
            self._watch_thread = None
        self._update_icon("idle")
        logger.info("감시 중지")

    def _toggle_watching(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """감시 토글."""
        if self._watching:
            self._stop_watching()
        else:
            self._start_watching()

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """종료."""
        self._stop_watching()
        icon.stop()

    # ─── 메뉴 구성 ──────────────────────────────────────────────────

    def _build_menu(self) -> pystray.Menu:
        """트레이 메뉴를 구성합니다."""
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: "⏸ 감시 중지" if self._watching else "▶ 감시 시작",
                self._toggle_watching,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: f"프로젝트: {self._config.jira.project_key}",
                action=None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda _: f"감시 간격: {self._config.tray.poll_interval}초",
                action=None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda _: f"감지된 이슈: {len(self._seen_keys)}개",
                action=None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._on_quit),
        )

    # ─── 실행 ────────────────────────────────────────────────────────

    def run(self) -> None:
        """트레이 앱을 실행합니다."""
        self._icon = pystray.Icon(
            name="jira-branch-creator",
            icon=_create_idle_icon(),
            title=self._config.tray.tooltip,
            menu=self._build_menu(),
        )

        if self._config.tray.autostart:
            self._start_watching()

        logger.info("시스템 트레이 시작")
        self._icon.run()


# ─── 진입점 ──────────────────────────────────────────────────────────────


def main() -> None:
    """시스템 트레이 메인 함수."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        config = load_config()
        app = TrayApp(config)
        app.run()
    except JiraBranchCreatorError as e:
        logger.error("설정 오류: %s", e)
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("종료")


if __name__ == "__main__":
    main()
