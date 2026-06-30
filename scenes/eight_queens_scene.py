"""
scenes/eight_queens_scene.py
============================
Eight-Queens demo for CR7 Game. Supports Backtracking, Forward Checking,
and Min-Conflicts as separate solving algorithms.
"""

import random

import pygame

import config as C
from scenes.base_scene import BaseScene
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_wood_panel, draw_stadium_background

N = 8
CELL = 50
BOARD_X = 40
BOARD_Y = 90

ALGORITHMS = [
    {"name": "Backtracking", "desc": "Duyệt lại từng hàng, thử cột và quay lui khi xung đột."},
    {"name": "Forward Checking", "desc": "Dùng domain để loại các cột không khả thi sớm hơn."},
    {"name": "Min-Conflict", "desc": "Local search, di chuyển quân gây nhiều xung đột nhất."},
]


def is_safe(board, row, col):
    for r in range(row):
        if board[r] == col or abs(board[r] - col) == abs(r - row):
            return False
    return True


def backtracking_steps(n):
    board = [-1] * n
    steps = [{"board": board.copy(), "status": "Bắt đầu Backtracking"}]

    def dfs(row):
        if row == n:
            steps.append({"board": board.copy(), "status": "Đã tìm giải pháp bằng Backtracking"})
            return True
        for col in range(n):
            if is_safe(board, row, col):
                board[row] = col
                steps.append({"board": board.copy(), "status": f"Đặt hậu tại ({row + 1}, {col + 1})"})
                if dfs(row + 1):
                    return True
                board[row] = -1
                steps.append({"board": board.copy(), "status": f"Quay lui hàng {row + 1}"})
        return False

    dfs(0)
    return steps


def forward_checking_steps(n):
    board = [-1] * n
    domains = [set(range(n)) for _ in range(n)]
    steps = [{"board": board.copy(), "status": "Bắt đầu Forward Checking"}]

    def prune(domains, row, col):
        new_domains = [d.copy() for d in domains]
        for r in range(row + 1, n):
            if col in new_domains[r]:
                new_domains[r].remove(col)
            offset = r - row
            if col + offset in new_domains[r]:
                new_domains[r].remove(col + offset)
            if col - offset in new_domains[r]:
                new_domains[r].remove(col - offset)
            if not new_domains[r]:
                return None
        return new_domains

    def dfs(row, domains):
        if row == n:
            steps.append({"board": board.copy(), "status": "Đã tìm giải pháp bằng Forward Checking"})
            return True
        for col in sorted(domains[row]):
            if not is_safe(board, row, col):
                continue
            new_domains = prune(domains, row, col)
            board[row] = col
            steps.append({"board": board.copy(), "status": f"Đặt hậu tại ({row + 1}, {col + 1})"})
            if new_domains is not None and dfs(row + 1, new_domains):
                return True
            board[row] = -1
            steps.append({"board": board.copy(), "status": f"Quay lui hàng {row + 1}"})
        return False

    dfs(0, domains)
    return steps


def min_conflicts_steps(n, max_steps=300):
    board = [random.randrange(n) for _ in range(n)]
    steps = [{"board": board.copy(), "status": "Bắt đầu Min-Conflict với cấu hình ngẫu nhiên"}]

    def conflicts(row, col):
        count = 0
        for r in range(n):
            if r == row:
                continue
            if board[r] == col or abs(board[r] - col) == abs(r - row):
                count += 1
        return count

    def row_conflicts(r):
        return conflicts(r, board[r])

    for step in range(max_steps):
        conflicted = [r for r in range(n) if row_conflicts(r) > 0]
        if not conflicted:
            steps.append({"board": board.copy(), "status": "Đã tìm giải pháp bằng Min-Conflict"})
            break
        row = random.choice(conflicted)
        best = min(range(n), key=lambda c: conflicts(row, c))
        board[row] = best
        steps.append({"board": board.copy(), "status": f"Di chuyển hàng {row + 1} sang cột {best + 1}"})
    else:
        steps.append({"board": board.copy(), "status": "Không tìm được giải pháp trong giới hạn bước"})
    return steps


class EightQueensScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.algo_index = 0
        self.steps = []
        self.step_idx = 0
        self.step_timer = 0.0
        self.auto_play = False
        self.mouse_play = False
        self.done = False
        self.status = "Chọn thuật toán và nhấn RUN để giải"
        self.current_board = [-1] * N
        self.solution_board = [-1] * N
        self.hovered_cell = None
        self.placed_count = 0
        self.back_button = Button(pygame.Rect(20, 20, 100, 30), "BACK", font_size=13, on_click=self._go_to_level_select)
        self.run_button = Button(pygame.Rect(480, 520, 100, 32), "RUN", font_size=14, on_click=self._run)
        self.reset_button = Button(pygame.Rect(600, 520, 100, 32), "RESET", font_size=14, on_click=self._reset)
        self.auto_button = Button(pygame.Rect(720, 520, 120, 32), "AUTO", font_size=14, on_click=self._toggle_auto)
        self._reset()

    def on_enter(self, **kwargs):
        self._reset()
        self.game_state.kit_index = 5

    def handle_event(self, event):
        self.back_button.handle_event(event)
        self.run_button.handle_event(event)
        self.reset_button.handle_event(event)
        self.auto_button.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self.hovered_cell = self._board_cell_at(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for idx in range(len(ALGORITHMS)):
                if self._algo_button_rect(idx).collidepoint(mx, my):
                    self.algo_index = idx
                    self.status = f"Đã chọn {ALGORITHMS[idx]['name']}"
                    self.steps = []
                    self.step_idx = 0
                    self.auto_play = False
                    self.mouse_play = False
                    self.done = False
                    return
            cell = self._board_cell_at((mx, my))
            if cell is not None and self.mouse_play and not self.done:
                self._try_place_click(cell)

    def update(self, dt):
        if self.auto_play and self.steps and not self.done:
            self.step_timer += dt
            if self.step_timer >= 0.2:
                self.step_timer = 0.0
                self.step_idx += 1
                if self.step_idx >= len(self.steps):
                    self.step_idx = len(self.steps) - 1
                self.current_board = self.steps[self.step_idx]["board"].copy()
                if self.step_idx >= len(self.steps) - 1:
                    self.step_idx = len(self.steps) - 1
                    self.done = True
                    self.auto_play = False
                    self.status = "Thuật toán hoàn thành"

    def draw(self, surface):
        draw_stadium_background(surface)
        draw_text(surface, "8 QUAN HAU", (C.SCREEN_W // 2, 24), size=28, color=C.COL_GOLD_BRIGHT, align="center")
        draw_text(surface, "Giải CSP với Backtracking - Forward Checking - Min-Conflict", (C.SCREEN_W // 2, 56), size=16, color=C.COL_CREAM_TEXT, align="center")

        for idx in range(len(ALGORITHMS)):
            self._draw_algo_tab(surface, idx)

        draw_wood_panel(surface, pygame.Rect(BOARD_X - 8, BOARD_Y - 8, N * CELL + 16, N * CELL + 16), border=3, corner=8, fill=(40, 34, 24))
        self._draw_board(surface)
        self._draw_info_panel(surface)
        self._draw_bottom_panel(surface)

        self.back_button.draw(surface)
        self.run_button.draw(surface)
        self.reset_button.draw(surface)
        self.auto_button.draw(surface)

    def _algo_button_rect(self, index):
        return pygame.Rect(120 + index * 220, 74, 200, 32)

    def _draw_algo_tab(self, surface, index):
        rect = self._algo_button_rect(index)
        selected = index == self.algo_index
        base = (90, 60, 34) if selected else (64, 44, 30)
        border = C.COL_GOLD if selected else C.COL_WOOD_DARK
        pygame.draw.rect(surface, base, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)
        draw_text(surface, ALGORITHMS[index]["name"], rect.center, size=14,
                  color=C.COL_GOLD_BRIGHT if selected else C.COL_CREAM_TEXT,
                  align="center")

    def _draw_board(self, surface):
        board = self.current_board
        target = self._target_cell()

        for r in range(N):
            for c in range(N):
                cell = pygame.Rect(BOARD_X + c * CELL + 2, BOARD_Y + r * CELL + 2, CELL - 4, CELL - 4)
                color = (70, 80, 50) if (r + c) % 2 == 0 else (50, 60, 40)
                pygame.draw.rect(surface, color, cell)
                if self.hovered_cell == (r, c):
                    pygame.draw.rect(surface, C.COL_GOLD, cell, 2)

        for r in range(N + 1):
            y = BOARD_Y + r * CELL
            pygame.draw.line(surface, C.COL_CREAM_TEXT, (BOARD_X, y), (BOARD_X + N * CELL, y), 2)
        for c in range(N + 1):
            x = BOARD_X + c * CELL
            pygame.draw.line(surface, C.COL_CREAM_TEXT, (x, BOARD_Y), (x, BOARD_Y + N * CELL), 2)

        for r in range(N):
            for c in range(N):
                cell = pygame.Rect(BOARD_X + c * CELL + 2, BOARD_Y + r * CELL + 2, CELL - 4, CELL - 4)
                center = cell.center
                if board[r] == c:
                    pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, center, CELL // 3)
                    pygame.draw.circle(surface, C.COL_BLACK, center, CELL // 3, 2)
                elif self.mouse_play and self.solution_board[r] == c and self.current_board[r] == -1:
                    pygame.draw.circle(surface, (255, 240, 160), center, CELL // 5, 2)
                    pygame.draw.circle(surface, (255, 220, 100), center, CELL // 8)

                if target == (r, c):
                    pygame.draw.circle(surface, (255, 240, 150), center, CELL // 5)

    def _draw_info_panel(self, surface):
        panel = pygame.Rect(520, 120, 430, 340)
        draw_wood_panel(surface, panel, border=4, corner=10, fill=(42, 30, 24))
        algo = ALGORITHMS[self.algo_index]
        draw_text(surface, algo["name"], (panel.centerx, panel.top + 18), size=18, color=C.COL_GOLD_BRIGHT, align="center")
        draw_text(surface, algo["desc"], (panel.centerx, panel.top + 50), size=13, color=C.COL_CREAM_TEXT, align="center")
        draw_text(surface, f"Bước: {self.step_idx}/{len(self.steps) - 1}", (panel.left + 18, panel.top + 100), size=13, color=C.COL_CREAM_TEXT)
        draw_text(surface, f"Trạng thái:", (panel.left + 18, panel.top + 130), size=13, color=C.COL_GOLD_BRIGHT)
        draw_text(surface, self.steps[self.step_idx]["status"] if self.steps else self.status,
                  (panel.left + 18, panel.top + 154), size=13, color=C.COL_CREAM_TEXT, max_width=panel.width - 36)
        draw_text(surface, self.status, (panel.left + 18, panel.top + 240), size=14, color=C.COL_GOLD_BRIGHT)
        draw_text(surface, "Nút:", (panel.left + 18, panel.top + 274), size=13, color=C.COL_GOLD_BRIGHT)
        draw_text(surface, "RUN = giải, RESET = khởi tạo lại, AUTO = tự chạy",
                  (panel.left + 18, panel.top + 298), size=12, color=C.COL_CREAM_TEXT, max_width=panel.width - 36)

    def _draw_bottom_panel(self, surface):
        panel = pygame.Rect(40, 470, 820, 42)
        draw_wood_panel(surface, panel, border=3, corner=8, fill=(34, 28, 20))
        draw_text(surface, f"Thuật toán: {ALGORITHMS[self.algo_index]['name']} | Bước: {self.step_idx}/{max(len(self.steps) - 1, 0)}",
                  (panel.left + 14, panel.top + 8), size=13, color=C.COL_CREAM_TEXT, align="topleft")
        mode = "AUTO" if self.auto_play else "TAY"
        draw_text(surface, f"Trạng thái: {self.status} | Chế độ: {mode}",
                  (panel.left + 14, panel.top + 24), size=12, color=C.COL_GOLD_BRIGHT, align="topleft")

    def _run(self):
        if ALGORITHMS[self.algo_index]["name"] == "Backtracking":
            self.steps = backtracking_steps(N)
        elif ALGORITHMS[self.algo_index]["name"] == "Forward Checking":
            self.steps = forward_checking_steps(N)
        else:
            self.steps = min_conflicts_steps(N)
        self.step_idx = 0
        self.step_timer = 0.0
        self.auto_play = False
        self.mouse_play = True
        self.done = False
        self.current_board = [-1] * N
        self.solution_board = self.steps[-1]["board"].copy()
        self.placed_count = 0
        self.status = "Di chuột đúng ô để đặt hậu từng hàng"

    def _reset(self):
        self.steps = [{"board": [-1] * N, "status": "Bắt đầu mới"}]
        self.current_board = [-1] * N
        self.solution_board = [-1] * N
        self.step_idx = 0
        self.step_timer = 0.0
        self.auto_play = False
        self.mouse_play = False
        self.done = False
        self.placed_count = 0
        self.status = "Chọn thuật toán và nhấn RUN để giải"

    def _toggle_auto(self):
        if self.steps and len(self.steps) > 1:
            self.auto_play = not self.auto_play
            self.mouse_play = False
            self.status = "Tự chạy BẬT" if self.auto_play else "Tự chạy TẮT"

    def _board_cell_at(self, pos):
        mx, my = pos
        if not (BOARD_X <= mx < BOARD_X + N * CELL and BOARD_Y <= my < BOARD_Y + N * CELL):
            return None
        col = (mx - BOARD_X) // CELL
        row = (my - BOARD_Y) // CELL
        return (row, col)

    def _next_unplaced_row(self):
        for row, col in enumerate(self.current_board):
            if col == -1:
                return row
        return None

    def _target_cell(self):
        row = self._next_unplaced_row()
        if row is None or self.solution_board[row] == -1:
            return None
        return (row, self.solution_board[row])

    def _try_place_click(self, cell):
        if self.done or not self.mouse_play:
            return
        row, col = cell
        next_row = self._next_unplaced_row()
        if next_row is None:
            return
        if row != next_row:
            self.status = f"Chọn hàng {next_row + 1} trước" 
            return
        if self.solution_board[row] != col:
            self.status = "Sai ô! Nhấp vào ô có cờ vàng để đúng." 
            return
        self.current_board[row] = col
        self.placed_count += 1
        self.status = f"Đã đặt hậu hàng {row + 1}."
        if self.placed_count >= N:
            self._finish_game()

    def _finish_game(self):
        self.done = True
        self.mouse_play = False
        self.auto_play = False
        self.status = "Bạn đã thắng! Tất cả hậu đã đặt đúng." 

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)
