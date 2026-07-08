"""장꾸와의 채팅 패널.

펫 위에 뜨는 말풍선 스타일의 작은 채팅창. LLM 호출은 데몬 스레드에서 돌리고
결과는 시그널로 메인 스레드에 전달해 UI가 멈추지 않게 한다.
"""

import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .llm import Brain

GREETING = "왔어, 집사? 🐾 나 장꾸야. 세상에서 제일 귀여운 포메라니안이지. 뭐 도와줄까? 흥, 특별히 들어주는 거야."

STYLE = """
#panel {
    background: #FFF9EE;
    border: 2px solid #E4D3AE;
    border-radius: 14px;
}
#title { font-weight: bold; font-size: 14px; color: #4A3B2A; }
#closeBtn {
    border: none; background: transparent; font-size: 14px; color: #A08B6A;
}
#closeBtn:hover { color: #4A3B2A; }
QLabel[bubble="pet"] {
    background: #FFFFFF; border: 1px solid #E9DCC0; border-radius: 10px;
    padding: 7px 10px; color: #3A2E1E; font-size: 13px;
}
QLabel[bubble="user"] {
    background: #FFDFAE; border: 1px solid #EDC488; border-radius: 10px;
    padding: 7px 10px; color: #3A2E1E; font-size: 13px;
}
QLineEdit {
    background: #FFFFFF; border: 1px solid #E4D3AE; border-radius: 9px;
    padding: 6px 9px; font-size: 13px; color: #3A2E1E;
}
QPushButton#sendBtn {
    background: #F4B860; border: none; border-radius: 9px;
    padding: 6px 14px; font-size: 13px; font-weight: bold; color: #4A3113;
}
QPushButton#sendBtn:hover { background: #EFA83F; }
QPushButton#sendBtn:disabled { background: #EBDDC2; color: #A08B6A; }
QScrollArea { border: none; background: transparent; }
"""


class _Worker(QObject):
    reply_ready = Signal(str)

    def __init__(self, brain: Brain):
        super().__init__()
        self._brain = brain

    def ask(self, text: str) -> None:
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text: str) -> None:
        self.reply_ready.emit(self._brain.send(text))


class ChatWindow(QWidget):
    thinking_started = Signal()
    reply_shown = Signal(str)

    def __init__(self, brain: Brain):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(330, 420)
        self.setStyleSheet(STYLE)

        self._worker = _Worker(brain)
        self._worker.reply_ready.connect(self._on_reply)
        self._greeted = False

        panel = QFrame(self)
        panel.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("🐾 장꾸")
        title.setObjectName("title")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self.hide)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        messages_host = QWidget()
        messages_host.setStyleSheet("background: transparent;")
        self._messages = QVBoxLayout(messages_host)
        self._messages.setContentsMargins(2, 2, 2, 2)
        self._messages.setSpacing(6)
        self._messages.addStretch()
        self._scroll.setWidget(messages_host)
        layout.addWidget(self._scroll, 1)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("장꾸에게 말 걸기…")
        self._input.returnPressed.connect(self._send)
        self._send_btn = QPushButton("보내기")
        self._send_btn.setObjectName("sendBtn")
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(self._send_btn)
        layout.addLayout(input_row)

        # 지난 대화 기록 복원 (최근 30개)
        for role, text in brain.history[-30:]:
            self._add_bubble(text, "user" if role == "user" else "pet")
        if brain.history:
            self._greeted = True

    # ── 표시 위치 ────────────────────────────────────────────────
    def toggle_near(self, pet_window: QWidget) -> None:
        if self.isVisible():
            self.hide()
            return
        if not self._greeted:
            self._greeted = True
            self._add_bubble(GREETING, "pet")
        geo = pet_window.geometry()
        screen = pet_window.screen().availableGeometry()
        x = geo.center().x() - self.width() // 2
        x = max(screen.left() + 8, min(x, screen.right() - self.width() - 8))
        y = max(screen.top() + 8, geo.top() - self.height() - 10)
        self.move(x, y)
        self.show()
        self.raise_()
        self._input.setFocus()

    # ── 메시지 처리 ──────────────────────────────────────────────
    def _send(self) -> None:
        text = self._input.text().strip()
        if not text or not self._send_btn.isEnabled():
            return
        self._input.clear()
        self._add_bubble(text, "user")
        self._set_busy(True)
        self.thinking_started.emit()
        self._worker.ask(text)

    def _on_reply(self, reply: str) -> None:
        self._set_busy(False)
        self._add_bubble(reply, "pet")
        self.reply_shown.emit(reply)
        self._input.setFocus()

    def _set_busy(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._send_btn.setText("생각 중…" if busy else "보내기")

    def _add_bubble(self, text: str, who: str) -> None:
        bubble = QLabel(text)
        bubble.setProperty("bubble", who)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setMaximumWidth(240)
        row = QHBoxLayout()
        if who == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        self._messages.insertLayout(self._messages.count() - 1, row)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
