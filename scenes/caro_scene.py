"""Dynamic adversarial Caro scene with Minimax, Alpha-Beta and Expectimax.

The board size is configurable from 3x3 to 12x12.  The drawing area scales
with ``n`` and the AI panel shows the candidate nodes evaluated for the most
recent move.
"""

from __future__ import annotations

import random

import pygame

import config as C
from entities.player import Player
from scenes.base_scene import BaseScene
from systems.asset_manager import AssetManager
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_stadium_background, draw_wood_panel

EMPTY = 0
HUMAN = 1
AI = 2

DEFAULT_BOARD_SIZE = 5
MIN_BOARD_SIZE = 3
MAX_BOARD_SIZE = 12
DEFAULT_WIN_LENGTH = 4

BOARD_PANEL = pygame.Rect(24, 108, 548, 444)
SIDE_PANEL = pygame.Rect(586, 108, 414, 444)
TRACE_RECT = pygame.Rect(SIDE_PANEL.left + 12, SIDE_PANEL.top + 205, SIDE_PANEL.width - 24, 168)

ALGORITHMS = [
    {
        "name": "Minimax",
        "depth": 3,
        "desc": "Duyệt cây trò chơi và giả sử đối thủ luôn đánh tối ưu.",
    },
    {
        "name": "Alpha-Beta",
        "depth": 4,
        "desc": "Cắt tỉa nhánh không cần thiết nhưng vẫn giữ kết quả Minimax.",
    },
    {
        "name": "Expectimax",
        "depth": 3,
        "desc": "Đánh giá nước đi theo kỳ vọng khi đối thủ không hoàn toàn tối ưu.",
    },
]


def board_size(board):
    return len(board)


def win_length(board):
    return min(DEFAULT_WIN_LENGTH, board_size(board))


def check_win(board, player):
    n = board_size(board)
    target = win_length(board)
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    for row in range(n):
        for col in range(n):
            for dr, dc in directions:
                end_row = row + (target - 1) * dr
                end_col = col + (target - 1) * dc
                if not (0 <= end_row < n and 0 <= end_col < n):
                    continue
                if all(board[row + step * dr][col + step * dc] == player for step in range(target)):
                    return True
    return False


def is_full(board):
    return all(value != EMPTY for row in board for value in row)


def score_line(board, player):
    n = board_size(board)
    target = win_length(board)
    opponent = 3 - player
    score = 0
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))

    for row in range(n):
        for col in range(n):
            for dr, dc in directions:
                end_row = row + (target - 1) * dr
                end_col = col + (target - 1) * dc
                if not (0 <= end_row < n and 0 <= end_col < n):
                    continue

                values = [board[row + step * dr][col + step * dc] for step in range(target)]
                own_count = values.count(player)
                opponent_count = values.count(opponent)

                if opponent_count == 0 and own_count:
                    if own_count == target:
                        score += 1000
                    elif own_count == target - 1:
                        score += 55
                    elif own_count == target - 2:
                        score += 7
                    else:
                        score += 1
                elif own_count == 0 and opponent_count:
                    if opponent_count == target:
                        score -= 1000
                    elif opponent_count == target - 1:
                        score -= 65
                    elif opponent_count == target - 2:
                        score -= 8
                    else:
                        score -= 1
    return score


def evaluate(board):
    if check_win(board, AI):
        return 9000
    if check_win(board, HUMAN):
        return -9000
    return score_line(board, AI)


def get_moves(board, limit=14):
    """Return useful empty cells instead of expanding every square on large boards."""
    n = board_size(board)
    empty = [(row, col) for row in range(n) for col in range(n) if board[row][col] == EMPTY]
    if not empty:
        return []

    occupied = [(row, col) for row in range(n) for col in range(n) if board[row][col] != EMPTY]
    if not occupied:
        center = n // 2
        return sorted(empty, key=lambda pos: abs(pos[0] - center) + abs(pos[1] - center))[:limit]

    candidates = set()
    for row, col in occupied:
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = row + dr, col + dc
                if 0 <= nr < n and 0 <= nc < n and board[nr][nc] == EMPTY:
                    candidates.add((nr, nc))

    if len(candidates) < min(8, len(empty)):
        for row, col in occupied:
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < n and 0 <= nc < n and board[nr][nc] == EMPTY:
                        candidates.add((nr, nc))

    if not candidates:
        candidates.update(empty)

    center = (n - 1) / 2

    def priority(pos):
        row, col = pos
        neighbours = 0
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = row + dr, col + dc
                if 0 <= nr < n and 0 <= nc < n and board[nr][nc] != EMPTY:
                    neighbours += 1
        distance = abs(row - center) + abs(col - center)
        return (-neighbours, distance, row, col)

    return sorted(candidates, key=priority)[:limit]


def minimax(board, depth, is_max, nodes):
    nodes[0] += 1
    if check_win(board, AI):
        return 9000 - depth
    if check_win(board, HUMAN):
        return -9000 + depth
    if is_full(board) or depth == 0:
        return evaluate(board)

    moves = get_moves(board)
    if is_max:
        best = -99999
        for row, col in moves:
            board[row][col] = AI
            best = max(best, minimax(board, depth - 1, False, nodes))
            board[row][col] = EMPTY
        return best

    best = 99999
    for row, col in moves:
        board[row][col] = HUMAN
        best = min(best, minimax(board, depth - 1, True, nodes))
        board[row][col] = EMPTY
    return best


def alphabeta(board, depth, alpha, beta, is_max, nodes):
    nodes[0] += 1
    if check_win(board, AI):
        return 9000 - depth
    if check_win(board, HUMAN):
        return -9000 + depth
    if is_full(board) or depth == 0:
        return evaluate(board)

    moves = get_moves(board)
    if is_max:
        best = -99999
        for row, col in moves:
            board[row][col] = AI
            best = max(best, alphabeta(board, depth - 1, alpha, beta, False, nodes))
            board[row][col] = EMPTY
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best

    best = 99999
    for row, col in moves:
        board[row][col] = HUMAN
        best = min(best, alphabeta(board, depth - 1, alpha, beta, True, nodes))
        board[row][col] = EMPTY
        beta = min(beta, best)
        if beta <= alpha:
            break
    return best


def expectimax(board, depth, is_max, nodes):
    nodes[0] += 1
    if check_win(board, AI):
        return 9000 - depth
    if check_win(board, HUMAN):
        return -9000 + depth
    if is_full(board) or depth == 0:
        return evaluate(board)

    moves = get_moves(board)
    if is_max:
        best = -99999
        for row, col in moves:
            board[row][col] = AI
            best = max(best, expectimax(board, depth - 1, False, nodes))
            board[row][col] = EMPTY
        return best

    total = 0.0
    for row, col in moves:
        board[row][col] = HUMAN
        value = expectimax(board, depth - 1, True, nodes)
        total += value * 0.8 + random.uniform(-50, 50) * 0.2
        board[row][col] = EMPTY
    return total / len(moves) if moves else 0.0


def best_move_ai(board, algorithm_name, depth):
    """Return the chosen move, expanded-node count and candidate trace."""
    moves = get_moves(board)
    nodes = [0]
    best_value = -99999
    best_move = None
    trace = []

    for order, (row, col) in enumerate(moves, start=1):
        before = nodes[0]
        board[row][col] = AI
        if algorithm_name == "Minimax":
            value = minimax(board, depth - 1, False, nodes)
        elif algorithm_name == "Alpha-Beta":
            value = alphabeta(board, depth - 1, -99999, 99999, False, nodes)
        else:
            value = expectimax(board, depth - 1, False, nodes)
        board[row][col] = EMPTY

        trace.append(
            {
                "order": order,
                "move": (row, col),
                "score": value,
                "nodes": nodes[0] - before,
                "total_nodes": nodes[0],
                "selected": False,
            }
        )
        if value > best_value:
            best_value = value
            best_move = (row, col)

    for item in trace:
        item["selected"] = item["move"] == best_move
    return best_move, nodes[0], trace, best_value


class CaroScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.algo_index = 1
        self.board_n = DEFAULT_BOARD_SIZE
        self.board = None
        self.turn = HUMAN
        self.game_over = False
        self.winner = None
        self.status = ""
        self.nodes = 0
        self.ai_move = None
        self.best_score = None
        self.history = []
        self.search_trace = []
        self.trace_scroll = 0
        self.experiment_results = {}
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.cell_size = 1
        self.actor_anim_time = 0.0
        self.actor_walk_timer = 0.0
        self.actor_facing = "down"

        self.back_button = Button(
            pygame.Rect(18, 18, 102, 30), "BACK", font_size=13, on_click=self._go_to_level_select
        )
        self.size_down_button = Button(
            pygame.Rect(SIDE_PANEL.left + 14, SIDE_PANEL.top + 14, 62, 28),
            "N -",
            font_size=12,
            on_click=lambda: self._change_board_size(-1),
        )
        self.size_up_button = Button(
            pygame.Rect(SIDE_PANEL.right - 76, SIDE_PANEL.top + 14, 62, 28),
            "N +",
            font_size=12,
            on_click=lambda: self._change_board_size(1),
        )
        button_y = SIDE_PANEL.bottom - 44
        button_w = 118
        gap = 10
        self.reset_button = Button(
            pygame.Rect(SIDE_PANEL.left + 14, button_y, button_w, 30),
            "RESET",
            font_size=12,
            on_click=self._reset,
        )
        self.undo_button = Button(
            pygame.Rect(SIDE_PANEL.left + 14 + button_w + gap, button_y, button_w, 30),
            "UNDO",
            font_size=12,
            on_click=self._undo,
        )
        self.compare_button = Button(
            pygame.Rect(SIDE_PANEL.left + 14 + (button_w + gap) * 2, button_y, button_w, 30),
            "COMPARE",
            font_size=11,
            on_click=self._run_experiment,
        )
        self._reset()

    def on_enter(self, **kwargs):
        self._reset()
        self.game_state.kit_index = 4

    def handle_event(self, event):
        for button in (
            self.back_button,
            self.size_down_button,
            self.size_up_button,
            self.reset_button,
            self.undo_button,
            self.compare_button,
        ):
            button.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self._change_board_size(-1)
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self._change_board_size(1)
            elif event.key == pygame.K_r:
                self._reset()
            elif event.key == pygame.K_u:
                self._undo()
            elif event.key == pygame.K_ESCAPE:
                self._go_to_level_select()

        if event.type == pygame.MOUSEWHEEL and TRACE_RECT.collidepoint(pygame.mouse.get_pos()):
            max_scroll = max(0, len(self.search_trace) - self._visible_trace_rows())
            self.trace_scroll = max(0, min(max_scroll, self.trace_scroll - event.y))

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        mouse_x, mouse_y = event.pos
        for index in range(len(ALGORITHMS)):
            if self._algo_button_rect(index).collidepoint(mouse_x, mouse_y):
                self.algo_index = index
                self.search_trace = []
                self.trace_scroll = 0
                self.experiment_results = {}
                self.nodes = 0
                self.best_score = None
                self.status = f"Đã chọn {ALGORITHMS[index]['name']}. Lượt của bạn."
                return

        if self.game_over or self.turn != HUMAN:
            return

        self._update_board_geometry()
        if not self.board_rect.collidepoint(mouse_x, mouse_y):
            return

        col = (mouse_x - self.board_rect.left) // self.cell_size
        row = (mouse_y - self.board_rect.top) // self.cell_size
        if not (0 <= row < self.board_n and 0 <= col < self.board_n):
            return
        if self.board[row][col] != EMPTY:
            return

        self.board[row][col] = HUMAN
        self.history.append((row, col, HUMAN))
        self.ai_move = None
        self.search_trace = []
        self.best_score = None
        self._pulse_actor("right")

        if check_win(self.board, HUMAN):
            self.winner = HUMAN
            self.game_over = True
            self.status = "Bạn thắng!"
        elif is_full(self.board):
            self.game_over = True
            self.status = "Hòa!"
        else:
            self.turn = AI
            self.status = "AI đang duyệt các node con..."
            self._ai_play()

    def update(self, dt):
        self.actor_anim_time += dt
        if self.actor_walk_timer > 0:
            self.actor_walk_timer = max(0.0, self.actor_walk_timer - dt)

    def draw(self, surface):
        draw_stadium_background(surface)
        draw_text(
            surface,
            "CARO ĐỐI KHÁNG",
            (C.SCREEN_W // 2, 12),
            size=26,
            color=C.COL_GOLD_BRIGHT,
            align="center",
        )
        draw_text(
            surface,
            f"Bàn cờ {self.board_n} × {self.board_n}  •  {self.current_win_length} quân liên tiếp thắng",
            (C.SCREEN_W // 2, 44),
            size=13,
            color=C.COL_CREAM_TEXT,
            align="center",
            shadow=False,
        )

        self.back_button.draw(surface)
        self._draw_algorithm_tabs(surface)
        self._draw_board_panel(surface)
        self._draw_side_panel(surface)
        draw_outer_frame(surface)

    @property
    def current_win_length(self):
        return min(DEFAULT_WIN_LENGTH, self.board_n)

    def _algo_button_rect(self, index):
        width = 205
        gap = 12
        start_x = (C.SCREEN_W - (width * 3 + gap * 2)) // 2
        return pygame.Rect(start_x + index * (width + gap), 70, width, 30)

    def _draw_algorithm_tabs(self, surface):
        for index, algorithm in enumerate(ALGORITHMS):
            rect = self._algo_button_rect(index)
            selected = index == self.algo_index
            base = (102, 68, 34) if selected else (64, 44, 30)
            border = C.COL_GOLD_BRIGHT if selected else C.COL_WOOD_DARK
            pygame.draw.rect(surface, base, rect, border_radius=7)
            pygame.draw.rect(surface, border, rect, 2, border_radius=7)
            draw_text(
                surface,
                algorithm["name"],
                rect.center,
                size=13,
                color=C.COL_GOLD_BRIGHT if selected else C.COL_CREAM_TEXT,
                align="center",
                shadow=False,
            )

    def _update_board_geometry(self):
        inner = pygame.Rect(
            BOARD_PANEL.left + 16,
            BOARD_PANEL.top + 42,
            BOARD_PANEL.width - 32,
            BOARD_PANEL.height - 58,
        )
        self.cell_size = max(22, min(92, inner.width // self.board_n, inner.height // self.board_n))
        board_width = self.cell_size * self.board_n
        board_height = self.cell_size * self.board_n
        self.board_rect = pygame.Rect(
            inner.centerx - board_width // 2,
            inner.centery - board_height // 2,
            board_width,
            board_height,
        )

    def _draw_board_panel(self, surface):
        draw_wood_panel(surface, BOARD_PANEL, border=4, corner=9, fill=(38, 30, 23))
        draw_text(
            surface,
            f"BÀN CỜ N × N   |   N = {self.board_n}",
            (BOARD_PANEL.centerx, BOARD_PANEL.top + 10),
            size=13,
            color=C.COL_GOLD_BRIGHT,
            align="center",
            shadow=False,
        )
        self._update_board_geometry()
        self._draw_board(surface)

    def _draw_board(self, surface):
        mouse = pygame.mouse.get_pos()
        hover = None
        if self.board_rect.collidepoint(mouse) and not self.game_over and self.turn == HUMAN:
            col = (mouse[0] - self.board_rect.left) // self.cell_size
            row = (mouse[1] - self.board_rect.top) // self.cell_size
            if 0 <= row < self.board_n and 0 <= col < self.board_n and self.board[row][col] == EMPTY:
                hover = (row, col)

        grid_color = (214, 205, 177)
        tile_size = (self.cell_size, self.cell_size)
        grass_tile = AssetManager.instance().get_terrain_tile("grass", size=tile_size)
        path_tile = AssetManager.instance().get_terrain_tile("path", size=tile_size)
        hover_overlay = pygame.Surface(tile_size, pygame.SRCALPHA)
        hover_overlay.fill((245, 214, 92, 78))
        for row in range(self.board_n):
            for col in range(self.board_n):
                rect = pygame.Rect(
                    self.board_rect.left + col * self.cell_size,
                    self.board_rect.top + row * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                tile = grass_tile if (row + col) % 2 == 0 else path_tile
                surface.blit(tile, rect.topleft)
                if hover == (row, col):
                    surface.blit(hover_overlay, rect.topleft)
                pygame.draw.rect(surface, grid_color, rect, max(1, self.cell_size // 34))

                inset = max(5, self.cell_size // 5)
                stroke = max(3, self.cell_size // 13)
                if self.board[row][col] == HUMAN:
                    pygame.draw.line(
                        surface,
                        C.COL_GOLD_BRIGHT,
                        (rect.left + inset, rect.top + inset),
                        (rect.right - inset, rect.bottom - inset),
                        stroke,
                    )
                    pygame.draw.line(
                        surface,
                        C.COL_GOLD_BRIGHT,
                        (rect.right - inset, rect.top + inset),
                        (rect.left + inset, rect.bottom - inset),
                        stroke,
                    )
                elif self.board[row][col] == AI:
                    pygame.draw.circle(
                        surface,
                        C.COL_HIGHLIGHT_PURPLE,
                        rect.center,
                        max(5, self.cell_size // 3),
                        stroke,
                    )

                if self.ai_move == (row, col):
                    pygame.draw.rect(
                        surface,
                        C.COL_HIGHLIGHT_PURPLE,
                        rect.inflate(-4, -4),
                        max(2, self.cell_size // 24),
                        border_radius=3,
                    )

    def _draw_side_panel(self, surface):
        draw_wood_panel(surface, SIDE_PANEL, border=4, corner=9, fill=(48, 31, 24))
        self.size_down_button.enabled = self.board_n > MIN_BOARD_SIZE
        self.size_up_button.enabled = self.board_n < MAX_BOARD_SIZE
        self.size_down_button.draw(surface)
        self.size_up_button.draw(surface)
        self.reset_button.draw(surface)
        self.undo_button.draw(surface)
        self.compare_button.draw(surface)

        algorithm = ALGORITHMS[self.algo_index]
        draw_text(
            surface,
            f"N = {self.board_n}",
            (SIDE_PANEL.centerx, SIDE_PANEL.top + 16),
            size=17,
            color=C.COL_GOLD_BRIGHT,
            align="center",
            shadow=False,
        )
        draw_text(
            surface,
            algorithm["name"],
            (SIDE_PANEL.centerx, SIDE_PANEL.top + 50),
            size=17,
            color=C.COL_GOLD_BRIGHT,
            align="center",
        )
        draw_text(
            surface,
            algorithm["desc"],
            (SIDE_PANEL.centerx, SIDE_PANEL.top + 77),
            size=10,
            color=C.COL_CREAM_TEXT,
            align="center",
            max_width=SIDE_PANEL.width - 32,
            shadow=False,
        )

        depth = self._effective_depth()
        draw_text(
            surface,
            f"Độ sâu thực tế: {depth}    Nodes AI: {self.nodes}",
            (SIDE_PANEL.left + 14, SIDE_PANEL.top + 116),
            size=11,
            color=C.COL_CREAM_TEXT,
            max_width=SIDE_PANEL.width - 112,
            shadow=False,
        )
        score_text = "-" if self.best_score is None else self._format_score(self.best_score)
        move_text = "-" if self.ai_move is None else self._format_move(self.ai_move)
        draw_text(
            surface,
            f"Nước chọn: {move_text}    Điểm: {score_text}",
            (SIDE_PANEL.left + 14, SIDE_PANEL.top + 137),
            size=11,
            color=C.COL_GOLD_BRIGHT,
            max_width=SIDE_PANEL.width - 112,
            shadow=False,
        )
        draw_text(
            surface,
            self.status,
            (SIDE_PANEL.left + 14, SIDE_PANEL.top + 158),
            size=10,
            color=C.COL_CREAM_TEXT,
            max_width=SIDE_PANEL.width - 112,
            shadow=False,
        )
        self._draw_actor(surface)

        self._draw_trace_panel(surface)
        self._draw_experiment_summary(surface)

    def _visible_trace_rows(self):
        return 5

    def _draw_trace_panel(self, surface):
        pygame.draw.rect(surface, (232, 224, 198), TRACE_RECT, border_radius=5)
        pygame.draw.rect(surface, C.COL_WOOD_DARK, TRACE_RECT, 2, border_radius=5)
        draw_text(
            surface,
            "TIẾN TRÌNH GIẢI AI",
            (TRACE_RECT.centerx, TRACE_RECT.top + 6),
            size=12,
            color=C.COL_BLACK,
            align="center",
            shadow=False,
        )

        header_y = TRACE_RECT.top + 28
        columns = (
            (TRACE_RECT.left + 8, "#"),
            (TRACE_RECT.left + 42, "Node con"),
            (TRACE_RECT.left + 150, "Điểm"),
            (TRACE_RECT.left + 225, "Nodes"),
            (TRACE_RECT.left + 310, "Kết quả"),
        )
        pygame.draw.line(
            surface,
            C.COL_WOOD_DARK,
            (TRACE_RECT.left + 5, header_y + 17),
            (TRACE_RECT.right - 5, header_y + 17),
            1,
        )
        for x, label in columns:
            draw_text(surface, label, (x, header_y), size=9, color=C.COL_BLACK, shadow=False)

        if not self.search_trace:
            draw_text(
                surface,
                "Chưa có node được xét. Hãy đánh một nước để AI bắt đầu.",
                (TRACE_RECT.centerx, TRACE_RECT.top + 78),
                size=9,
                color=(75, 65, 50),
                align="center",
                max_width=TRACE_RECT.width - 24,
                shadow=False,
            )
            return

        visible_count = self._visible_trace_rows()
        max_scroll = max(0, len(self.search_trace) - visible_count)
        self.trace_scroll = max(0, min(self.trace_scroll, max_scroll))
        rows = self.search_trace[self.trace_scroll:self.trace_scroll + visible_count]
        row_y = header_y + 23
        for index, item in enumerate(rows):
            y = row_y + index * 21
            if item["selected"]:
                pygame.draw.rect(
                    surface,
                    (248, 221, 125),
                    pygame.Rect(TRACE_RECT.left + 4, y - 2, TRACE_RECT.width - 8, 20),
                    border_radius=3,
                )
            draw_text(surface, str(item["order"]), (TRACE_RECT.left + 10, y), size=9, color=C.COL_BLACK, shadow=False)
            draw_text(surface, self._format_move(item["move"]), (TRACE_RECT.left + 42, y), size=9, color=C.COL_BLACK, shadow=False)
            draw_text(surface, self._format_score(item["score"]), (TRACE_RECT.left + 150, y), size=9, color=C.COL_BLACK, shadow=False)
            draw_text(surface, str(item["nodes"]), (TRACE_RECT.left + 225, y), size=9, color=C.COL_BLACK, shadow=False)
            result = "CHỌN" if item["selected"] else "LOẠI"
            draw_text(
                surface,
                result,
                (TRACE_RECT.left + 310, y),
                size=9,
                color=(35, 105, 45) if item["selected"] else (125, 55, 45),
                shadow=False,
            )

        if len(self.search_trace) > visible_count:
            draw_text(
                surface,
                f"Dòng {self.trace_scroll + 1}-{min(len(self.search_trace), self.trace_scroll + visible_count)}/{len(self.search_trace)} • cuộn chuột",
                (TRACE_RECT.right - 8, TRACE_RECT.bottom - 15),
                size=8,
                color=(75, 65, 50),
                align="right",
                shadow=False,
            )

    def _draw_experiment_summary(self, surface):
        if not self.experiment_results:
            return
        y = TRACE_RECT.bottom + 4
        pieces = []
        for name, result in self.experiment_results.items():
            pieces.append(f"{name}: {self._format_move(result['move'])}/{result['nodes']}")
        draw_text(
            surface,
            "So sánh: " + " | ".join(pieces),
            (SIDE_PANEL.left + 14, y),
            size=8,
            color=C.COL_CREAM_TEXT,
            max_width=SIDE_PANEL.width - 28,
            shadow=False,
        )

    def _effective_depth(self):
        base_depth = ALGORITHMS[self.algo_index]["depth"]
        empty_count = sum(value == EMPTY for row in self.board for value in row) if self.board else self.board_n ** 2
        if self.board_n <= 5:
            depth = base_depth
        elif self.board_n <= 7:
            depth = min(base_depth, 3)
        else:
            depth = min(base_depth, 2)
        return max(1, min(depth, empty_count))

    def _ai_play(self):
        algorithm = ALGORITHMS[self.algo_index]
        move, nodes, trace, best_score = best_move_ai(
            self.board,
            algorithm["name"],
            self._effective_depth(),
        )
        self.nodes = nodes
        self.search_trace = trace
        self.trace_scroll = max(0, len(trace) - self._visible_trace_rows())
        self.best_score = best_score

        if move is None:
            self.game_over = True
            self.status = "Không còn nước đi. Hòa!"
            return

        row, col = move
        self.board[row][col] = AI
        self.ai_move = move
        self.history.append((row, col, AI))
        self._pulse_actor("left")

        if check_win(self.board, AI):
            self.winner = AI
            self.game_over = True
            self.status = f"AI ({algorithm['name']}) thắng!"
        elif is_full(self.board):
            self.game_over = True
            self.status = "Hòa!"
        else:
            self.turn = HUMAN
            self.status = f"AI đã chọn {self._format_move(move)}. Lượt của bạn."

    def _change_board_size(self, delta):
        new_size = max(MIN_BOARD_SIZE, min(MAX_BOARD_SIZE, self.board_n + delta))
        if new_size == self.board_n:
            return
        self.board_n = new_size
        self._reset()
        self.status = (
            f"Đã đổi thành bàn cờ {self.board_n} × {self.board_n}. "
            f"Cần {self.current_win_length} quân liên tiếp để thắng."
        )

    def _reset(self):
        self.board = [[EMPTY for _ in range(self.board_n)] for _ in range(self.board_n)]
        self.turn = HUMAN
        self.game_over = False
        self.winner = None
        self.status = "Lượt của bạn (X). Click vào ô trống."
        self.nodes = 0
        self.ai_move = None
        self.best_score = None
        self.history = []
        self.search_trace = []
        self.trace_scroll = 0
        self.experiment_results = {}
        self.actor_walk_timer = 0.0
        self.actor_facing = "down"

    def _run_experiment(self):
        if self.board is None or self.game_over:
            return
        board_copy = [row[:] for row in self.board]
        self.experiment_results = {}
        for algorithm in ALGORITHMS:
            test_board = [row[:] for row in board_copy]
            depth = self._depth_for_algorithm(algorithm)
            move, nodes, _, score = best_move_ai(test_board, algorithm["name"], depth)
            self.experiment_results[algorithm["name"]] = {
                "move": move,
                "nodes": nodes,
                "score": score,
            }
        self.status = "Đã so sánh cùng một trạng thái bàn cờ bằng ba thuật toán."

        self._pulse_actor("up")

    def _depth_for_algorithm(self, algorithm):
        base_depth = algorithm["depth"]
        if self.board_n <= 5:
            return base_depth
        if self.board_n <= 7:
            return min(base_depth, 3)
        return min(base_depth, 2)

    def _undo(self):
        if not self.history:
            self.status = "Chưa có nước đi để hoàn tác."
            return

        remove_count = 2 if len(self.history) >= 2 and self.history[-1][2] == AI else 1
        for _ in range(remove_count):
            if not self.history:
                break
            row, col, _ = self.history.pop()
            self.board[row][col] = EMPTY

        self.turn = HUMAN
        self.game_over = False
        self.winner = None
        self.ai_move = None
        self.nodes = 0
        self.best_score = None
        self.search_trace = []
        self.trace_scroll = 0
        self.experiment_results = {}
        self.status = "Đã hoàn tác. Lượt của bạn."

        self._pulse_actor("down")

    def _pulse_actor(self, facing):
        self.actor_facing = facing
        self.actor_walk_timer = 0.42

    def _draw_actor(self, surface):
        actor_rect = pygame.Rect(SIDE_PANEL.right - 78, SIDE_PANEL.top + 108, 64, 88)
        Player.draw_in_rect(
            surface,
            actor_rect,
            kit_index=max(0, min(self.game_state.kit_index, len(C.KITS) - 1)),
            state="walk" if self.actor_walk_timer > 0 else "idle",
            facing=self.actor_facing,
            anim_time=self.actor_anim_time,
        )

    @staticmethod
    def _format_move(move):
        if move is None:
            return "-"
        row, col = move
        return f"({row + 1},{col + 1})"

    @staticmethod
    def _format_score(score):
        if isinstance(score, float) and not score.is_integer():
            return f"{score:.1f}"
        return str(int(score))

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)
