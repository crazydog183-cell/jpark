"""시스템 트레이 아이콘과 설정 다이얼로그."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMenu,
    QSpinBox,
    QSystemTrayIcon,
)

from .config import DEFAULT_MODEL, Config
from .sprites import ASSETS


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("장꾸 설정 🐾")
        self._config = config

        form = QFormLayout(self)
        self._api_key = QLineEdit(config.api_key)
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Google AI Studio에서 발급한 Gemini API 키")
        self._model = QLineEdit(config.model)
        self._model.setPlaceholderText(DEFAULT_MODEL)
        self._size = QSpinBox()
        self._size.setRange(64, 200)
        self._size.setSingleStep(8)
        self._size.setValue(config.pet_size)
        self._size.setSuffix(" px")

        form.addRow("Gemini API 키", self._api_key)
        form.addRow("모델", self._model)
        form.addRow("장꾸 크기", self._size)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def edit(config: Config, parent=None) -> bool:
        """다이얼로그를 띄우고, 저장했으면 config에 반영 후 True."""
        dialog = SettingsDialog(config, parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        config.api_key = dialog._api_key.text().strip()
        config.model = dialog._model.text().strip() or DEFAULT_MODEL
        config.pet_size = dialog._size.value()
        config.save()
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
