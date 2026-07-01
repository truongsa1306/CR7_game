"""
scenes/eight_queens_scene.py
============================
N-Queens demo for CR7 Game. Supports Backtracking, Forward Checking,
and Min-Conflicts as separate solving algorithms.
"""

import random

import pygame

import config as C
from entities.player import Player
from scenes.base_scene import BaseScene
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_wood_panel, draw_stadium_background

MIN_QUEENS = 4
MAX_QUEENS = 8
DEFAULT_QUEENS = 8
BOARD_X = 40
BOARD_Y = 124
BOARD_SIZE = 304
AUTO_STEP_DELAY = 0.2

ALGORITHMS = [
    {"name": "Backtracking", "desc": "Duyet tung hang, thu cot va quay lui khi xung dot."},
    {"name": "Forward Checking", "desc": "Dung domain de loai cac cot khong kha thi som hon."},
    {"name": "Min-Conflict", "desc": "Local search, di chuyen quan dang gay nhieu xung dot nhat."},
]


def is_safe(board, row, col):
    for r in range(row):
        if board[r] == col or abs(board[r] - col) == abs(r - row):
            return False
    return True


def board_is_solved(board):
    n = len(board)
    if any(col < 0 or col >= n for col in board):
        return False
    for row in range(n):
        for other in range(row + 1, n):
            if board[row] == board[other]:
                return False
            if abs(board[row] - board[other]) == abs(row - other):
                return False
    return True


def total_conflicts(board):
    total = 0
    for row, col in enumerate(board):
        if col == -1:
            continue
        for other_row in range(row + 1, len(board)):
            other_col = board[other_row]
            if other_col == -1:
                continue
            if col == other_col or abs(col - other_col) == abs(row - other_row):
                total += 1
    return total


def format_assignment(board):
    items = [f"Q{row + 1}={col + 1}" for row, col in enumerate(board) if col != -1]
    return "Assignment={" + ", ".join(items) + "}" if items else "Assignment={}"


def format_domain(values):
    return "{" + ",".join(str(value + 1) for value in values) + "}"


def compact_domains(domains, limit=5):
    if not domains:
        return ""
    parts = []
    for index, domain in enumerate(domains[:limit]):
        parts.append(f"Q{index + 1}:{format_domain(sorted(domain))}")
    if len(domains) > limit:
        parts.append("...")
    return " ".join(parts)


def domain_changes(before, after):
    if before is None or after is None:
        return []
    changes = []
    for index, old_domain in enumerate(before):
        removed = sorted(old_domain - after[index])
        if removed:
            changes.append(f"Q{index + 1} bo {format_domain(removed)}")
    return changes


def first_solution(n):
    board = [-1] * n

    def dfs(row):
        if row == n:
            return True
        for col in range(n):
            if is_safe(board, row, col):
                board[row] = col
                if dfs(row + 1):
                    return True
                board[row] = -1
        return False

    return board.copy() if dfs(0) else [-1] * n


def _normalize_seed_board(n, initial_board=None):
    if initial_board is None:
        return [-1] * n
    board = list(initial_board[:n])
    board.extend([-1] * (n - len(board)))
    return [col if isinstance(col, int) and 0 <= col < n else -1 for col in board]


def _preferred_values(values, preferred):
    ordered = sorted(values)
    if preferred in ordered:
        ordered.remove(preferred)
        ordered.insert(0, preferred)
    return ordered


def backtracking_steps(n, initial_board=None):
    seed = _normalize_seed_board(n, initial_board)
    board = seed.copy()
    placed = sum(col != -1 for col in seed)
    steps = [{
        "board": board.copy(),
        "status": (
            f"Khoi tao Backtracking tu {placed} quan hau da dat"
            if placed else "Khoi tao Backtracking"
        ),
        "action": "init",
        "seeded": bool(placed),
    }]

    def dfs(row):
        if row == n:
            steps.append({
                "board": board.copy(),
                "status": "Da tim giai phap bang Backtracking",
                "action": "solution",
            })
            return True

        preferred = seed[row]
        board[row] = -1
        for col in _preferred_values(range(n), preferred):
            steps.append({
                "board": board.copy(),
                "status": f"Thu Q{row + 1}={col + 1}",
                "action": "try",
                "var": row,
                "value": col,
            })
            if is_safe(board, row, col):
                board[row] = col
                steps.append({
                    "board": board.copy(),
                    "status": f"Hop le, gan Q{row + 1}={col + 1}",
                    "action": "place",
                    "var": row,
                    "value": col,
                })
                if dfs(row + 1):
                    return True
                board[row] = -1
                steps.append({
                    "board": board.copy(),
                    "status": f"Quay lui, xoa Q{row + 1}={col + 1}",
                    "action": "backtrack",
                    "var": row,
                    "value": col,
                })
            else:
                steps.append({
                    "board": board.copy(),
                    "status": f"Vi pham rang buoc tai Q{row + 1}={col + 1}",
                    "action": "reject",
                    "var": row,
                    "value": col,
                })
        return False

    dfs(0)
    return steps


def forward_checking_steps(n, initial_board=None):
    seed = _normalize_seed_board(n, initial_board)
    board = seed.copy()
    placed = sum(col != -1 for col in seed)
    domains = [set(range(n)) for _ in range(n)]
    steps = [{
        "board": board.copy(),
        "status": (
            f"Khoi tao Forward Checking tu {placed} quan hau da dat"
            if placed else "Khoi tao Forward Checking"
        ),
        "action": "init",
        "domains": [domain.copy() for domain in domains],
        "seeded": bool(placed),
    }]

    def prune(current_domains, row, col):
        new_domains = [domain.copy() for domain in current_domains]
        for r in range(row + 1, n):
            new_domains[r].discard(col)
            offset = r - row
            new_domains[r].discard(col + offset)
            new_domains[r].discard(col - offset)
            if not new_domains[r]:
                return None
        return new_domains

    def dfs(row, current_domains):
        if row == n:
            steps.append({
                "board": board.copy(),
                "status": "Da tim giai phap bang Forward Checking",
                "action": "solution",
                "domains": [domain.copy() for domain in current_domains],
            })
            return True

        preferred = seed[row]
        board[row] = -1
        for col in _preferred_values(current_domains[row], preferred):
            domain_before = [domain.copy() for domain in current_domains]
            steps.append({
                "board": board.copy(),
                "status": f"Thu Q{row + 1}={col + 1}",
                "action": "try",
                "var": row,
                "value": col,
                "domains": domain_before,
            })
            if not is_safe(board, row, col):
                steps.append({
                    "board": board.copy(),
                    "status": f"Loai Q{row + 1}={col + 1} vi xung dot",
                    "action": "reject",
                    "var": row,
                    "value": col,
                    "domains": domain_before,
                })
                continue
            new_domains = prune(current_domains, row, col)
            board[row] = col
            if new_domains is not None:
                steps.append({
                    "board": board.copy(),
                    "status": f"Gan Q{row + 1}={col + 1} va cat tia domain",
                    "action": "place",
                    "var": row,
                    "value": col,
                    "domains": [domain.copy() for domain in new_domains],
                    "domain_before": domain_before,
                    "domain_changes": domain_changes(domain_before, new_domains),
                })
                if dfs(row + 1, new_domains):
                    return True
                board[row] = -1
                steps.append({
                    "board": board.copy(),
                    "status": f"Quay lui Q{row + 1}: nhanh nay khong thanh cong",
                    "action": "backtrack",
                    "var": row,
                    "value": col,
                    "domains": domain_before,
                })
            else:
                steps.append({
                    "board": board.copy(),
                    "status": f"Loai Q{row + 1}={col + 1}: co domain rong",
                    "action": "prune_fail",
                    "var": row,
                    "value": col,
                    "domains": domain_before,
                })
                board[row] = -1
        return False

    dfs(0, domains)
    return steps


def min_conflicts_steps(n, max_steps=None, max_restarts=20, initial_board=None):
    steps = []
    steps_per_restart = max_steps or max(120, n * n * 20)
    seed = _normalize_seed_board(n, initial_board)
    placed = sum(col != -1 for col in seed)

    for restart in range(max_restarts):
        if restart == 0 and placed:
            board = [col if col != -1 else random.randrange(n) for col in seed]
            label = f"Bat dau Min-Conflict tu {placed} quan da dat; bo sung cac hang con thieu"
        else:
            board = [random.randrange(n) for _ in range(n)]
            label = "Bat dau Min-Conflict voi cau hinh ngau nhien"
            if restart:
                label = f"Restart Min-Conflict lan {restart + 1}"
        steps.append({
            "board": board.copy(),
            "status": label,
            "action": "init" if restart == 0 else "restart",
            "total_conflicts": total_conflicts(board),
            "restart": restart,
            "seeded": bool(placed and restart == 0),
        })

        def conflicts(row, col):
            count = 0
            for r in range(n):
                if r == row:
                    continue
                if board[r] == col or abs(board[r] - col) == abs(r - row):
                    count += 1
            return count

        def row_conflicts(row):
            return conflicts(row, board[row])

        for _ in range(steps_per_restart):
            conflicted = [row for row in range(n) if row_conflicts(row) > 0]
            if not conflicted:
                steps.append({
                    "board": board.copy(),
                    "status": "Da tim giai phap bang Min-Conflict",
                    "action": "solution",
                    "total_conflicts": total_conflicts(board),
                })
                return steps
            row = random.choice(conflicted)
            scores = [(conflicts(row, col), col) for col in range(n)]
            best_score = min(score for score, _ in scores)
            best_cols = [col for score, col in scores if score == best_score]
            best = random.choice(best_cols)
            board[row] = best
            steps.append({
                "board": board.copy(),
                "status": f"Gan lai Q{row + 1}={best + 1}",
                "action": "move",
                "var": row,
                "value": best,
                "scores": scores,
                "best_score": best_score,
                "conflicted_vars": conflicted,
                "total_conflicts": total_conflicts(board),
            })

    fallback = first_solution(n)
    if board_is_solved(fallback):
        steps.append({
            "board": fallback.copy(),
            "status": "Chot loi giai hop le sau cac lan restart",
            "action": "solution",
            "total_conflicts": 0,
        })
    else:
        steps.append({
            "board": fallback.copy(),
            "status": "Khong tim duoc giai phap",
            "action": "failed",
            "total_conflicts": total_conflicts(fallback),
        })
    return steps


class EightQueensScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.board_size = DEFAULT_QUEENS
        self.algo_index = 0
        self.steps = []
        self.step_idx = 0
        self.step_timer = 0.0
        self.auto_play = False
        self.mouse_play = True
        self.done = False
        self.status = "Tu choi: nhan o trong de dat du quan hau"
        self.current_board = self._empty_board()
        self.solution_board = self._empty_board()
        self.hovered_cell = None
        self.selected_cell = None
        self.placed_count = 0
        self.actor_anim_time = 0.0
        self.actor_walk_timer = 0.0
        self.actor_facing = "down"
        self.back_button = Button(pygame.Rect(20, 20, 100, 30), "BACK", font_size=13, on_click=self._go_to_level_select)
        self.prev_button = Button(pygame.Rect(360, 540, 100, 28), "PREV", font_size=14, on_click=self._rewind_ai_step)
        self.run_button = Button(pygame.Rect(480, 540, 100, 28), "RUN", font_size=14, on_click=self._run)
        self.reset_button = Button(pygame.Rect(600, 540, 100, 28), "RESET", font_size=14, on_click=self._reset)
        self.auto_button = Button(pygame.Rect(720, 540, 120, 28), "AUTO", font_size=14, on_click=self._toggle_auto)
        self._reset()

    def on_enter(self, **kwargs):
        self._reset()
        self.game_state.kit_index = 5

    def handle_event(self, event):
        self.back_button.handle_event(event)
        self.prev_button.handle_event(event)
        self.run_button.handle_event(event)
        self.reset_button.handle_event(event)
        self.auto_button.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self.hovered_cell = self._board_cell_at(event.pos)

        if event.type == pygame.KEYDOWN:
            size_key = self._size_from_key(event.key)
            if size_key is not None:
                self._set_board_size(size_key)
                return
            if event.key == pygame.K_r:
                self._reset()
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._run()
                return
            if event.key == pygame.K_RIGHT:
                self._run()
                return
            if event.key == pygame.K_LEFT:
                self._rewind_ai_step()
                return
            if event.key == pygame.K_SPACE:
                self._toggle_auto()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for idx in range(len(ALGORITHMS)):
                if self._algo_button_rect(idx).collidepoint(mx, my):
                    self._select_algorithm(idx)
                    return
            for size in range(MIN_QUEENS, MAX_QUEENS + 1):
                if self._size_button_rect(size).collidepoint(mx, my):
                    self._set_board_size(size)
                    return
            cell = self._board_cell_at((mx, my))
            if cell is not None and self.mouse_play and not self.done:
                self._try_place_click(cell)
            elif cell is not None and not self.mouse_play and not self.auto_play:
                self.status = "Nhan RESET de quay ve che do tu choi"

    def update(self, dt):
        self.actor_anim_time += dt
        if self.actor_walk_timer > 0:
            self.actor_walk_timer = max(0.0, self.actor_walk_timer - dt)
        if self.auto_play and self.steps and not self.done:
            self.step_timer += dt
            if self.step_timer >= AUTO_STEP_DELAY:
                self.step_timer = 0.0
                self._advance_auto_step()

    def draw(self, surface):
        draw_stadium_background(surface)
        draw_text(surface, f"{self.board_size} QUAN HAU", (C.SCREEN_W // 2, 24), size=28, color=C.COL_GOLD_BRIGHT, align="center")
        draw_text(surface, "Giai CSP voi Backtracking - Forward Checking - Min-Conflict", (C.SCREEN_W // 2, 56), size=16, color=C.COL_CREAM_TEXT, align="center")

        for idx in range(len(ALGORITHMS)):
            self._draw_algo_tab(surface, idx)

        board_panel = self._board_rect().inflate(16, 16)
        draw_wood_panel(surface, board_panel, border=3, corner=8, fill=(40, 34, 24))
        self._draw_board(surface)
        self._draw_info_panel(surface)
        self._draw_bottom_panel(surface)

        self.back_button.draw(surface)
        self.prev_button.draw(surface)
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
        n = self.board_size
        conflicted = self._conflicted_cells(board)
        ai_target = self._ai_target_cell()
        ai_target_color = self._ai_target_color()

        for row in range(n):
            for col in range(n):
                cell = self._cell_rect(row, col, inset=2)
                color = (70, 80, 50) if (row + col) % 2 == 0 else (50, 60, 40)
                pygame.draw.rect(surface, color, cell)
                if ai_target == (row, col):
                    pygame.draw.rect(surface, ai_target_color, cell, 4)
                if self.hovered_cell == (row, col):
                    pygame.draw.rect(surface, C.COL_GOLD, cell, 2)
                can_receive_selected = (
                    self.selected_cell is not None
                    and self.mouse_play
                    and not (board[row] == col)
                    and (board[row] == -1 or row == self.selected_cell[0])
                )
                if can_receive_selected:
                    pygame.draw.rect(surface, (120, 110, 70), cell, 1)

        board_rect = self._board_rect()
        for row in range(n + 1):
            y = board_rect.y + row * board_rect.height // n
            pygame.draw.line(surface, C.COL_CREAM_TEXT, (board_rect.x, y), (board_rect.right, y), 2)
        for col in range(n + 1):
            x = board_rect.x + col * board_rect.width // n
            pygame.draw.line(surface, C.COL_CREAM_TEXT, (x, board_rect.y), (x, board_rect.bottom), 2)

        for row in range(n):
            for col in range(n):
                cell = self._cell_rect(row, col, inset=2)
                center = cell.center
                radius = max(8, min(cell.width, cell.height) // 3)
                if board[row] == col:
                    pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, center, radius)
                    pygame.draw.circle(surface, C.COL_BLACK, center, radius, 2)
                    if (row, col) in conflicted:
                        pygame.draw.circle(surface, C.COL_DANGER_RED, center, radius + 4, 3)
                    if self.selected_cell == (row, col):
                        pygame.draw.circle(surface, C.COL_WHITE, center, radius + 7, 2)
                        pygame.draw.circle(surface, C.COL_GOLD, center, radius + 10, 2)

    def _draw_info_panel(self, surface):
        panel = self._info_panel_rect()
        draw_wood_panel(surface, panel, border=4, corner=10, fill=(42, 30, 24))
        algo = ALGORITHMS[self.algo_index]
        draw_text(surface, algo["name"], (panel.centerx, panel.top + 18), size=18, color=C.COL_GOLD_BRIGHT, align="center")
        draw_text(surface, algo["desc"], (panel.centerx, panel.top + 48), size=13, color=C.COL_CREAM_TEXT, align="center", max_width=panel.width - 36)
        self._draw_size_selector(surface, panel)
        draw_text(surface, f"Buoc: {self.step_idx}/{max(len(self.steps) - 1, 0)}", (panel.left + 18, panel.top + 118), size=13, color=C.COL_CREAM_TEXT)

        y = panel.top + 146
        draw_text(surface, "Bieu dien CSP:", (panel.left + 18, y), size=13, color=C.COL_GOLD_BRIGHT)
        y += 22
        for line in self._csp_summary_lines():
            y += draw_text(surface, line, (panel.left + 18, y), size=12, color=C.COL_CREAM_TEXT,
                           max_width=panel.width - 150, shadow=False)

        y = panel.top + 264
        draw_text(surface, "Trang thai:", (panel.left + 18, y), size=13, color=C.COL_GOLD_BRIGHT)
        draw_text(surface, self.steps[self.step_idx]["status"] if self.steps else self.status,
                  (panel.left + 18, y + 22), size=13, color=C.COL_CREAM_TEXT, max_width=panel.width - 150)
        draw_text(surface, "PREV/RUN = lui/tien AI, AUTO = tu chay, RESET = xoa ban co",
                  (panel.left + 18, panel.top + 314), size=11, color=C.COL_CREAM_TEXT, max_width=panel.width - 150)
        self._draw_actor(surface, panel)

    def _draw_size_selector(self, surface, panel):
        draw_text(surface, "So hau:", (panel.left + 18, panel.top + 82), size=13, color=C.COL_GOLD_BRIGHT)
        for size in range(MIN_QUEENS, MAX_QUEENS + 1):
            rect = self._size_button_rect(size)
            selected = size == self.board_size
            base = (90, 60, 34) if selected else (64, 44, 30)
            border = C.COL_GOLD if selected else C.COL_WOOD_DARK
            pygame.draw.rect(surface, base, rect, border_radius=6)
            pygame.draw.rect(surface, border, rect, 2, border_radius=6)
            draw_text(surface, str(size), (rect.centerx, rect.top + 5), size=14,
                      color=C.COL_GOLD_BRIGHT if selected else C.COL_CREAM_TEXT,
                      align="center", shadow=False)

    def _draw_bottom_panel(self, surface):
        panel = pygame.Rect(40, 458, 920, 68)
        draw_wood_panel(surface, panel, border=3, corner=8, fill=(34, 28, 20))
        mode = "AI AUTO" if self.auto_play else ("TU CHOI" if self.mouse_play else "AI")
        draw_text(surface, f"N={self.board_size} | {ALGORITHMS[self.algo_index]['name']} | Che do: {mode}",
                  (panel.left + 14, panel.top + 7), size=12, color=C.COL_GOLD_BRIGHT, align="left")
        y = panel.top + 23
        for line in self._dialogue_lines()[:4]:
            draw_text(surface, line, (panel.left + 14, y), size=11, color=C.COL_CREAM_TEXT,
                      align="left", max_width=panel.width - 28, shadow=False)
            y += 12

    def _current_step(self):
        if not self.steps:
            return {"board": self.current_board, "status": self.status, "action": "manual"}
        self.step_idx = max(0, min(self.step_idx, len(self.steps) - 1))
        return self.steps[self.step_idx]

    def _csp_summary_lines(self):
        step = self._current_step()
        board = self.current_board if self.mouse_play else step.get("board", self.current_board)
        domain_line = f"Domain moi Q_i: {format_domain(range(self.board_size))}"
        if ALGORITHMS[self.algo_index]["name"] == "Forward Checking" and step.get("domains"):
            domain_line = f"Domain hien tai: {compact_domains(step['domains'])}"
        lines = [
            f"Variables: Q1..Q{self.board_size} (Q_i la cot cua hau hang i)",
            domain_line,
            format_assignment(board),
            "Constraints: Qi != Qj va |Qi-Qj| != |i-j|",
        ]
        if ALGORITHMS[self.algo_index]["name"] == "Min-Conflict":
            lines.append(f"So xung dot: {total_conflicts(board)}")
        return lines

    def _dialogue_lines(self):
        if self.mouse_play:
            return [
                self.status,
                f"Tu choi: dat du {self.board_size} quan hau tren ban co.",
                "Click mot quan hau de chon, click o dich de di chuyen.",
                "Thang khi khong co hai hau nao cung cot hoac cung duong cheo.",
            ]
        if not self._is_ai_session():
            return [
                self.status,
                "RUN: AI di tung buoc. PREV: tua lai tung buoc.",
                "AUTO: AI tu chay cac buoc.",
                "RESET de quay lai che do nguoi choi tu sap xep.",
            ]

        name = ALGORITHMS[self.algo_index]["name"]
        if name == "Backtracking":
            return self._backtracking_dialogue_lines()
        if name == "Forward Checking":
            return self._forward_checking_dialogue_lines()
        return self._min_conflict_dialogue_lines()

    def _backtracking_dialogue_lines(self):
        step = self._current_step()
        action = step.get("action")
        row = step.get("var")
        col = step.get("value")
        if action == "init":
            return [
                "Buoc 1: Khoi tao CSP voi assignment rong.",
                f"Variables: Q1..Q{self.board_size}; Domain moi bien = {format_domain(range(self.board_size))}.",
                "Chon bien theo thu tu hang: Q1, Q2, ...; moi Q_i la cot dat hau.",
                "Rang buoc: khong cung cot va khong cung duong cheo.",
            ]
        if action == "try":
            return [
                f"Buoc {self.step_idx}: Chon bien Q{row + 1}, thu gia tri {col + 1}.",
                f"Kiem tra rang buoc voi {format_assignment(step['board'])}.",
                "Neu hop le thi gan vao assignment, neu vi pham thi thu gia tri tiep.",
            ]
        if action == "place":
            return [
                f"Buoc {self.step_idx}: Q{row + 1}={col + 1} hop le.",
                f"Gan thanh cong -> {format_assignment(step['board'])}.",
                f"Chuyen sang bien ke tiep Q{row + 2} neu con bien chua gan.",
            ]
        if action == "reject":
            return [
                f"Buoc {self.step_idx}: Thu Q{row + 1}={col + 1}.",
                "Kiem tra rang buoc -> vi pham cung cot hoac duong cheo.",
                "Khong doi assignment, tiep tuc thu gia tri khac cho bien hien tai.",
            ]
        if action == "backtrack":
            return [
                f"Buoc {self.step_idx}: Nhanh hien tai that bai.",
                f"Quay lui: xoa Q{row + 1}={col + 1} khoi assignment.",
                f"Assignment sau quay lui: {format_assignment(step['board'])}.",
            ]
        return [
            f"Buoc {self.step_idx}: Hoan thanh.",
            f"Loi giai cuoi cung: {format_assignment(step['board'])}.",
            "Tat ca rang buoc deu thoa man.",
        ]

    def _forward_checking_dialogue_lines(self):
        step = self._current_step()
        action = step.get("action")
        row = step.get("var")
        col = step.get("value")
        if action == "init":
            return [
                "Buoc 1: Khoi tao assignment rong va domain cho moi bien.",
                f"Variables: Q1..Q{self.board_size}; Domain ban dau: {format_domain(range(self.board_size))}.",
                "Sau moi lan gan, Forward Checking cat tia domain cua cac bien sau.",
            ]
        if action == "try":
            return [
                f"Buoc {self.step_idx}: Chon bien Q{row + 1}.",
                f"Thu Q{row + 1}={col + 1} trong domain {format_domain(sorted(step['domains'][row]))}.",
                "Kiem tra rang buoc voi assignment hien tai truoc khi cat tia.",
            ]
        if action == "place":
            changes = step.get("domain_changes") or ["khong co gia tri nao bi loai"]
            return [
                f"Buoc {self.step_idx}: Q{row + 1}={col + 1} hop le -> gan vao assignment.",
                "Forward checking: " + "; ".join(changes[:3]) + ".",
                f"Domain con lai: {compact_domains(step.get('domains'))}.",
                format_assignment(step["board"]),
            ]
        if action == "reject":
            return [
                f"Buoc {self.step_idx}: Thu Q{row + 1}={col + 1}.",
                "Kiem tra rang buoc -> vi pham voi assignment hien tai.",
                "Loai gia tri nay va tiep tuc trong domain cua Q hien tai.",
            ]
        if action == "prune_fail":
            return [
                f"Buoc {self.step_idx}: Gan thu Q{row + 1}={col + 1} lam mot domain rong.",
                "Forward checking phat hien nhanh that bai som.",
                "Quay lui ngay thay vi di tiep den cac bien sau.",
            ]
        if action == "backtrack":
            return [
                f"Buoc {self.step_idx}: Khong tim duoc loi giai trong nhanh nay.",
                f"Quay lui va phuc hoi domain truoc khi gan Q{row + 1}.",
                f"Domain phuc hoi: {compact_domains(step.get('domains'))}.",
            ]
        return [
            f"Buoc {self.step_idx}: Hoan thanh Forward Checking.",
            f"Loi giai: {format_assignment(step['board'])}.",
            "Moi bien da gan va moi rang buoc deu thoa man.",
        ]

    def _min_conflict_dialogue_lines(self):
        step = self._current_step()
        action = step.get("action")
        row = step.get("var")
        col = step.get("value")
        if action in ("init", "restart"):
            return [
                "Buoc 1: Khoi tao loi giai day du ngau nhien.",
                format_assignment(step["board"]),
                f"Kiem tra rang buoc -> co {step.get('total_conflicts', total_conflicts(step['board']))} cap xung dot.",
                "Lap: chon mot bien dang xung dot va gan gia tri giam xung dot nhat.",
            ]
        if action == "move":
            scores = ", ".join(f"{candidate + 1}->{score}" for score, candidate in step.get("scores", []))
            return [
                f"Buoc {self.step_idx}: Chon bien gay xung dot Q{row + 1}.",
                f"Thu cac cot cho Q{row + 1} (cot->xung dot): {scores}.",
                f"Chon Q{row + 1}={col + 1}, tong xung dot con {step.get('total_conflicts', total_conflicts(step['board']))}.",
                format_assignment(step["board"]),
            ]
        if action == "failed":
            return [
                "Min-Conflict khong tim thay loi giai trong gioi han restart.",
                "AI dung loi giai backtracking de ket thuc an toan.",
            ]
        return [
            f"Buoc {self.step_idx}: Hoan thanh Min-Conflict.",
            f"Loi giai: {format_assignment(step['board'])}.",
            "Tong xung dot = 0, tat ca rang buoc deu thoa man.",
        ]

    def _ai_target_cell(self):
        if self.mouse_play or not self._is_ai_session():
            return None
        step = self._current_step()
        row = step.get("var")
        col = step.get("value")
        if row is None or col is None:
            return None
        return (row, col)

    def _ai_target_color(self):
        action = self._current_step().get("action")
        if action in ("reject", "prune_fail"):
            return C.COL_DANGER_RED
        if action == "backtrack":
            return C.COL_FIRE
        if action in ("place", "move", "solution"):
            return C.COL_SUCCESS if hasattr(C, "COL_SUCCESS") else (90, 200, 100)
        return C.COL_GOLD

    def _is_ai_session(self):
        return bool(self.steps and self.steps[0].get("action") in ("init", "restart"))

    def _run(self):
        if not self._is_ai_session() or self.done or self.step_idx >= len(self.steps) - 1:
            self._start_solver(auto_play=False)
        self.auto_play = False
        self.auto_button.text = "AUTO"
        self._advance_ai_step()

    def _reset(self):
        self.steps = [{"board": self._empty_board(), "status": "Bat dau moi"}]
        self.current_board = self._empty_board()
        self.solution_board = self._empty_board()
        self.step_idx = 0
        self.step_timer = 0.0
        self.auto_play = False
        self.mouse_play = True
        self.done = False
        self.placed_count = 0
        self.hovered_cell = None
        self.selected_cell = None
        self.auto_button.text = "AUTO"
        self.status = "Tu choi: nhan o trong de dat du quan hau"
        self.actor_walk_timer = 0.0
        self.actor_facing = "down"

    def _toggle_auto(self):
        if self.auto_play:
            self.auto_play = False
            self.auto_button.text = "AUTO"
            self.status = "AI tu chay tam dung"
            return

        if not self._is_ai_session() or self.done or self.step_idx >= len(self.steps) - 1:
            self._start_solver(auto_play=True)
        else:
            self.auto_play = True
            self.mouse_play = False
            self.done = False
            self.selected_cell = None
            self.auto_button.text = "STOP"
        self.status = f"AI tu chay bang {ALGORITHMS[self.algo_index]['name']}"

    def _start_solver(self, auto_play):
        n = self.board_size
        name = ALGORITHMS[self.algo_index]["name"]
        manual_count = self._queen_count() if self.mouse_play else 0
        seed_board = self.current_board.copy() if manual_count else None

        if name == "Backtracking":
            self.steps = backtracking_steps(n, initial_board=seed_board)
        elif name == "Forward Checking":
            self.steps = forward_checking_steps(n, initial_board=seed_board)
        else:
            self.steps = min_conflicts_steps(n, initial_board=seed_board)

        self.step_idx = 0
        self.step_timer = 0.0
        self.auto_play = auto_play
        self.mouse_play = False
        self.done = False
        self.selected_cell = None
        self.current_board = self.steps[0]["board"].copy()
        self.solution_board = self._solution_from_steps()
        self.placed_count = manual_count
        self.auto_button.text = "STOP" if auto_play else "AUTO"
        self.actor_walk_timer = 0.0
        self.actor_facing = "down"
        if manual_count:
            self.status = f"AI bat dau tu {manual_count} quan hau ban da dat va se di chuyen khi can"
        else:
            self.status = f"AI bat dau tu ban co rong bang {name}"

    def _advance_auto_step(self):
        self._advance_ai_step()

    def _advance_ai_step(self):
        previous_board = self.current_board.copy()
        self.step_idx = min(self.step_idx + 1, len(self.steps) - 1)
        self.current_board = self.steps[self.step_idx]["board"].copy()
        self._pulse_actor_for_board_delta(previous_board, self.current_board, fallback="right")
        if self.step_idx >= len(self.steps) - 1:
            self.done = True
            self.auto_play = False
            self.mouse_play = False
            self.auto_button.text = "AUTO"
            self.status = f"AI da giai xong {self.board_size} quan hau"
        else:
            self.status = self.steps[self.step_idx].get("status", "AI dang giai")

    def _rewind_ai_step(self):
        if not self._is_ai_session():
            self.status = "Chua co tien trinh AI de tua lai"
            return
        self.auto_play = False
        self.mouse_play = False
        self.done = False
        self.selected_cell = None
        self.auto_button.text = "AUTO"
        if self.step_idx <= 0:
            self.step_idx = 0
            self.current_board = self.steps[0]["board"].copy()
            self.status = "Dang o buoc dau tien cua AI"
            return
        previous_board = self.current_board.copy()
        self.step_idx -= 1
        self.current_board = self.steps[self.step_idx]["board"].copy()
        self._pulse_actor_for_board_delta(previous_board, self.current_board, fallback="left")
        self.status = f"Tua lai buoc {self.step_idx}: {self.steps[self.step_idx].get('status', '')}"

    def _solution_from_steps(self):
        for step in reversed(self.steps):
            board = step["board"]
            if board_is_solved(board):
                return board.copy()
        return first_solution(self.board_size)

    def _select_algorithm(self, index):
        self.algo_index = index
        self.auto_play = False
        self.auto_button.text = "AUTO"
        self.step_timer = 0.0
        if self.mouse_play and not self.done:
            # Giữ nguyên các quân người chơi đã đặt; RUN/AUTO sẽ tiếp tục từ đó.
            self.steps = [{
                "board": self.current_board.copy(),
                "status": f"Da chon {ALGORITHMS[index]['name']}",
                "action": "manual",
            }]
            self.step_idx = 0
            self.solution_board = self._empty_board()
            self.selected_cell = None
            self.status = (
                f"Da chon {ALGORITHMS[index]['name']}. "
                f"Giu nguyen {self._queen_count()} quan da dat."
            )
            return
        self._reset()
        self.algo_index = index
        self.status = f"Da chon {ALGORITHMS[index]['name']}"

    def _set_board_size(self, size):
        size = max(MIN_QUEENS, min(MAX_QUEENS, size))
        if size == self.board_size:
            self.status = f"Dang chon {size} quan hau"
            return
        self.board_size = size
        self._reset()
        self.status = f"Da chon {size} quan hau"

    def _board_cell_at(self, pos):
        board_rect = self._board_rect()
        mx, my = pos
        if not board_rect.collidepoint(mx, my):
            return None
        col = (mx - board_rect.x) * self.board_size // board_rect.width
        row = (my - board_rect.y) * self.board_size // board_rect.height
        return (row, col)

    def _next_unplaced_row(self):
        for row, col in enumerate(self.current_board):
            if col == -1:
                return row
        return None

    def _try_place_click(self, cell):
        if self.done or not self.mouse_play:
            return
        row, col = cell
        clicked_queen = self.current_board[row] == col

        if clicked_queen:
            if self.selected_cell == (row, col):
                self.selected_cell = None
                self.status = "Da bo chon quan hau"
            else:
                self.selected_cell = (row, col)
                self.status = f"Da chon hau tai ({row + 1}, {col + 1})"
            return

        if self.selected_cell is not None:
            self._move_selected_queen(row, col)
            return

        if self._queen_count() >= self.board_size:
            self.status = "Da du quan hau, hay chon mot quan de di chuyen"
            return

        if self.current_board[row] != -1:
            self.status = "Hang nay da co hau, hay chon quan do de di chuyen"
            return

        self.current_board[row] = col
        self.placed_count = self._queen_count()
        self.status = f"Da dat hau {self.placed_count}/{self.board_size}"
        self._pulse_actor("right")
        self._check_player_win()

    def _move_selected_queen(self, row, col):
        old_row, old_col = self.selected_cell
        if row != old_row and self.current_board[row] != -1:
            self.status = "O dich nam tren hang da co hau"
            return
        self.current_board[old_row] = -1
        self.current_board[row] = col
        self.selected_cell = (row, col)
        self.status = f"Di chuyen hau tu ({old_row + 1}, {old_col + 1}) den ({row + 1}, {col + 1})"
        self._pulse_actor_for_move((old_col, old_row), (col, row))
        self._check_player_win()

    def _check_player_win(self):
        count = self._queen_count()
        if count < self.board_size:
            return
        if board_is_solved(self.current_board):
            self._finish_game()
            return
        conflicts = len(self._conflicted_cells(self.current_board))
        self.status = f"Chua dung, con {conflicts} quan dang xung dot"

    def _finish_game(self):
        self.done = True
        self.mouse_play = False
        self.auto_play = False
        self.selected_cell = None
        self.auto_button.text = "AUTO"
        self.status = "Ban da thang! Tat ca hau da dat dung."

    def _empty_board(self):
        return [-1] * self.board_size

    def _queen_count(self):
        return sum(1 for col in self.current_board if col != -1)

    def _conflicted_cells(self, board):
        conflicted = set()
        for row, col in enumerate(board):
            if col == -1:
                continue
            for other_row in range(row + 1, len(board)):
                other_col = board[other_row]
                if other_col == -1:
                    continue
                same_col = col == other_col
                same_diag = abs(col - other_col) == abs(row - other_row)
                if same_col or same_diag:
                    conflicted.add((row, col))
                    conflicted.add((other_row, other_col))
        return conflicted

    def _pulse_actor(self, facing):
        self.actor_facing = facing
        self.actor_walk_timer = 0.42

    def _pulse_actor_for_move(self, previous, current):
        self._pulse_actor(
            Player.facing_from_delta(
                current[0] - previous[0],
                current[1] - previous[1],
                fallback=self.actor_facing,
            )
        )

    def _pulse_actor_for_board_delta(self, previous_board, current_board, fallback="right"):
        for row, (old_col, new_col) in enumerate(zip(previous_board, current_board)):
            if old_col == new_col:
                continue
            if old_col >= 0 and new_col >= 0:
                self._pulse_actor_for_move((old_col, row), (new_col, row))
            elif new_col >= 0:
                self._pulse_actor(fallback)
            else:
                self._pulse_actor("left")
            return
        self._pulse_actor(fallback)

    def _draw_actor(self, surface, panel):
        actor_rect = pygame.Rect(panel.right - 104, panel.top + 142, 78, 122)
        Player.draw_in_rect(
            surface,
            actor_rect,
            kit_index=max(0, min(self.game_state.kit_index, len(C.KITS) - 1)),
            state="walk" if self.actor_walk_timer > 0 else "idle",
            facing=self.actor_facing,
            anim_time=self.actor_anim_time,
        )

    def _board_rect(self):
        return pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE)

    def _cell_rect(self, row, col, inset=0):
        board_rect = self._board_rect()
        n = self.board_size
        left = board_rect.x + col * board_rect.width // n
        right = board_rect.x + (col + 1) * board_rect.width // n
        top = board_rect.y + row * board_rect.height // n
        bottom = board_rect.y + (row + 1) * board_rect.height // n
        return pygame.Rect(left + inset, top + inset,
                           max(1, right - left - inset * 2),
                           max(1, bottom - top - inset * 2))

    def _info_panel_rect(self):
        return pygame.Rect(388, 116, 572, 336)

    def _size_button_rect(self, size):
        panel = self._info_panel_rect()
        index = size - MIN_QUEENS
        return pygame.Rect(panel.left + 118 + index * 56, panel.top + 76, 46, 28)

    def _size_from_key(self, key):
        key_map = {
            pygame.K_4: 4,
            pygame.K_5: 5,
            pygame.K_6: 6,
            pygame.K_7: 7,
            pygame.K_8: 8,
            pygame.K_KP4: 4,
            pygame.K_KP5: 5,
            pygame.K_KP6: 6,
            pygame.K_KP7: 7,
            pygame.K_KP8: 8,
        }
        return key_map.get(key)

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)
