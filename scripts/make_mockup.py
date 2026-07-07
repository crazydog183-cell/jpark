"""README용 목업 스크린샷 생성 (개발용, Linux offscreen에서도 동작).

실제 ChatWindow 위젯을 offscreen으로 렌더링해 캡처하고, Pillow로
Windows 11 풍 바탕화면/작업표시줄을 그려 그 위에 장꾸와 채팅창을
합성한다. 결과: docs/screenshot_mockup.png

실행: python scripts/make_mockup.py
"""

import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QBuffer
from PySide6.QtWidgets import QApplication

from jjanggu.chat_window import ChatWindow
from jjanggu.config import Config
from jjanggu.llm import Brain

OUT = ROOT / "docs" / "screenshot_mockup.png"

SCENE_W, SCENE_H = 1440, 810
TASKBAR_H = 52

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

CONVERSATION = [
    ("pet", "왔어, 집사? 🐾 나 장꾸야. 세상에서 제일 귀여운 포메라니안이지. 뭐 도와줄까? 흥, 특별히 들어주는 거야."),
    ("user", "볼륨 30으로 줄여줘"),
    ("pet", "볼륨 30%로 맞췄어! 흥, 내가 귀여우니까 특별히 해주는 거야. 멍! 🐾"),
    ("user", "역시 넌 천재야"),
    ("pet", "당연하지. 세상에서 제일 귀엽고 똑똑한 포메라니안이 바로 나라구. ✨"),
]


def grab_chat_window() -> Image.Image:
    """가짜 대화가 채워진 ChatWindow를 실제로 렌더링해 캡처한다."""
    app = QApplication.instance() or QApplication([])
    chat = ChatWindow(Brain(Config(path=None)))
    for who, text in CONVERSATION:
        chat._add_bubble(text, who)
    chat.show()
    app.processEvents()
    chat._scroll_to_bottom()
    app.processEvents()

    pixmap = chat.grab()
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.ReadWrite)
    pixmap.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA")


def ImageChops_add(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.add(a, b)


def draw_taskbar(scene: Image.Image) -> None:
    """Windows 11 풍 작업표시줄(중앙 아이콘 + 우측 트레이/시계)."""
    d = ImageDraw.Draw(scene)
    top = SCENE_H - TASKBAR_H
    d.rectangle((0, top, SCENE_W, SCENE_H), fill=(243, 244, 248))
    d.line((0, top, SCENE_W, top), fill=(215, 218, 226), width=1)

    icon_size = 26
    cy = top + TASKBAR_H // 2
    icons_cx = SCENE_W // 2 - 90

    # 시작 버튼 (파란 4분할 창)
    x0, y0 = icons_cx - icon_size // 2, cy - icon_size // 2
    g = 3
    half = (icon_size - g) // 2
    for dx, dy in ((0, 0), (half + g, 0), (0, half + g), (half + g, half + g)):
        d.rounded_rectangle(
            (x0 + dx, y0 + dy, x0 + dx + half, y0 + dy + half),
            radius=3,
            fill=(0, 120, 212),
        )

    # 앱 아이콘 자리 (검색/탐색기/브라우저 흉내)
    palette = [(90, 95, 105), (255, 200, 60), (60, 150, 240), (35, 170, 110)]
    for i, color in enumerate(palette):
        cx = icons_cx + 52 * (i + 1)
        if i == 0:  # 검색: 원 + 손잡이
            r = 9
            d.ellipse((cx - r, cy - r - 2, cx + r, cy + r - 2), outline=color, width=3)
            d.line((cx + 6, cy + 5, cx + 12, cy + 11), fill=color, width=3)
        else:
            d.rounded_rectangle(
                (cx - 13, cy - 13, cx + 13, cy + 13), radius=6, fill=color
            )

    # 우측 트레이: ^ · 와이파이 · 스피커 · 시계
    font_s = ImageFont.truetype(FONT_PATH, 13)
    font_tray = ImageFont.truetype(FONT_PATH, 15)
    tray_x = SCENE_W - 170
    d.text((tray_x, cy - 9), "^", font=font_tray, fill=(70, 72, 80))
    # 와이파이 부채꼴 3개
    wx = tray_x + 30
    for i, r in enumerate((12, 8, 4)):
        d.arc((wx - r, cy - 3 - r, wx + r, cy - 3 + r), 225, 315, fill=(70, 72, 80), width=2)
    d.ellipse((wx - 1, cy - 5, wx + 2, cy - 2), fill=(70, 72, 80))
    # 스피커
    sx = wx + 28
    d.polygon(
        [(sx - 8, cy - 4), (sx - 3, cy - 4), (sx + 3, cy - 10), (sx + 3, cy + 4), (sx - 3, cy - 2 + 4), (sx - 8, cy + 2)],
        fill=(70, 72, 80),
    )
    d.arc((sx + 3, cy - 8, sx + 13, cy + 2), -60, 60, fill=(70, 72, 80), width=2)
    # 시계 (두 줄)
    d.text((SCENE_W - 78, top + 9), "오후 3:24", font=font_s, fill=(50, 52, 60))
    d.text((SCENE_W - 88, top + 27), "2026-07-07", font=font_s, fill=(50, 52, 60))


def paste_with_shadow(scene: Image.Image, img: Image.Image, pos: tuple[int, int]) -> None:
    shadow = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    mask = img.getchannel("A").point(lambda a: min(a, 110))
    black = Image.new("RGBA", img.size, (10, 15, 30, 255))
    shadow.paste(black, (pos[0] + 5, pos[1] + 7), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    scene.alpha_composite(shadow)
    scene.alpha_composite(img, pos)


def main() -> None:
    chat_img = grab_chat_window()

    scene = ImageChops_add(
        make_wallpaper_base(), make_wallpaper_glow()
    ).convert("RGBA")
    draw_taskbar(scene)

    # 장꾸: 걷기 포즈, 작업표시줄 위
    pet = Image.open(ROOT / "assets" / "sprites" / "walking.png").convert("RGBA")
    pet = pet.resize((round(pet.width * 96 / pet.height), 96), Image.LANCZOS)
    pet_x = int(SCENE_W * 0.66)
    # 스프라이트 하단 투명 여백만큼 살짝 내려서 발이 작업표시줄에 닿게
    pet_y = SCENE_H - TASKBAR_H - pet.height + 6
    paste_with_shadow(scene, pet, (pet_x, pet_y))

    # 채팅창: 펫 위쪽
    chat_x = min(pet_x + pet.width // 2 - chat_img.width // 2, SCENE_W - chat_img.width - 24)
    chat_y = pet_y - chat_img.height - 14
    paste_with_shadow(scene, chat_img, (chat_x, chat_y))

    OUT.parent.mkdir(exist_ok=True)
    scene.convert("RGB").save(OUT)
    print("saved:", OUT)


def make_wallpaper_base() -> Image.Image:
    img = Image.new("RGB", (SCENE_W, SCENE_H))
    top, bottom = (26, 60, 120), (108, 160, 220)
    for y in range(SCENE_H):
        t = y / SCENE_H
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        img.paste(color, (0, y, SCENE_W, y + 1))
    return img


def make_wallpaper_glow() -> Image.Image:
    glow = Image.new("RGB", (SCENE_W, SCENE_H), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((SCENE_W * 0.5, SCENE_H * 0.05, SCENE_W * 1.15, SCENE_H * 0.75), fill=(45, 60, 80))
    d.ellipse((-SCENE_W * 0.2, SCENE_H * 0.4, SCENE_W * 0.35, SCENE_H * 1.1), fill=(30, 45, 60))
    return glow.filter(ImageFilter.GaussianBlur(90))


if __name__ == "__main__":
    main()
