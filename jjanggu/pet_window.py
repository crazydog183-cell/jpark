"""작업표시줄 위를 돌아다니는 펫 창.

프레임 없는 투명 최상위 창에 현재 포즈 스프라이트를 그린다.
Qt.Tool 플래그로 작업표시줄에 창 자신이 나타나지 않게 한다.
"""

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from . import taskbar
from .behavior import Behavior
from .sprites import SpriteSet

TICK_MS = 40  # 25fps
GROUND_REFRESH_TICKS = 125  # 5초마다 작업표시줄 위치 재확인


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
        self._bob = 0.0
        self._ground_y = 0
        self._drag_offset: QPoint | None = None
        self._dragged = False
        self._tick_count = 0

        self.setFixedSize(sprites.cell())
        self._refresh_ground()
        self._behavior.x = float(
            (self._behavior.span[0] + self._behavior.span[1]) // 2
        )

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

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
        self._tick_count += 1
        if self._tick_count % GROUND_REFRESH_TICKS == 0:
            self._refresh_ground()

        if self._drag_offset is not None:
            return  # 드래그 중에는 자율 이동 정지

        state, x, flipped, bob = self._behavior.update(TICK_MS / 1000.0)
        self._pixmap = self._sprites.get(state, flipped)
        self._bob = bob
        self.move(round(x), self._ground_y - self.height())
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 규약)
        painter = QPainter(self)
        # 하단 중앙 정렬로 그려서 포즈 크기가 달라도 발이 바닥에 붙는다
        x = (self.width() - self._pixmap.width()) // 2
        y = self.height() - self._pixmap.height() - round(self._bob)
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
            # 어디에 놓든 다시 작업표시줄 위로 스냅
            self._behavior.x = float(self.x())
            self._refresh_ground()  # span 갱신 + x 클램프
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
