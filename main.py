"""장꾸 실행 진입점: python main.py"""

import sys
import traceback

from PySide6.QtCore import QDir, QLockFile, QTimer
from PySide6.QtWidgets import QApplication

from jjanggu import tools
from jjanggu.behavior import Behavior
from jjanggu.bubble import SpeechBubble
from jjanggu.chat_window import ChatWindow
from jjanggu.config import Config
from jjanggu.confirm import ConfirmBridge
from jjanggu.llm import Brain
from jjanggu.mutter import Mutterer
from jjanggu.pet_window import PetWindow
from jjanggu.sprites import SpriteSet
from jjanggu.tray import SettingsDialog, create_tray


def _install_crash_log() -> None:
    """예기치 못한 예외를 %APPDATA%/Jjanggu/error.log 에 남긴다."""
    from jjanggu.config import config_dir

    def hook(exc_type, exc, tb):
        try:
            path = config_dir() / "error.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                traceback.print_exception(exc_type, exc, tb, file=f)
        except OSError:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def main() -> int:
    _install_crash_log()
    app = QApplication(sys.argv)
    app.setApplicationName("Jjanggu")
    app.setQuitOnLastWindowClosed(False)  # 펫/채팅창을 닫아도 트레이에 남는다

    # 단일 인스턴스: 자동 실행 + 수동 실행이 겹쳐도 장꾸는 한 마리만
    lock = QLockFile(QDir.tempPath() + "/jjanggu.lock")
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        print("장꾸가 이미 실행 중이에요. (한 마리면 충분히 귀여워요)")
        return 0

    config = Config.load()
    behavior = Behavior(config.walk_speed, config.activity)
    sprites = SpriteSet(config.pet_size)
    pet = PetWindow(sprites, behavior)
    pet.set_always_on_top(config.always_on_top)
    brain = Brain(config)
    chat = ChatWindow(brain)
    bubble = SpeechBubble()
    mutterer = Mutterer(config, behavior, bubble, pet, chat)  # noqa: F841

    confirm = ConfirmBridge()
    tools.set_confirmer(confirm.confirm)

    def open_chat() -> None:
        chat.toggle_near(pet)

    def open_settings() -> None:
        old_size = config.pet_size
        if not SettingsDialog.edit(config, brain=brain, on_quit=app.quit):
            return
        brain.reset()
        behavior.walk_speed = config.walk_speed
        behavior.set_activity(config.activity)
        pet.set_always_on_top(config.always_on_top)
        if config.pet_size != old_size:
            pet.set_sprites(SpriteSet(config.pet_size))

    pet.chat_requested.connect(open_chat)
    pet.settings_requested.connect(open_settings)
    pet.quit_requested.connect(app.quit)
    chat.thinking_started.connect(behavior.chat_thinking)
    chat.reply_shown.connect(lambda reply: behavior.chat_talking(len(reply)))

    tray = create_tray(  # noqa: F841 (참조 유지용)
        app,
        on_chat=open_chat,
        on_toggle_sleep=behavior.toggle_forced_sleep,
        on_settings=open_settings,
        on_quit=app.quit,
    )

    pet.show()
    if not config.api_key:
        QTimer.singleShot(800, open_settings)  # 첫 실행이면 바로 키 입력 안내

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
