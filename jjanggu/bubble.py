"""펫 머리 위에 잠깐 뜨는 혼잣말/알림 말풍선."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

STYLE = """
QLabel {
    background: #FFF9EE;
    border: 2px solid #E4D3AE;
    border-radius: 11px;
    padding: 7px 11px;
    color: #3A2E1E;
    font-size: 13px;
}
"""


class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(STYLE)

        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(230)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._anchor: QWidget | None = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(80)
        self._follow_timer.timeout.connect(self._reposition)

    def show_for(self, anchor: QWidget, text: str, msecs: int = 4500) -> None:
        """anchor(펫 창) 위에 text를 msecs 동안 띄운다."""
        self._anchor = anchor
        self._label.setText(text)
        self.adjustSize()
        self._reposition()
        self.show()
        self._hide_timer.start(msecs)
        self._follow_timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._follow_timer.stop()
        super().hideEvent(event)

    def _reposition(self) -> None:
        if self._anchor is None or not self._anchor.isVisible():
            self.hide()
            return
        geo = self._anchor.geometry()
        screen = (self._anchor.screen() or QApplication.primaryScreen()).availableGeometry()
        x = geo.center().x() - self.width() // 2
        x = max(screen.left() + 4, min(x, screen.right() - self.width() - 4))
        y = max(screen.top() + 4, geo.top() - self.height() - 6)
        self.move(x, y)
