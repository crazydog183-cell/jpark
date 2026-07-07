"""워커 스레드에서 안전하게 메인 스레드 확인 다이얼로그를 띄우는 브리지.

도구 실행은 LLM 워커 스레드에서 일어나지만 QMessageBox는 메인 스레드에서만
만들 수 있다. 시그널(큐 연결)로 메인 스레드에 요청을 넘기고 Event로 결과를
기다린다.
"""

import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMessageBox


class ConfirmBridge(QObject):
    _request = Signal(str)

    def __init__(self):
        super().__init__()
        self._event = threading.Event()
        self._result = False
        self._request.connect(self._show)

    def confirm(self, message: str) -> bool:
        """아무 스레드에서나 호출 가능. 사용자가 '예'를 누르면 True."""
        app = QApplication.instance()
        if app is not None and QObject.thread(self) is app.thread() and (
            threading.current_thread() is threading.main_thread()
        ):
            return self._ask(message)
        self._event.clear()
        self._request.emit(message)
        if not self._event.wait(timeout=120):
            return False
        return self._result

    def _show(self, message: str) -> None:
        self._result = self._ask(message)
        self._event.set()

    @staticmethod
    def _ask(message: str) -> bool:
        answer = QMessageBox.question(
            None,
            "장꾸 🐾",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes
