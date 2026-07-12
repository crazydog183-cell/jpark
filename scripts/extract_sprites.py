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


POCKET_GROW_TOL = 60  # 포켓 후보 영역 확장 톨러런스
POCKET_MAX_SIZE = 1200  # 이보다 크면 몸통 밝은 털로 간주하고 보존
POCKET_DARK_RATIO = 0.6  # 경계의 어두운 픽셀 비율이 이 이상이어야 포켓
POCKET_DARK_DIFF = 100  # '어두운 외곽선' 판정 색 차


def remove_enclosed_background(img: Image.Image, bg: tuple) -> Image.Image:
    """외곽선에 완전히 둘러싸여 테두리 flood-fill이 못 닿은 배경 포켓 제거.

    (예: 걷기 포즈 다리 사이 틈) 색만으로는 개의 밝은 가슴/얼굴 털과 구분이
    안 되므로 기하학적으로 분류한다: 배경색과 거의 같은(≤8) 시드에서 영역을
    키웠을 때 '작고, 경계가 대부분 어두운 외곽선'인 영역만 배경 포켓이다.
    몸통의 밝은 털은 영역이 크거나 경계가 중간톤 털이라 보존된다.
    """
    w, h = img.size
    px = img.load()

    def diffmax(p):
        return max(abs(p[i] - bg[i]) for i in range(3))

    visited = bytearray(w * h)
    for sy in range(h):
        for sx in range(w):
            p = px[sx, sy]
            if visited[sy * w + sx] or p[3] == 0 or diffmax(p) > 8:
                continue
            # 시드에서 POCKET_GROW_TOL 안의 이웃으로 영역 확장
            region = [(sx, sy)]
            visited[sy * w + sx] = 1
            queue = deque(region)
            boundary: list[tuple] = []
            oversize = False
            while queue:
                x, y = queue.popleft()
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    np_ = px[nx, ny]
                    if np_[3] == 0:
                        continue  # 이미 투명(외부와 연결) — 경계로 안 침
                    if visited[ny * w + nx]:
                        continue
                    if diffmax(np_) <= POCKET_GROW_TOL:
                        visited[ny * w + nx] = 1
                        region.append((nx, ny))
                        queue.append((nx, ny))
                        if len(region) > POCKET_MAX_SIZE:
                            oversize = True
                            queue.clear()
                            break
                    else:
                        boundary.append(np_)
            if oversize or not boundary:
                continue  # 몸통 밝은 털(큰 영역)은 보존
            dark = sum(1 for p_ in boundary if diffmax(p_) >= POCKET_DARK_DIFF)
            if dark / len(boundary) >= POCKET_DARK_RATIO:
                for x, y in region:
                    px[x, y] = (0, 0, 0, 0)
    return img


def flood_from_transparent(img: Image.Image, tol: int, bg: tuple) -> Image.Image:
    """이미 투명해진 영역과 맞닿은 배경색 픽셀을 연쇄 제거한다.

    (그림자 잔선 제거로 '아래가 열린' 다리 사이 틈 내부 정리용)
    """
    w, h = img.size
    px = img.load()

    def near_bg(p):
        return all(abs(p[i] - bg[i]) <= tol for i in range(3))

    seen = bytearray(w * h)
    queue = deque()
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] == 0 or not near_bg(p) or seen[y * w + x]:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= nx < w and 0 <= ny < h) or px[nx, ny][3] == 0:
                    seen[y * w + x] = 1
                    queue.append((x, y))
                    break
    while queue:
        x, y = queue.popleft()
        px[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                p = px[nx, ny]
                if p[3] > 0 and near_bg(p):
                    seen[ny * w + nx] = 1
                    queue.append((nx, ny))
    return img


def strip_bottom_shadow(img: Image.Image, bg: tuple, iterations: int = 6) -> Image.Image:
    """크롭 하단 존에서 투명과 맞닿은 그림자/배경 혼합 픽셀을 벗겨낸다.

    발밑 그림자 잔선이 다리 사이 틈을 아래에서 막아 포켓으로 만들기 때문에,
    이 선을 지워야 다음 border flood가 틈 안까지 들어갈 수 있다.
    발 자체는 어두운 외곽선으로 둘러싸여 침식되지 않는다.
    """
    w, h = img.size
    px = img.load()
    zone_y = int(h * 0.72)

    def shadowish(p):
        return all(abs(p[i] - SHADOW[i]) <= 40 for i in range(3)) or all(
            abs(p[i] - bg[i]) <= 45 for i in range(3)
        )

    for _ in range(iterations):
        to_clear = []
        for y in range(zone_y, h):
            for x in range(w):
                p = px[x, y]
                if p[3] == 0 or not shadowish(p):
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if not (0 <= nx < w and 0 <= ny < h) or px[nx, ny][3] == 0:
                        to_clear.append((x, y))
                        break
        if not to_clear:
            break
        for x, y in to_clear:
            px[x, y] = (0, 0, 0, 0)
    return img


def defringe(img: Image.Image, bg: tuple, loose: int = 55, iterations: int = 2) -> Image.Image:
    """투명 영역과 맞닿은 밝은(배경 혼합) 테두리 픽셀을 벗겨낸다.

    어두운 바탕화면에서 스프라이트 둘레에 보이는 흰 헤일로 제거용.
    어두운 외곽선은 배경과 색 차가 커서(> loose) 침식되지 않는다.
    """
    w, h = img.size
    px = img.load()
    for _ in range(iterations):
        to_clear = []
        for y in range(h):
            for x in range(w):
                p = px[x, y]
                if p[3] == 0 or not all(abs(p[i] - bg[i]) <= loose for i in range(3)):
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if not (0 <= nx < w and 0 <= ny < h) or px[nx, ny][3] == 0:
                        to_clear.append((x, y))
                        break
        if not to_clear:
            break
        for x, y in to_clear:
            px[x, y] = (0, 0, 0, 0)
    return img


def count_eroded(original: Image.Image, result: Image.Image, bg: tuple) -> int:
    """원본에서 명백한 '개 픽셀'(배경과 색 차 >60)이었는데 투명해진 수.

    다리 사이처럼 원래 배경이던 정상 구멍은 세지 않고, 얼굴/몸통 침식만 잡는다.
    """
    opx = original.load()
    rpx = result.load()
    w, h = result.size
    eroded = 0
    for y in range(h):
        for x in range(w):
            if rpx[x, y][3] == 0:
                o = opx[x, y]
                if any(abs(o[i] - bg[i]) > 60 for i in range(3)):
                    eroded += 1
    return eroded


def count_bg_remnants(img: Image.Image, bg: tuple) -> int:
    """배경색과 거의 같은(≤8) 불투명 픽셀 수 — 흰색 노출의 원인."""
    px = img.load()
    w, h = img.size
    return sum(
        1
        for y in range(h)
        for x in range(w)
        if px[x, y][3] > 200 and all(abs(px[x, y][i] - bg[i]) <= 8 for i in range(3))
    )


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
        original = crop.convert("RGBA")
        sprite = flood_remove_background(crop, tol)
        sprite = strip_bottom_shadow(sprite, bg_color)
        sprite = flood_from_transparent(sprite, tol, bg_color)  # 열린 틈 내부 정리
        sprite = remove_enclosed_background(sprite, bg_color)
        sprite = defringe(sprite, bg_color, loose=45, iterations=1)
        eroded = count_eroded(original, sprite, bg_color)
        leftover = count_bg_remnants(sprite, bg_color)
        sprite = trim(remove_small_islands(sprite))
        sprite.save(OUT_DIR / f"{name}.png")
        results[name] = sprite
        flags = ""
        # 침식 수치에는 발밑 그림자 정리분(~70px)이 포함되므로 여유를 둔다
        if eroded > 150:
            flags += "  ⚠ 몸통 침식!"
        if leftover > 40:
            flags += "  ⚠ 배경 잔존!"
        print(f"{name}: {sprite.size} 침식={eroded} 배경잔존={leftover}{flags}")

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
