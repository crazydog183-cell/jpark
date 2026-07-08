"""시스템 트레이 아이콘과 탭 구조 설정 다이얼로그."""

import threading
import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import __version__, autostart
from .config import DEFAULT_MODEL, Config
from .sprites import ASSETS

MODEL_CHOICES = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
API_KEY_URL = "https://aistudio.google.com/apikey"


def _slider_row(slider: QSlider, suffix: str = "") -> QWidget:
    """슬라이더 옆에 현재 값을 보여주는 행."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    value_label = QLabel(f"{slider.value()}{suffix}")
    value_label.setMinimumWidth(44)
    slider.valueChanged.connect(lambda v: value_label.setText(f"{v}{suffix}"))
    layout.addWidget(slider, 1)
    layout.addWidget(value_label)
    return row


class SettingsDialog(QDialog):
    _test_result = Signal(str)

    def __init__(self, config: Config, brain=None, on_quit=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("장꾸 설정 🐾")
        self.setMinimumWidth(400)
        self._config = config
        self._brain = brain
        self._on_quit = on_quit

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "🐾 일반")
        tabs.addTab(self._build_ai_tab(), "🤖 AI")
        tabs.addTab(self._build_info_tab(), "ℹ️ 정보")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    # ── 탭 구성 ─────────────────────────────────────────────────
    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        self._size = QSpinBox()
        self._size.setRange(64, 200)
        self._size.setSingleStep(8)
        self._size.setValue(self._config.pet_size)
        self._size.setSuffix(" px")

        self._speed = QSlider(Qt.Orientation.Horizontal)
        self._speed.setRange(20, 120)
        self._speed.setValue(int(self._config.walk_speed))

        self._activity = QSlider(Qt.Orientation.Horizontal)
        self._activity.setRange(0, 100)
        self._activity.setValue(self._config.activity)

        self._mutter = QCheckBox("가끔 혼잣말을 하고 배터리/시간 알림을 해줘요")
        self._mutter.setChecked(self._config.mutter_enabled)

        self._on_top = QCheckBox("장꾸를 항상 다른 창 위에 표시")
        self._on_top.setChecked(self._config.always_on_top)

        self._autostart = QCheckBox("Windows 시작 시 자동 실행")
        if autostart.supported():
            self._autostart.setChecked(autostart.is_enabled())
        else:
            self._autostart.setChecked(False)
            self._autostart.setEnabled(False)
            self._autostart.setText("Windows 시작 시 자동 실행 (Windows 전용)")

        form.addRow("장꾸 크기", self._size)
        form.addRow("걷는 속도", _slider_row(self._speed, " px/s"))
        form.addRow("활동성", _slider_row(self._activity))
        form.addRow("혼잣말", self._mutter)
        form.addRow("맨 위 고정", self._on_top)
        form.addRow("자동 실행", self._autostart)
        return tab

    def _build_ai_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)

        self._api_key = QLineEdit(self._config.api_key)
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Google AI Studio에서 발급한 Gemini API 키")

        self._model = QComboBox()
        self._model.setEditable(True)
        self._model.addItems(MODEL_CHOICES)
        self._model.setCurrentText(self._config.model or DEFAULT_MODEL)

        test_btn = QPushButton("연결 테스트")
        test_btn.clicked.connect(self._run_test)
        self._test_btn = test_btn
        self._test_label = QLabel("")
        self._test_label.setWordWrap(True)
        self._test_result.connect(self._show_test_result)

        clear_btn = QPushButton("대화 기록 지우기")
        clear_btn.clicked.connect(self._clear_history)

        form.addRow("API 키", self._api_key)
        form.addRow("모델", self._model)
        form.addRow(test_btn, self._test_label)
        form.addRow("기록", clear_btn)
        return tab

    def _build_info_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        about = QLabel(
            f"<b>장꾸 (Jjanggu) v{__version__}</b><br>"
            "작업표시줄 위에 사는, 자기가 세상에서 제일<br>"
            "귀여운 걸 아는 포메라니안 데스크톱 펫 🐾<br><br>"
            "왼쪽 클릭: 채팅 · 드래그: 옮기기 · 오른쪽 클릭: 메뉴"
        )
        about.setTextFormat(Qt.TextFormat.RichText)

        key_btn = QPushButton("Gemini API 키 발급 페이지 열기")
        key_btn.clicked.connect(lambda: webbrowser.open(API_KEY_URL))

        quit_btn = QPushButton("장꾸 종료 ❌")
        if self._on_quit:
            quit_btn.clicked.connect(self._on_quit)
        else:
            quit_btn.setEnabled(False)

        layout.addWidget(about)
        layout.addStretch()
        layout.addWidget(key_btn)
        layout.addWidget(quit_btn)
        return tab

    # ── 동작 ────────────────────────────────────────────────────
    def _run_test(self) -> None:
        key = self._api_key.text().strip()
        model = self._model.currentText().strip() or DEFAULT_MODEL
        if not key:
            self._test_label.setText("API 키부터 입력해줘, 집사!")
            return
        self._test_btn.setEnabled(False)
        self._test_label.setText("장꾸를 부르는 중…")

        def work():
            try:
                from google import genai

                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model=model,
                    contents="너는 도도한 포메라니안 '장꾸'야. 아주 짧게 한마디로 인사해줘.",
                )
                self._test_result.emit("✅ " + (response.text or "(빈 응답)").strip()[:80])
            except Exception as e:
                self._test_result.emit("❌ 실패: " + str(e)[:100])

        threading.Thread(target=work, daemon=True).start()

    def _show_test_result(self, text: str) -> None:
        self._test_btn.setEnabled(True)
        self._test_label.setText(text)

    def _clear_history(self) -> None:
        if self._brain is None:
            return
        answer = QMessageBox.question(
            self,
            "장꾸 🐾",
            "장꾸와의 대화 기록을 모두 지울까요?\n(장꾸가 지난 대화를 잊어버려요)",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._brain.clear_history()
            QMessageBox.information(self, "장꾸 🐾", "기록을 지웠어요. 새 채팅창부터 적용됩니다.")

    @staticmethod
    def edit(config: Config, brain=None, on_quit=None, parent=None) -> bool:
        """다이얼로그를 띄우고, 저장했으면 config 반영/자동실행 등록 후 True."""
        dialog = SettingsDialog(config, brain=brain, on_quit=on_quit, parent=parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        config.api_key = dialog._api_key.text().strip()
        config.model = dialog._model.currentText().strip() or DEFAULT_MODEL
        config.pet_size = dialog._size.value()
        config.walk_speed = float(dialog._speed.value())
        config.activity = dialog._activity.value()
        config.mutter_enabled = dialog._mutter.isChecked()
        config.always_on_top = dialog._on_top.isChecked()
        config.save()
        if autostart.supported():
            autostart.set_enabled(dialog._autostart.isChecked())
        return True


def create_tray(
    parent, on_chat, on_toggle_sleep, on_settings, on_quit
) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(QIcon(str(ASSETS / "idle.png")), parent)
    tray.setToolTip("장꾸 — 작업표시줄 포메라니안")

    menu = QMenu()
    menu.addAction("💬 채팅 열기", on_chat)
    menu.addAction("💤 재우기/깨우기", on_toggle_sleep)
    menu.addSeparator()
    menu.addAction("⚙️ 설정", on_settings)
    menu.addAction("❌ 종료", on_quit)
    tray.setContextMenu(menu)

    def _activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            on_chat()

    tray.activated.connect(_activated)
    tray.show()
    return tray
