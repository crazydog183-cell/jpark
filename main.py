"""장꾸 실행 진입점: python main.py"""

import sys

from PySide6.QtCore import QTimer
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


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Jjanggu")
    app.setQuitOnLastWindowClosed(False)  # 펫/채팅창을 닫아도 트레이에 남는다

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
