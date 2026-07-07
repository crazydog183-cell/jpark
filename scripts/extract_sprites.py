"""디자인 시트(assets/design_sheet.png)에서 장꾸의 포즈별 스프라이트를 추출한다.

각 포즈 영역을 크롭한 뒤, 크롭 테두리에서 시작하는 flood-fill로 크림색 배경만
투명 처리한다(개 몸통도 크림 계열이라 전역 색상 키는 쓸 수 없음). 마지막으로
알파 기준으로 트림해서 assets/sprites/<이름>.png 로 저장한다.

개발용 1회성 스크립트: python scripts/extract_sprites.py [--debug]
--debug 를 주면 체커보드 배경의 확인용 시트(scratch 검토용)도 만든다.
"""

import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "assets" / "design_sheet.png"
OUT_DIR = ROOT / "assets" / "sprites"

# 포즈 이름 -> (left, top, right, bottom) 크롭 박스 (시트 원본 좌표)
BOXES = {
    "idle": (748, 88, 948, 328),
    "sitting": (980, 90, 1150, 328),
    "walking": (1188, 100, 1408, 328),
    "thinking": (742, 398, 862, 598),
    "talking": (958, 415, 1092, 598),
    "sleeping": (1195, 390, 1400, 600),
    "surprised": (733, 640, 932, 838),
    "happy": (1000, 645, 1240, 838),
}

TOLERANCE = 34  # 배경으로 판정할 채널별 색 거리 (더 크면 밝은 얼굴 털이 침식됨)
SHADOW = (231, 215, 194)  # 포즈 밑 바닥 그림자 색 (시트에서 샘플링)
SHADOW_TOL = 25


def flood_remove_background(img: Image.Image, tol: int = TOLERANCE) -> Image.Image:
    """테두리에서 연결된 배경색 픽셀만 투명 처리한다."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    # 네 모서리 색의 평균을 배경 기준색으로 사용
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))

    # 그림자 판정은 크롭 하단 대역에서만 허용 — 개 몸통의 크림색 털과
    # 그림자 색이 겹쳐서 전역 적용하면 얼굴/몸이 침식된다.
    shadow_zone_y = int(h * 0.85)

    def is_bg(p, y):
        if all(abs(p[i] - bg[i]) <= tol for i in range(3)):
            return True
        return y >= shadow_zone_y and all(
            abs(p[i] - SHADOW[i]) <= SHADOW_TOL for i in range(3)
        )

    seen = bytearray(w * h)
    queue = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg(px[x, y], y):
                queue.append((x, y))
                seen[y * w + x] = 1
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(px[x, y], y) and not seen[y * w + x]:
                queue.append((x, y))
                seen[y * w + x] = 1

    while queue:
        x, y = queue.popleft()
        px[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                if is_bg(px[nx, ny], ny):
                    seen[ny * w + nx] = 1
                    queue.append((nx, ny))
    return img


def trim(img: Image.Image, margin: int = 2) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l = max(0, l - margin)
    t = max(0, t - margin)
    r = min(img.width, r + margin)
    b = min(img.height, b + margin)
    return img.crop((l, t, r, b))


def checkerboard(size, cell=12):
    board = Image.new("RGBA", size, (200, 200, 200, 255))
    d = ImageDraw.Draw(board)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                d.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(240, 240, 240, 255))
    return board


def main():
    debug = "--debug" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SHEET).convert("RGBA")

    results = {}
    for name, box in BOXES.items():
        sprite = trim(flood_remove_background(sheet.crop(box)))
        sprite.save(OUT_DIR / f"{name}.png")
        results[name] = sprite
        print(f"{name}: {sprite.size}")

    if debug:
        pad = 10
        cell_w = max(s.width for s in results.values()) + pad * 2
        cell_h = max(s.height for s in results.values()) + pad * 2 + 18
        cols = 4
        rows = (len(results) + cols - 1) // cols
        board = checkerboard((cell_w * cols, cell_h * rows))
        d = ImageDraw.Draw(board)
        for i, (name, s) in enumerate(results.items()):
            cx, cy = (i % cols) * cell_w, (i // cols) * cell_h
            board.paste(s, (cx + (cell_w - s.width) // 2, cy + pad), s)
            d.text((cx + 6, cy + cell_h - 16), name, fill=(30, 30, 30, 255))
        debug_path = OUT_DIR / "_debug_sheet.png"
        board.save(debug_path)
        print(f"debug sheet: {debug_path}")


if __name__ == "__main__":
    main()
