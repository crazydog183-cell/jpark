"""장꾸의 혼잣말과 시스템 알림 (API 호출 없이 로컬 멘트 풀 사용).

- 한가할 때 가끔 도도한 혼잣말을 말풍선으로 띄운다
- 배터리 15% 이하(미충전)면 다급하게 경고한다
- 점심/퇴근/심야 시간대에 하루 한 번 인사한다
"""

import datetime
import random
import time

from PySide6.QtCore import QObject, QTimer

MUTTERS = [
    "하암… 좀 심심한데. 멍!",
    "나 오늘도 귀엽네. 어쩔 수 없지 ✨",
    "집사, 일 열심히 해. 난 응원만 할게. 흥.",
    "간식… 아니야, 아무것도 아니야.",
    "이 작업표시줄, 산책로로 나쁘지 않아.",
    "내 꼬리 봤어? 완벽하지. 🐾",
    "포메라니안이 왜 귀여운 줄 알아? 그야 나니까.",
    "…쳐다보지 마. 부담스러워. 조금만 봐.",
    "낮잠이나 잘까. 귀여움 유지엔 수면이 필수야.",
    "집사 모니터엔 뭐가 그렇게 재밌는 게 있어?",
    "멍! …아, 그냥 불러봤어.",
    "오늘의 귀여움 할당량, 이미 초과 달성했어.",
    "물 마셨어, 집사? 난 집사 건강까지 챙기는 펫이야. 흥.",
    "스트레칭 좀 해. 나처럼 유연해지려면 멀었지만.",
    "칭찬은 언제든 환영이야. 받아줄게.",
    "창 정리 좀 해. 내가 걸어다니기 불편하잖아. 멍!",
]

GREETINGS = {
    "lunch": (12, "점심시간이야, 집사! 밥 굶지 마. 집사가 건강해야 나를 돌보지. 멍!"),
    "evening": (18, "슬슬 퇴근할 시간 아니야? 오늘 하루 고생했어. …조, 조금 멋있었어."),
    "night": (23, "집사, 너무 늦게까지 하지 마. 내 미모도 잠을 자야 유지된다구. 💤"),
}

CHECK_MS = 20_000  # 20초마다 점검
MUTTER_GAP_S = 120  # 혼잣말 최소 간격
MUTTER_CHANCE = 0.12  # 점검마다 혼잣말 확률
BATTERY_GAP_S = 20 * 60  # 배터리 경고 최소 간격


class Mutterer(QObject):
    def __init__(self, config, behavior, bubble, pet, chat):
        super().__init__()
        self._config = config
        self._behavior = behavior
        self._bubble = bubble
        self._pet = pet
        self._chat = chat
        self._last_mutter = 0.0
        self._last_battery_warn = 0.0
        self._greeted: set[tuple[str, str]] = set()  # (slot, 날짜)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._timer.start(CHECK_MS)

    def _check(self) -> None:
        if not self._config.mutter_enabled:
            return
        if self._battery_warning():
            return
        if self._time_greeting():
            return
        self._random_mutter()

    # ── 종류별 처리 ──────────────────────────────────────────────
    def _battery_warning(self) -> bool:
        now = time.monotonic()
        if now - self._last_battery_warn < BATTERY_GAP_S:
            return False
        try:
            import psutil

            battery = psutil.sensors_battery()
        except Exception:
            return False
        if battery and not battery.power_plugged and battery.percent <= 15:
            self._last_battery_warn = now
            self._behavior.startled()
            self._say(f"집사!! 배터리 {battery.percent:.0f}%야!! 충전기 꽂아!! 멍멍!! ⚡", 6000)
            return True
        return False

    def _time_greeting(self) -> bool:
        now = datetime.datetime.now()
        today = now.date().isoformat()
        for slot, (hour, text) in GREETINGS.items():
            if now.hour == hour and (slot, today) not in self._greeted:
                self._greeted.add((slot, today))
                self._say(text, 7000)
                return True
        return False

    def _random_mutter(self) -> None:
        if self._chat.isVisible():
            return  # 대화 중엔 혼잣말 금지
        if self._behavior.forced_sleep:
            return
        now = time.monotonic()
        if now - self._last_mutter < MUTTER_GAP_S:
            return
        if random.random() > MUTTER_CHANCE:
            return
        self._last_mutter = now
        self._say(random.choice(MUTTERS))

    def _say(self, text: str, msecs: int = 4500) -> None:
        self._bubble.show_for(self._pet, text, msecs)
        self._behavior.chat_talking(len(text))
