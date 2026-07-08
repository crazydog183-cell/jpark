"""장꾸의 자율 행동 상태머신.

평소에는 대기/걷기/앉기/잠자기를 랜덤하게 오가고, 채팅 이벤트가 있으면
THINKING(응답 대기) / TALKING(응답 표시) / HAPPY(마무리) 로 오버라이드된다.
x 좌표(펫 창의 좌측)와 진행 방향도 여기서 관리한다.
"""

import math
import random

IDLE = "idle"
SITTING = "sitting"
WALKING = "walking"
THINKING = "thinking"
TALKING = "talking"
SLEEPING = "sleeping"
SURPRISED = "surprised"
HAPPY = "happy"

class Behavior:
    def __init__(self, walk_speed: float = 55.0, activity: int = 60):
        self.walk_speed = walk_speed
        self.set_activity(activity)
        self.x = 200.0
        self.span = (0, 800)  # 걸을 수 있는 x 범위 (창 좌측 기준)
        self.facing_right = random.random() < 0.5
        self._state = IDLE
        self._time_left = 2.0
        self._override: str | None = None
        self._override_left = 0.0
        self._forced_sleep = False
        self._bob_t = 0.0

    # ── 외부 이벤트 ──────────────────────────────────────────────
    def set_activity(self, activity: int) -> None:
        """활동성(0=게으름~100=활발)에 따라 상태 전환 가중치를 조정한다."""
        activity = max(0, min(100, activity))
        self.activity = activity
        # (상태, 가중치, 최소 지속초, 최대 지속초)
        self._auto_states = (
            (WALKING, 10 + activity * 0.6, 3.0, 8.0),
            (IDLE, 30, 2.0, 5.0),
            (SITTING, 20, 3.0, 7.0),
            (SLEEPING, max(1.0, (100 - activity) * 0.12), 12.0, 30.0),
        )

    def set_span(self, left: int, right: int, width: int) -> None:
        self.span = (left, max(left, right - width))
        self.x = min(max(self.x, self.span[0]), self.span[1])

    def chat_thinking(self) -> None:
        self._set_override(THINKING, 120.0)  # 응답 오면 해제됨

    def chat_talking(self, reply_len: int) -> None:
        self._set_override(TALKING, min(2.0 + reply_len * 0.05, 7.0))

    def chat_done_happy(self) -> None:
        self._set_override(HAPPY, 1.8)

    def startled(self) -> None:
        self._set_override(SURPRISED, 1.2)

    def clear_override(self) -> None:
        self._override = None

    def toggle_forced_sleep(self) -> bool:
        self._forced_sleep = not self._forced_sleep
        if self._forced_sleep:
            self._override = None
        return self._forced_sleep

    @property
    def forced_sleep(self) -> bool:
        return self._forced_sleep

    def _set_override(self, state: str, duration: float) -> None:
        self._forced_sleep = False
        self._override = state
        self._override_left = duration

    # ── 틱 ──────────────────────────────────────────────────────
    def update(self, dt: float) -> tuple[str, float, bool, float]:
        """(상태, x, 좌우반전 여부, y 바운스 오프셋) 반환."""
        if self._forced_sleep:
            return SLEEPING, self.x, False, 0.0

        if self._override:
            self._override_left -= dt
            if self._override_left <= 0:
                after_talk = self._override == TALKING
                self._override = None
                if after_talk:
                    self.chat_done_happy()
                    return self.update(0)
            else:
                return self._override, self.x, False, 0.0

        self._time_left -= dt
        if self._time_left <= 0:
            self._pick_next()

        bob = 0.0
        if self._state == WALKING:
            step = self.walk_speed * dt
            self.x += step if self.facing_right else -step
            if self.x <= self.span[0]:
                self.x = float(self.span[0])
                self.facing_right = True
            elif self.x >= self.span[1]:
                self.x = float(self.span[1])
                self.facing_right = False
            self._bob_t += dt
            bob = abs(math.sin(self._bob_t * 8.0)) * 2.0

        # 걷기 스프라이트 원본이 오른쪽을 보므로, 왼쪽 이동 시 반전
        flipped = self._state == WALKING and not self.facing_right
        return self._state, self.x, flipped, bob

    def _pick_next(self) -> None:
        states = [s for s in self._auto_states if s[0] != self._state]
        total = sum(s[1] for s in states)
        r = random.uniform(0, total)
        for name, weight, lo, hi in states:
            r -= weight
            if r <= 0:
                self._state = name
                self._time_left = random.uniform(lo, hi)
                break
        if self._state == WALKING and random.random() < 0.5:
            self.facing_right = not self.facing_right
