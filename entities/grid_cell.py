"""
entities/grid_cell.py
======================
Lightweight grid data model shared by the gameplay scene and every
search/hill-climbing algorithm. Kept free of pygame drawing code on
purpose -- rendering lives in scenes/gameplay_scene.py.

Thay đổi so với bản gốc:
- GridModel.__init__ chấp nhận start=None (multi-source) và goal=None
  (no-goal traversal). Khi None, không cố gắng đặt kind cho cell đó.
"""
from dataclasses import dataclass, field
import config as C

ORTHOGONAL_DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass
class Cell:
    col: int
    row: int
    kind: str = "grass"      # grass | path | danger | fire | wall | start | trophy
    revealed: bool = True    # fog-of-war visibility (Level 0 starts False)
    g: float = 0.0           # cost-so-far (informed search display)
    h: float = 0.0           # heuristic estimate to goal
    f: float = 0.0           # g + h

    @property
    def cost(self):
        return C.CELL_COST.get(self.kind, -1)

    @property
    def passable(self):
        return self.kind != "wall"


class GridModel:
    def __init__(self, cols, rows, start, goal, fog=False):
        self.cols  = cols
        self.rows  = rows
        self.start = start   # может быть None (multi-source)
        self.goal  = goal    # может быть None (no-goal traversal)
        self.fog   = fog
        self.cells = {
            (c, r): Cell(c, r, kind="grass", revealed=not fog)
            for r in range(rows) for c in range(cols)
        }
        # Đặt kind cho start / goal chỉ khi chúng là tuple hợp lệ
        if start is not None and start in self.cells:
            self.cells[start].kind = "start"
            self.cells[start].revealed = True
        if goal is not None and goal in self.cells:
            self.cells[goal].kind = "trophy"
            self.cells[goal].revealed = True

    # ------------------------------------------------------------------
    def set_kind(self, col, row, kind):
        if (col, row) in self.cells:
            self.cells[(col, row)].kind = kind

    def get(self, col, row):
        return self.cells.get((col, row))

    def in_bounds(self, col, row):
        return 0 <= col < self.cols and 0 <= row < self.rows

    def neighbors(self, col, row):
        """Return only orthogonal neighbors (left/right/up/down)."""
        for dc, dr in ORTHOGONAL_DIRECTIONS:
            nc, nr = col + dc, row + dr
            if self.in_bounds(nc, nr):
                cell = self.cells[(nc, nr)]
                if cell.passable:
                    yield cell

    def reveal_around(self, col, row, radius=1):
        self.cells[(col, row)].revealed = True
        for step in range(1, radius + 1):
            for dc, dr in ORTHOGONAL_DIRECTIONS:
                nc, nr = col + dc * step, row + dr * step
                if self.in_bounds(nc, nr):
                    self.cells[(nc, nr)].revealed = True

    def manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def heuristic_value(self, col, row):
        """Used by Hill Climbing levels: higher is better. Combines
        proximity to the goal with cell safety, roughly matching the
        'Heuristic Lân Cận' panel in the reference screenshots.

        Nếu goal=None, trả về giá trị dựa trên safety của ô thôi
        (không có đích → không ước tính khoảng cách).
        """
        cell = self.cells[(col, row)]
        danger_penalty = {"fire": 8, "danger": 3}.get(cell.kind, 0)
        if self.goal is None:
            return 10 - danger_penalty   # chỉ dựa trên safety
        max_dist = self.cols + self.rows
        dist = self.manhattan((col, row), self.goal)
        proximity_score = (max_dist - dist) * 2
        return proximity_score - danger_penalty
