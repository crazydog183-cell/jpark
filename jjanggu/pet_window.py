"""작업표시줄 위를 돌아다니는 펫 창.

프레임 없는 투명 최상위 창에 현재 포즈 스프라이트를 그린다.
Qt.Tool 플래그로 작업표시줄에 창 자신이 나타나지 않게 한다.
"""

from PySide6.QtCore import QElapsedTimer, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from . import taskbar
from .behavior import WALKING, Behavior
from .sprites import SpriteSet

# 적응형 프레임레이트: 움직일 때만 부드럽게, 멈춰 있으면 CPU를 아낀다
ACTIVE_TICK_MS = 40  # 걷기 중 25fps
IDLE_TICK_MS = 130  # 정지 포즈 ~8fps (전환 반응성 유지)
GROUND_REFRESH_S = 5.0  # 작업표시줄 위치 재확인 주기
GRAVITY = 2600.0  # 드래그 후 낙하 가속도 px/s²


class PetWindow(QWidget):
    chat_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, sprites: SpriteSet, behavior: Behavior):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._sprites = sprites
        self._behavior = behavior
        self._pixmap = sprites.get("idle")
        self._bob = 0
        self._ground_y = 0
        self._drag_offset: QPoint | None = None
        self._dragged = False
        self._fall_vy: float | None = None  # None이 아니면 낙하 중
        self._ground_accum = 0.0

        self.setFixedSize(sprites.cell())
        self._refresh_ground()
        self._behavior.x = float(
            (self._behavior.span[0] + self._behavior.span[1]) // 2
        )

        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(ACTIVE_TICK_MS)

    def set_always_on_top(self, on: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        self.show()  # 플래그 변경 후 창을 다시 띄워야 적용된다

    def set_sprites(self, sprites: SpriteSet) -> None:
        """설정에서 크기가 바뀌면 스프라이트 세트를 교체한다."""
        self._sprites = sprites
        self._pixmap = sprites.get("idle")
        self.setFixedSize(sprites.cell())
        self._refresh_ground()

    # ── 게임 루프 ────────────────────────────────────────────────
    def _refresh_ground(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        left, right, ground_y = taskbar.get_ground(screen)
        self._ground_y = ground_y
        self._behavior.set_span(left, right, self.width())

    def _tick(self) -> None:
        # 타이머 간격이 가변이므로 실제 경과 시간으로 진행한다
        dt = min(self._clock.restart() / 1000.0, 0.25)

        self._ground_accum += dt
        if self._ground_accum >= GROUND_REFRESH_S:
            self._ground_accum = 0.0
            self._refresh_ground()

        if self._drag_offset is not None:
            return  # 드래그 중에는 자율 이동 정지

        if self._fall_vy is not None:
            self._fall(dt)
            return

        state, x, flipped, bob = self._behavior.update(dt)

        target = (round(x), self._ground_y - self.height())
        if target != (self.x(), self.y()):
            self.move(*target)

        # 보이는 내용이 실제로 바뀔 때만 리페인트
        pixmap = self._sprites.get(state, flipped)
        bob_px = round(bob)
        if pixmap is not self._pixmap or bob_px != self._bob:
            self._pixmap = pixmap
            self._bob = bob_px
            self.update()

        want = ACTIVE_TICK_MS if state == WALKING else IDLE_TICK_MS
        if self._timer.interval() != want:
            self._timer.setInterval(want)

    def _fall(self, dt: float) -> None:
        """드래그 후 공중에서 작업표시줄까지 중력 낙하."""
        self._fall_vy += GRAVITY * dt
        ground_top = self._ground_y - self.height()
        y = self.y() + self._fall_vy * dt
        if y >= ground_top:
            y = ground_top
            self._fall_vy = None
            self._behavior.startled()  # 착지하면 깜짝
        self.move(self.x(), round(y))
        pixmap = self._sprites.get("surprised", self._behavior.facing_right)
        if pixmap is not self._pixmap:
            self._pixmap = pixmap
            self._bob = 0
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 규약)
        painter = QPainter(self)
        # 하단 중앙 정렬로 그려서 포즈 크기가 달라도 발이 바닥에 붙는다
        x = (self.width() - self._pixmap.width()) // 2
        y = self.height() - self._pixmap.height() - self._bob
        painter.drawPixmap(x, y, self._pixmap)

    # ── 마우스 ──────────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self._dragged = False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            pos = event.globalPosition().toPoint() - self._drag_offset
            if (pos - self.pos()).manhattanLength() > 0:
                self._dragged = True
                self._pixmap = self._sprites.get("surprised")
                self.move(pos)
                self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        was_drag = self._dragged
        self._drag_offset = None
        self._dragged = False
        if was_drag:
            self._behavior.x = float(self.x())
            self._refresh_ground()  # span 갱신 + x 클램프
            if self.y() < self._ground_y - self.height():
                # 공중에서 놓았으면 중력 낙하 시작
                self._fall_vy = 0.0
                self._timer.setInterval(ACTIVE_TICK_MS)
            else:
                self._behavior.startled()
        else:
            self.chat_requested.emit()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = QMenu(self)
        menu.addAction("💬 채팅하기", self.chat_requested.emit)
        sleep_label = "☀️ 깨우기" if self._behavior.forced_sleep else "💤 재우기"
        menu.addAction(sleep_label, self._behavior.toggle_forced_sleep)
        menu.addSeparator()
        menu.addAction("⚙️ 설정", self.settings_requested.emit)
        menu.addAction("❌ 종료", self.quit_requested.emit)
        menu.exec(event.globalPos())
