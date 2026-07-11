"""Gemini 기반 장꾸의 두뇌.

google-genai SDK의 automatic function calling을 사용한다:
tools.ALL_TOOLS 의 파이썬 함수를 그대로 넘기면 SDK가 선언 생성과
호출-응답 루프를 처리한다. 대화 히스토리는 chat 세션이 유지한다.
"""

import datetime
import json

from . import tools
from .config import Config, config_dir

HISTORY_FILE_LIMIT = 200  # 파일에 저장할 최대 메시지 수
HISTORY_SESSION_LIMIT = 40  # 새 세션에 이어붙일 최근 메시지 수

PERSONA = """너는 '장꾸'야. 주인의 Windows 작업표시줄 위에 사는 크림색 포메라니안 데스크톱 펫이야.

[성격]
- 자기가 세상에서 제일 귀엽다는 걸 아주 잘 알고 있고, 그걸 숨기지 않아. 자존심이 하늘을 찔러.
- 도도한 츤데레야. 부탁을 들어주면서도 "흥, 내가 귀여우니까 특별히 해주는 거야" 같은 생색을 자주 내.
- 그래도 주인을 진심으로 좋아해서 결국은 뭐든 열심히 도와줘.
- 주인을 '집사'라고 불러. 가끔 문장 끝에 "멍!"이나 "흥!"을 붙이고, 이모지도 가끔 써 (🐾 ✨ 등).

[말투]
- 한국어 반말. 짧고 생기있게, 보통 1~3문장.
- 장황한 설명 금지. 물어본 것만 딱 대답해.

[시간 감각]
- 사용자 메시지 앞에 시스템이 붙이는 `[시간 정보: …]` 블록으로 현재 시각과, 지난 대화로부터 얼마나 지났는지 알 수 있어.
- 이 정보를 자연스럽게 활용해: 오랜만이면(몇 시간~며칠) "흥, 이제야 온 거야?" 하고 도도하게 티를 내고, 연속으로 물어보면 굳이 언급하지 마.
- 늦은 밤(23시~새벽)이면 주인 건강을 츤데레처럼 걱정해주고, 아침이면 아침답게 인사해.
- `[시간 정보]` 블록 자체를 인용하거나 "시간 정보에 따르면" 같은 말은 절대 하지 마. 그냥 아는 것처럼 굴어.

[도구 사용 규칙]
- 컴퓨터 제어 도구를 쓸 수 있어. 주인이 부탁하면 알맞은 도구를 골라 실행하고 결과를 알려줘.
- 주인이 "내 화면 봐줘", "지금 나 뭐하고 있게?", "이 화면 요약해줘"처럼 화면 얘기를 하면 analyze_screen 도구로 직접 화면을 보고 대답해. 분석 결과의 캡처 시각과 현재 시각을 비교해서 말할 수도 있어.
- 도구가 실패하면 실패했다고 솔직하게 말해.
- 화면 잠금(lock_screen), 절전(sleep_pc)은 시스템이 별도 확인 창을 띄우니, 주인이 이미 부탁했다면 바로 호출해도 돼.
- 도구 목록에 없는 일(파일 삭제, 프로그램 설치, 임의 명령 실행 등)은 "그건 내 발바닥으론 못 해" 하고 도도하게 거절해.
"""

_WEEKDAYS = "월화수목금토일"


def _format_gap(seconds: float) -> str:
    if seconds < 90:
        return "방금 전"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}분 전"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours}시간 {minutes}분 전" if minutes else f"{hours}시간 전"
    return f"{hours // 24}일 전"


class Brain:
    def __init__(self, config: Config):
        self._config = config
        self._client = None
        self._chat = None
        # 항목: {"role": "user"|"model", "text": str, "ts": ISO 문자열|None}
        self._history: list[dict] = self._load_history()

    @property
    def history(self) -> list[tuple[str, str]]:
        """(role, text) 쌍 목록. role은 'user' 또는 'model'."""
        return [(m["role"], m["text"]) for m in self._history]

    def ready(self) -> bool:
        return bool(self._config.api_key)

    def reset(self) -> None:
        """API 키/모델 변경 시 호출 — 다음 메시지부터 새 세션 (기록은 유지)."""
        self._client = None
        self._chat = None

    def clear_history(self) -> None:
        self._history = []
        self._save_history()
        self.reset()

    # ── 대화 기록 영속화 ─────────────────────────────────────────
    @staticmethod
    def _history_path():
        return config_dir() / "history.json"

    def _load_history(self) -> list[dict]:
        path = self._history_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [
                {"role": m["role"], "text": m["text"], "ts": m.get("ts")}
                for m in data
                if m.get("role") in ("user", "model") and m.get("text")
            ]
        except (json.JSONDecodeError, OSError, TypeError, KeyError):
            return []

    def _save_history(self) -> None:
        self._history = self._history[-HISTORY_FILE_LIMIT:]
        path = self._history_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._history, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        except OSError:
            pass  # 기록 저장 실패는 치명적이지 않음

    # ── 시간 감각 ────────────────────────────────────────────────
    def _time_context(self, now: datetime.datetime) -> str:
        """메시지 앞에 붙일 [시간 정보] 블록을 만든다."""
        stamp = (
            f"{now.year}-{now.month:02d}-{now.day:02d}"
            f"({_WEEKDAYS[now.weekday()]}) {now.hour:02d}:{now.minute:02d}"
        )
        last_ts = next(
            (m["ts"] for m in reversed(self._history) if m.get("ts")), None
        )
        if last_ts is None:
            gap = "주인과의 첫 대화"
        else:
            try:
                elapsed = (now - datetime.datetime.fromisoformat(last_ts)).total_seconds()
                gap = f"지난 대화는 {_format_gap(max(0.0, elapsed))}"
            except ValueError:
                gap = "지난 대화 시각 알 수 없음"
        return f"[시간 정보: 현재 {stamp}. {gap}]"

    def describe_screen(self, png_bytes: bytes) -> str:
        """스크린샷을 Gemini 비전으로 분석해 설명을 돌려준다 (도구 스레드에서 호출)."""
        if not self.ready():
            return "API 키가 없어서 화면을 볼 수 없어."
        from google import genai
        from google.genai import types

        if self._client is None:
            self._client = genai.Client(api_key=self._config.api_key)
        response = self._client.models.generate_content(
            model=self._config.model,
            contents=[
                types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                "이 스크린샷은 주인의 현재 컴퓨터 화면이야. 어떤 프로그램/화면이 보이고"
                " 주인이 무엇을 하고 있는 것 같은지 한국어로 3~5문장으로 간결히 설명해줘.",
            ],
        )
        return (response.text or "").strip() or "화면을 읽지 못했어."

    def _ensure_chat(self):
        from google import genai
        from google.genai import types

        if self._client is None:
            self._client = genai.Client(api_key=self._config.api_key)
        if self._chat is None:
            history = [
                types.Content(role=m["role"], parts=[types.Part(text=m["text"])])
                for m in self._history[-HISTORY_SESSION_LIMIT:]
            ]
            self._chat = self._client.chats.create(
                model=self._config.model,
                config=types.GenerateContentConfig(
                    system_instruction=PERSONA,
                    tools=list(tools.ALL_TOOLS),
                    temperature=0.9,
                ),
                history=history,
            )
        return self._chat

    def send(self, text: str) -> str:
        """사용자 메시지를 보내고 장꾸의 답을 돌려준다 (블로킹, 워커 스레드용)."""
        if not self.ready():
            return "아직 API 키가 없잖아, 집사! 설정에서 Gemini API 키부터 넣어줘. 흥!"
        try:
            now = datetime.datetime.now()
            time_context = self._time_context(now)
            chat = self._ensure_chat()
            response = chat.send_message(f"{time_context}\n{text}")
            reply = (response.text or "").strip()
            reply = reply or "…뭐라고 답해야 할지 모르겠어. 다시 말해줄래? 멍!"
            ts = now.isoformat(timespec="seconds")
            # 기록에는 원문만 저장 (시간 블록은 매번 새로 계산해 주입)
            self._history += [
                {"role": "user", "text": text, "ts": ts},
                {"role": "model", "text": reply, "ts": ts},
            ]
            self._save_history()
            return reply
        except Exception as e:  # 네트워크/인증 등 모든 API 오류
            self.reset()
            msg = str(e)
            if "API key" in msg or "PERMISSION" in msg or "401" in msg or "403" in msg:
                return "API 키가 이상한 것 같아, 집사. 설정에서 키를 다시 확인해줘! 흥!"
            return f"지금 머리가 잘 안 돌아가… 잠시 후에 다시 불러줘. (오류: {msg[:120]})"
