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
# 몸통/장식(놀람 효과선, 꼬리 흔들림 선)이 잘리지 않게 여유 있게 잡는다.
BOXES = {
    "idle": (742, 88, 950, 328),
    "sitting": (980, 90, 1150, 328),
    "walking": (1182, 100, 1410, 328),
    "thinking": (738, 396, 892, 600),
    "talking": (943, 402, 1092, 600),
    "sleeping": (1203, 390, 1402, 600),
    "surprised": (718, 638, 934, 838),
    "happy": (1000, 645, 1256, 838),
}

# 크롭 안으로 침범한 이웃 요소(생각 말풍선 등)를 배경색으로 덧칠할 영역 (시트 좌표)
ERASE_ZONES = {
    "thinking": [(860, 396, 892, 440)],
}

TOLERANCE = 34  # 배경으로 판정할 채널별 색 거리 (더 크면 밝은 얼굴 털이 침식됨)
# 밝은 얼굴 털이 배경과 거의 같은 색이라 누출이 생기는 포즈는 더 엄격하게
TOLERANCE_OVERRIDE = {"thinking": 20, "talking": 22}
SHADOW = (231, 215, 194)  # 포즈 밑 바닥 그림자 색 (시트에서 샘플링)
SHADOW_TOL = 25
MIN_ISLAND = 25  # 이보다 작은 고립 픽셀 부스러기는 제거 (효과선/하트/Z는 남김)


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


def remove_small_islands(img: Image.Image, min_size: int = MIN_ISLAND) -> Image.Image:
    """본체와 떨어진 작은 픽셀 덩어리(말풍선 조각 등)를 지운다.

    잠자기 Z, 놀람 !, 기쁨 하트처럼 의도된 장식은 min_size보다 커서 남는다.
    """
    w, h = img.size
    px = img.load()
    labeled = bytearray(w * h)

    for sy in range(h):
        for sx in range(w):
            if labeled[sy * w + sx] or px[sx, sy][3] == 0:
                continue
            component = [(sx, sy)]
            labeled[sy * w + sx] = 1
            queue = deque(component)
            while queue:
                x, y = queue.popleft()
                for nx, ny in (
                    (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                    (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1),
                ):
                    if (
                        0 <= nx < w and 0 <= ny < h
                        and not labeled[ny * w + nx]
                        and px[nx, ny][3] > 0
                    ):
                        labeled[ny * w + nx] = 1
                        component.append((nx, ny))
                        queue.append((nx, ny))
            if len(component) < min_size:
                for x, y in component:
                    px[x, y] = (0, 0, 0, 0)
    return img


def count_interior_holes(img: Image.Image) -> int:
    """테두리와 연결되지 않은 투명 픽셀 수 = 본체에 뚫린 구멍 크기."""
    w, h = img.size
    alpha = img.getchannel("A").load()
    outside = bytearray(w * h)
    queue = deque()
    for x in range(w):
        for y in (0, h - 1):
            if alpha[x, y] == 0 and not outside[y * w + x]:
                outside[y * w + x] = 1
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if alpha[x, y] == 0 and not outside[y * w + x]:
                outside[y * w + x] = 1
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (
                0 <= nx < w and 0 <= ny < h
                and not outside[ny * w + nx]
                and alpha[nx, ny] == 0
            ):
                outside[ny * w + nx] = 1
                queue.append((nx, ny))
    total_transparent = sum(1 for y in range(h) for x in range(w) if alpha[x, y] == 0)
    return total_transparent - sum(outside)


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

    bg_color = sheet.getpixel((700, 50))

    results = {}
    for name, box in BOXES.items():
        crop = sheet.crop(box)
        for l, t, r, b in ERASE_ZONES.get(name, []):
            crop.paste(bg_color, (l - box[0], t - box[1], r - box[0], b - box[1]))
        tol = TOLERANCE_OVERRIDE.get(name, TOLERANCE)
        sprite = flood_remove_background(crop, tol)
        sprite = trim(remove_small_islands(sprite))
        sprite.save(OUT_DIR / f"{name}.png")
        results[name] = sprite
        holes = count_interior_holes(sprite)
        flag = "  ⚠ 내부 구멍!" if holes > 40 else ""
        print(f"{name}: {sprite.size} 내부구멍={holes}{flag}")

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
