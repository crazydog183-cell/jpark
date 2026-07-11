"""offscreen 스모크 테스트 — GUI 없이 전 모듈을 검증한다.

실행: QT_QPA_PLATFORM=offscreen python tests/smoke_test.py
"""

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

app = QApplication([])
app.setQuitOnLastWindowClosed(False)

# 대화 기록이 실제 사용자 파일을 건드리지 않게 임시 폴더로 격리
import jjanggu.llm as llm_mod

_tmp = Path(tempfile.mkdtemp(prefix="jjanggu_test_"))
llm_mod.config_dir = lambda: _tmp

# 1) 스프라이트 로드/반전
from jjanggu.sprites import STATES, SpriteSet

sprites = SpriteSet(96)
for s in STATES:
    assert not sprites.get(s).isNull() and sprites.get(s).height() > 0, s
    assert not sprites.get(s, flipped=True).isNull(), s
print("1. 스프라이트 8종 로드/반전 OK, cell =", sprites.cell())

# 2) 바닥 계산
from jjanggu import taskbar

left, right, ground = taskbar.get_ground(app.primaryScreen())
assert right > left and ground > 0
print(f"2. 바닥 계산 OK: span=({left},{right}) ground_y={ground}")

# 3) 행동 상태머신 — 60초 시뮬레이션
from jjanggu.behavior import Behavior

b = Behavior()
b.set_span(left, right, 100)
seen = set()
for _ in range(1500):
    state, x, flipped, bob = b.update(0.04)
    seen.add(state)
    assert left <= x <= right, x
b.chat_thinking()
assert b.update(0.04)[0] == "thinking"
b.chat_talking(80)
assert b.update(0.04)[0] == "talking"
for _ in range(200):
    b.update(0.04)
assert b.toggle_forced_sleep() is True
assert b.update(0.04)[0] == "sleeping"
b.toggle_forced_sleep()
print("3. 행동 상태머신 OK, 관측 상태:", sorted(seen))

# 3.5) 방향 유지: 오른쪽으로 걷다 멈춰도 같은 방향을 본다
b.facing_right = True
assert b._flipped("walking") is False  # 걷기 원본은 오른쪽
assert b._flipped("idle") is True  # 대기 원본은 왼쪽 → 반전해서 오른쪽 유지
assert b._flipped("sitting") is False  # 정면 포즈는 반전 없음
b.facing_right = False
assert b._flipped("walking") is True
assert b._flipped("idle") is False
print("3.5 포즈 간 방향 유지 OK")

# 4) 활동성 가중치
b.set_activity(0)
assert b._auto_states[0][1] == 10 and b._auto_states[3][1] == 12.0
b.set_activity(100)
assert b._auto_states[0][1] == 70 and b._auto_states[3][1] == 1.0
b.set_activity(60)
print("4. 활동성 가중치 OK")

# 5) 펫 창: 틱, 조건부 리페인트, 적응형 FPS
from jjanggu.pet_window import ACTIVE_TICK_MS, IDLE_TICK_MS, PetWindow

pet = PetWindow(sprites, b)
pet.show()

repaints = 0
_orig_update = pet.update


def _counting_update(*a):
    global repaints
    repaints += 1
    _orig_update(*a)


pet.update = _counting_update
b.toggle_forced_sleep()
repaints = 0
for _ in range(60):
    time.sleep(0.002)
    pet._tick()
assert repaints <= 1, repaints
assert pet._timer.interval() == IDLE_TICK_MS
b.toggle_forced_sleep()
b._override = None
b._state = "walking"
b._time_left = 999
x0 = pet.x()
for _ in range(60):
    time.sleep(0.005)
    pet._tick()
assert pet._timer.interval() == ACTIVE_TICK_MS
assert pet.x() != x0
pet.update = _orig_update
print("5. 펫 창: 정지 시 리페인트 0~1회 + 저FPS, 걷기 시 이동 + 고FPS OK")

# 5.5) 드래그 낙하: 공중에서 시작하면 중력으로 떨어져 정확히 착지
ground_top = pet._ground_y - pet.height()
pet.move(pet.x(), ground_top - 250)
pet._fall_vy = 0.0
for _ in range(200):
    time.sleep(0.004)
    pet._tick()
    if pet._fall_vy is None:
        break
assert pet._fall_vy is None, "낙하가 끝나지 않음"
assert pet.y() == ground_top, (pet.y(), ground_top)
print("5.5 드래그 낙하 착지 OK")

# 6) Gemini 도구 선언 + 비Windows 가드
from google.genai import types as genai_types

from jjanggu import tools

for fn in tools.ALL_TOOLS:
    decl = genai_types.FunctionDeclaration.from_callable_with_api_option(
        callable=fn, api_option="GEMINI_API"
    )
    assert decl.name == fn.__name__ and decl.description
if sys.platform != "win32":
    assert tools.open_app("메모장") == tools.NOT_WINDOWS_MSG
    assert tools.set_volume(30) == tools.NOT_WINDOWS_MSG
    assert tools.lock_screen() == tools.NOT_WINDOWS_MSG
info = tools.get_system_info()
assert "현재 시각" in info and "CPU" in info
print(f"6. 도구 선언 {len(tools.ALL_TOOLS)}개 + 플랫폼 가드 OK")

# 7) Brain: 키 미설정 응답 + 대화 기록 저장/복원/삭제
from jjanggu.config import Config
from jjanggu.llm import Brain

cfg = Config(path=_tmp / "config.json")
cfg.api_key = ""
brain = Brain(cfg)
assert "API 키" in brain.send("안녕")
brain._history = [("user", "안녕"), ("model", "흥, 왔어?")]
brain._save_history()
brain2 = Brain(cfg)
assert brain2.history == [("user", "안녕"), ("model", "흥, 왔어?")]
brain2.clear_history()
assert brain2.history == []
print("7. Brain 키 가드 + 기록 저장/복원/삭제 OK")

# 8) 채팅창: 토글/말풍선/기록 복원
from jjanggu.chat_window import ChatWindow

brain._save_history()  # (user, model) 2개 저장된 상태
chat = ChatWindow(Brain(cfg))
assert chat._greeted is True  # 기록이 있으면 인사 생략
chat.toggle_near(pet)
assert chat.isVisible()
chat._add_bubble("테스트", "user")
chat.toggle_near(pet)
assert not chat.isVisible()
print("8. 채팅창 토글/기록 복원 OK")

# 9) 말풍선 + 혼잣말
from jjanggu import mutter as mutter_mod
from jjanggu.bubble import SpeechBubble
from jjanggu.mutter import Mutterer

bubble = SpeechBubble()
m = Mutterer(cfg, b, bubble, pet, chat)
# 갓 부팅된 CI 러너는 monotonic이 MUTTER_GAP_S보다 작을 수 있으므로 과거로 밀어둔다
m._last_mutter = time.monotonic() - mutter_mod.MUTTER_GAP_S - 1
mutter_mod.MUTTER_CHANCE = 1.0
m._random_mutter()
assert bubble.isVisible()
bubble.hide()
print("9. 말풍선/혼잣말 OK")

# 10) 자동 실행 가드 + 트레이/설정창/브리지
from jjanggu import autostart
from jjanggu.confirm import ConfirmBridge
from jjanggu.tray import SettingsDialog, create_tray

if sys.platform != "win32":
    assert autostart.supported() is False
    assert autostart.set_enabled(True) is False
SettingsDialog(cfg, brain=brain, on_quit=lambda: None)
create_tray(app, lambda: None, lambda: None, lambda: None, lambda: None)
tools.set_confirmer(ConfirmBridge().confirm)
pet.set_always_on_top(False)
pet.set_always_on_top(True)
print("10. autostart/설정창/트레이/브리지 OK")

print("\n=== 스모크 테스트 전체 통과 ===")
