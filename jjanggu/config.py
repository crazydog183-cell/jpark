"""설정 로드/저장. Windows에서는 %APPDATA%/Jjanggu/config.json 에 저장한다."""

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

DEFAULT_MODEL = "gemini-3.5-flash"


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home()))
        return Path(base) / "Jjanggu"
    return Path.home() / ".config" / "jjanggu"


@dataclass
class Config:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    pet_size: int = 96  # 펫(대기 포즈) 화면 높이 px
    walk_speed: float = 55.0  # px/초
    activity: int = 60  # 활동성 0(게으름)~100(활발) — 걷기/잠자기 비율
    always_on_top: bool = True  # 펫 창 항상 맨 위

    # ── 확장 기능 토글 (기본값 전부 ON, 설정창 '확장 기능' 탭) ──
    mutter_enabled: bool = True  # 혼잣말 말풍선
    battery_alert: bool = True  # 배터리 부족 경고
    time_greeting: bool = True  # 점심/퇴근/심야 시간대 인사
    remember_chat: bool = True  # 대화 기억 (끄면 세션 내에서만 유지)
    time_awareness: bool = True  # 시간 감각 페르소나 ([시간 정보] 주입)
    screen_analysis: bool = True  # 화면 비전 분석 도구
    reply_bubble: bool = True  # 채팅창 닫힘 시 답변을 말풍선으로
    fall_animation: bool = True  # 드래그 후 중력 낙하 애니메이션
    keep_facing: bool = True  # 포즈가 바뀌어도 진행 방향 유지

    path: Path = field(default=None, repr=False, compare=False)

    @classmethod
    def load(cls) -> "Config":
        path = config_dir() / "config.json"
        cfg = cls(path=path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for f in fields(cls):
                    if f.name != "path" and f.name in data:
                        setattr(cfg, f.name, data[f.name])
            except (json.JSONDecodeError, OSError):
                pass  # 손상된 설정은 기본값으로 시작
        # 환경변수 키가 있으면 우선 사용
        env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if env_key and not cfg.api_key:
            cfg.api_key = env_key
        return cfg

    def save(self) -> None:
        data = asdict(self)
        data.pop("path", None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
