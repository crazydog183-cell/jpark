"""장꾸가 쓸 수 있는 '제한적인 컴퓨터 제어' 도구 모음.

화이트리스트 기반으로만 동작하며 임의 셸 명령은 절대 실행하지 않는다.
각 함수는 google-genai SDK의 automatic function calling에 직접 전달되므로
타입 힌트와 docstring이 곧 모델에게 보이는 도구 명세다.
반환값은 모델이 읽고 사용자에게 전달할 결과 문자열이다.

화면 잠금/절전처럼 되돌리기 어려운 동작은 실행 전 확인 다이얼로그를 띄운다
(set_confirmer 로 주입, 워커 스레드에서 안전하게 호출됨).
"""

import ctypes
import datetime
import os
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Callable

IS_WINDOWS = sys.platform == "win32"
NOT_WINDOWS_MSG = "이 기능은 Windows에서만 쓸 수 있어."

_confirmer: Callable[[str], bool] | None = None


def set_confirmer(fn: Callable[[str], bool]) -> None:
    global _confirmer
    _confirmer = fn


def _confirm(message: str) -> bool:
    if _confirmer is None:
        return False
    return _confirmer(message)


# ── 앱/웹 열기 ──────────────────────────────────────────────────
_APP_WHITELIST = {
    "메모장": "notepad",
    "notepad": "notepad",
    "계산기": "calc",
    "calculator": "calc",
    "calc": "calc",
    "그림판": "mspaint",
    "paint": "mspaint",
    "탐색기": "explorer",
    "파일 탐색기": "explorer",
    "explorer": "explorer",
    "제어판": "control",
    "설정": "ms-settings:",
    "작업 관리자": "taskmgr",
}


def open_app(app_name: str) -> str:
    """허용된 Windows 기본 앱을 실행한다.

    Args:
        app_name: 실행할 앱 이름. 가능한 값: 메모장, 계산기, 그림판, 탐색기,
            제어판, 설정, 작업 관리자
    """
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    exe = _APP_WHITELIST.get(app_name.strip().lower()) or _APP_WHITELIST.get(
        app_name.strip()
    )
    if not exe:
        allowed = ", ".join(sorted({v for v in _APP_WHITELIST if not v.isascii()}))
        return f"'{app_name}'은(는) 허용 목록에 없어. 가능한 앱: {allowed}"
    try:
        if exe.endswith(":"):
            os.startfile(exe)  # ms-settings: 같은 URI
        else:
            subprocess.Popen([exe])
        return f"{app_name} 실행 완료"
    except OSError as e:
        return f"실행 실패: {e}"


def open_url(url: str) -> str:
    """기본 브라우저로 웹사이트를 연다.

    Args:
        url: 열 주소 (http:// 또는 https:// 로 시작해야 함)
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"{url} 열었음"


def web_search(query: str) -> str:
    """기본 브라우저에서 구글 웹 검색을 연다.

    Args:
        query: 검색어
    """
    webbrowser.open(
        "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    )
    return f"'{query}' 검색 결과를 브라우저로 열었음"


# ── 볼륨/미디어 ─────────────────────────────────────────────────
def _volume_interface():
    import comtypes
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    # LLM 도구는 워커 스레드에서 실행되므로 COM을 스레드별로 초기화해야 한다
    try:
        comtypes.CoInitialize()
    except OSError:
        pass  # 이미 초기화된 스레드
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)


def set_volume(level: int) -> str:
    """시스템 볼륨을 설정한다.

    Args:
        level: 볼륨 크기 (0~100)
    """
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    level = max(0, min(100, level))
    try:
        vol = _volume_interface()
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        if level > 0:
            vol.SetMute(0, None)
        return f"볼륨을 {level}%로 맞췄음"
    except Exception as e:  # pycaw/COM 오류는 종류가 다양함
        return f"볼륨 조절 실패: {e}"


def toggle_mute() -> str:
    """시스템 음소거를 켜거나 끈다."""
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    try:
        vol = _volume_interface()
        muted = not bool(vol.GetMute())
        vol.SetMute(1 if muted else 0, None)
        return "음소거 켰음" if muted else "음소거 껐음"
    except Exception as e:
        return f"음소거 전환 실패: {e}"


_MEDIA_KEYS = {"play_pause": 0xB3, "next": 0xB0, "prev": 0xB1, "stop": 0xB2}


def media_control(action: str) -> str:
    """음악/동영상 재생을 제어한다 (미디어 키 입력).

    Args:
        action: play_pause(재생/일시정지), next(다음 곡), prev(이전 곡), stop(정지) 중 하나
    """
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    vk = _MEDIA_KEYS.get(action)
    if vk is None:
        return f"'{action}'은 모르는 동작이야. 가능: {', '.join(_MEDIA_KEYS)}"
    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    return f"미디어 키({action}) 눌렀음"


# ── 시스템 정보/스크린샷 ────────────────────────────────────────
def get_system_info() -> str:
    """현재 시각, 배터리, CPU/메모리 사용량을 알려준다."""
    import psutil

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
    lines = [f"현재 시각: {now}"]
    battery = psutil.sensors_battery()
    if battery:
        plug = "충전 중" if battery.power_plugged else "배터리 사용 중"
        lines.append(f"배터리: {battery.percent:.0f}% ({plug})")
    lines.append(f"CPU 사용량: {psutil.cpu_percent(interval=0.3):.0f}%")
    mem = psutil.virtual_memory()
    lines.append(
        f"메모리: {mem.percent:.0f}% 사용 중"
        f" ({mem.used / 2**30:.1f}GB / {mem.total / 2**30:.1f}GB)"
    )
    return "\n".join(lines)


def take_screenshot() -> str:
    """전체 화면을 캡처해서 사진 폴더에 저장한다."""
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    from PIL import ImageGrab

    pictures = Path.home() / "Pictures"
    pictures.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = pictures / f"jjanggu_screenshot_{stamp}.png"
    ImageGrab.grab(all_screens=True).save(path)
    return f"스크린샷 저장 완료: {path}"


# ── 창 관리/절전 ────────────────────────────────────────────────
def minimize_all_windows() -> str:
    """열려 있는 모든 창을 최소화해서 바탕화면을 보여준다."""
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    MIN_ALL = 419
    WM_COMMAND = 0x0111
    tray = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
    if not tray:
        return "작업표시줄 창을 찾지 못했어."
    ctypes.windll.user32.SendMessageW(tray, WM_COMMAND, MIN_ALL, 0)
    return "모든 창 최소화 완료"


def lock_screen() -> str:
    """화면을 잠근다. 실행 전 사용자에게 확인을 받는다."""
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    if not _confirm("장꾸가 화면을 잠그려고 해요. 잠글까요?"):
        return "주인이 취소했어. 화면 안 잠갔음."
    ctypes.windll.user32.LockWorkStation()
    return "화면 잠금 완료"


def sleep_pc() -> str:
    """컴퓨터를 절전 모드로 전환한다. 실행 전 사용자에게 확인을 받는다."""
    if not IS_WINDOWS:
        return NOT_WINDOWS_MSG
    if not _confirm("장꾸가 컴퓨터를 절전 모드로 바꾸려고 해요. 진행할까요?"):
        return "주인이 취소했어. 절전 안 했음."
    ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
    return "절전 모드 전환"


ALL_TOOLS = [
    open_app,
    open_url,
    web_search,
    set_volume,
    toggle_mute,
    media_control,
    get_system_info,
    take_screenshot,
    minimize_all_windows,
    lock_screen,
    sleep_pc,
]
