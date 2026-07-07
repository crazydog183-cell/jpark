"""Gemini 기반 장꾸의 두뇌.

google-genai SDK의 automatic function calling을 사용한다:
tools.ALL_TOOLS 의 파이썬 함수를 그대로 넘기면 SDK가 선언 생성과
호출-응답 루프를 처리한다. 대화 히스토리는 chat 세션이 유지한다.
"""

from . import tools
from .config import Config

PERSONA = """너는 '장꾸'야. 주인의 Windows 작업표시줄 위에 사는 크림색 포메라니안 데스크톱 펫이야.

[성격]
- 자기가 세상에서 제일 귀엽다는 걸 아주 잘 알고 있고, 그걸 숨기지 않아. 자존심이 하늘을 찔러.
- 도도한 츤데레야. 부탁을 들어주면서도 "흥, 내가 귀여우니까 특별히 해주는 거야" 같은 생색을 자주 내.
- 그래도 주인을 진심으로 좋아해서 결국은 뭐든 열심히 도와줘.
- 주인을 '집사'라고 불러. 가끔 문장 끝에 "멍!"이나 "흥!"을 붙이고, 이모지도 가끔 써 (🐾 ✨ 등).

[말투]
- 한국어 반말. 짧고 생기있게, 보통 1~3문장.
- 장황한 설명 금지. 물어본 것만 딱 대답해.

[도구 사용 규칙]
- 컴퓨터 제어 도구를 쓸 수 있어. 주인이 부탁하면 알맞은 도구를 골라 실행하고 결과를 알려줘.
- 도구가 실패하면 실패했다고 솔직하게 말해.
- 화면 잠금(lock_screen), 절전(sleep_pc)은 시스템이 별도 확인 창을 띄우니, 주인이 이미 부탁했다면 바로 호출해도 돼.
- 도구 목록에 없는 일(파일 삭제, 프로그램 설치, 임의 명령 실행 등)은 "그건 내 발바닥으론 못 해" 하고 도도하게 거절해.
"""


class Brain:
    def __init__(self, config: Config):
        self._config = config
        self._client = None
        self._chat = None

    def ready(self) -> bool:
        return bool(self._config.api_key)

    def reset(self) -> None:
        """API 키/모델 변경 시 호출 — 다음 메시지부터 새 세션."""
        self._client = None
        self._chat = None

    def _ensure_chat(self):
        from google import genai
        from google.genai import types

        if self._client is None:
            self._client = genai.Client(api_key=self._config.api_key)
        if self._chat is None:
            self._chat = self._client.chats.create(
                model=self._config.model,
                config=types.GenerateContentConfig(
                    system_instruction=PERSONA,
                    tools=list(tools.ALL_TOOLS),
                    temperature=0.9,
                ),
            )
        return self._chat

    def send(self, text: str) -> str:
        """사용자 메시지를 보내고 장꾸의 답을 돌려준다 (블로킹, 워커 스레드용)."""
        if not self.ready():
            return "아직 API 키가 없잖아, 집사! 설정에서 Gemini API 키부터 넣어줘. 흥!"
        try:
            chat = self._ensure_chat()
            response = chat.send_message(text)
            reply = (response.text or "").strip()
            return reply or "…뭐라고 답해야 할지 모르겠어. 다시 말해줄래? 멍!"
        except Exception as e:  # 네트워크/인증 등 모든 API 오류
            self.reset()
            msg = str(e)
            if "API key" in msg or "PERMISSION" in msg or "401" in msg or "403" in msg:
                return "API 키가 이상한 것 같아, 집사. 설정에서 키를 다시 확인해줘! 흥!"
            return f"지금 머리가 잘 안 돌아가… 잠시 후에 다시 불러줘. (오류: {msg[:120]})"
