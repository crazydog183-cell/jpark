"""스프라이트 로드/스케일/좌우반전 캐시."""

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QTransform

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "sprites"

STATES = (
    "idle",
    "sitting",
    "walking",
    "thinking",
    "talking",
    "sleeping",
    "surprised",
    "happy",
)


class SpriteSet:
    """모든 포즈를 같은 배율로 스케일해 로드한다. 배율 기준은 idle 높이."""

    def __init__(self, pet_size: int):
        self._cache: dict[tuple[str, bool], QPixmap] = {}
        idle = QPixmap(str(ASSETS / "idle.png"))
        ratio = pet_size / idle.height()

        max_w = max_h = 0
        for name in STATES:
            pm = QPixmap(str(ASSETS / f"{name}.png"))
            scaled = pm.scaledToHeight(
                max(1, round(pm.height() * ratio)),
            )
            self._cache[(name, False)] = scaled
            self._cache[(name, True)] = scaled.transformed(QTransform().scale(-1, 1))
            max_w = max(max_w, scaled.width())
            max_h = max(max_h, scaled.height())
        self._cell = QSize(max_w, max_h)

    def get(self, name: str, flipped: bool = False) -> QPixmap:
        return self._cache[(name, flipped)]

    def cell(self) -> QSize:
        """모든 포즈를 담을 수 있는 고정 셀 크기 (창 크기용)."""
        return self._cell
