"""펫이 서 있을 '바닥'(작업표시줄 상단) 계산.

Qt의 availableGeometry는 작업표시줄을 제외한 영역이므로, 화면 전체 geometry와
비교하면 하단 작업표시줄의 상단 y 좌표를 DPI 무관하게 얻을 수 있다.
작업표시줄이 숨김/상단/측면이면 화면 맨 아래를 바닥으로 쓴다.
"""


def get_ground(screen) -> tuple[int, int, int]:
    """(걸을 수 있는 x 시작, x 끝, 바닥 y) 를 논리 좌표로 반환한다.

    바닥 y는 펫 창의 '하단'이 닿아야 할 좌표(작업표시줄 최상단)다.
    """
    full = screen.geometry()
    avail = screen.availableGeometry()

    if avail.bottom() < full.bottom():
        # 하단에 작업표시줄이 있음 → 그 위가 바닥
        ground_y = avail.bottom() + 1
    else:
        ground_y = full.bottom() + 1

    return avail.left(), avail.right(), ground_y
