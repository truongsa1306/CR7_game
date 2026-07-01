"""
scenes/caro_scene.py
====================
Adversarial caro level for CR7 Game. The player plays ✕ against an AI
using Minimax / Alpha-Beta / Expectimax on a 5×5 board. This scene is
only launched from level select as the dedicated caro demo.
"""

import pygame
import random

import config as C
from scenes.base_scene import BaseScene
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_wood_panel, draw_stadium_background

N = 5
WIN = 4
EMPTY = 0
HUMAN = 1
AI = 2
CELL = 92
BOARD_X = 58
BOARD_Y = 120

ALGORITHMS = [
    {"name": "Minimax", "depth": 3, "desc": "Duyệt cây trò chơi, giả sử đối thủ luôn đánh tối ưu."},
    {"name": "Alpha-Beta", "depth": 4, "desc": "Cắt tỉa những nhánh không cần thiết, nhanh hơn mà vẫn chính xác."},
    {"name": "Expectimax", "depth": 3, "desc": "Tính toán với xác suất cho quân địch, phù hợp khi đối thủ không hoàn hảo."},
]


def check_win(board, player):
    for r in range(N):
        for c in range(N):
            for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                line = [(r + k * dr, c + k * dc) for k in range(WIN)]
                if all(0 <= rr < N and 0 <= cc < N and board[rr][cc] == player for rr, cc in line):
                    return True
    return False


def is_full(board):
    return all(board[r][c] != EMPTY for r in range(N) for c in range(N))


def score_line(board, player):
    opp = 3 - player
    score = 0
    for r in range(N):
        for c in range(N):
            for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                line = [(r + k * dr, c + k * dc) for k in range(WIN)]
                if not all(0 <= rr < N and 0 <= cc < N for rr, cc in line):
                    continue
                values = [board[rr][cc] for rr, cc in line]
                pcount = values.count(player)
                ocount = values.count(opp)
                if ocount == 0:
                    if pcount == 4:
                        score += 1000
                    elif pcount == 3:
                        score += 50
                    elif pcount == 2:
                        score += 5
                elif pcount == 0:
                    if ocount == 4:
                        score -= 1000
                    elif ocount == 3:
                        score -= 60
                    elif ocount == 2:
                        score -= 6
    return score


def evaluate(board):
    if check_win(board, AI):
        return 9000
    if check_win(board, HUMAN):
        return -9000
    return score_line(board, AI)


def get_moves(board):
    moves = [(r, c) for r in range(N) for c in range(N) if board[r][c] == EMPTY]
    moves.sort(key=lambda pos: abs(pos[0] - N // 2) + abs(pos[1] - N // 2))
    return moves[:12]


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
        for r, c in moves:
            board[r][c] = AI
            best = max(best, minimax(board, depth - 1, False, nodes))
            board[r][c] = EMPTY
        return best
    best = 99999
    for r, c in moves:
        board[r][c] = HUMAN
        best = min(best, minimax(board, depth - 1, True, nodes))
        board[r][c] = EMPTY
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
        for r, c in moves:
            board[r][c] = AI
            best = max(best, alphabeta(board, depth - 1, alpha, beta, False, nodes))
            board[r][c] = EMPTY
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    best = 99999
    for r, c in moves:
        board[r][c] = HUMAN
        best = min(best, alphabeta(board, depth - 1, alpha, beta, True, nodes))
        board[r][c] = EMPTY
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

    # MAX NODE (AI)
    if is_max:
        best = -99999
        for r, c in moves:
            board[r][c] = AI
            best = max(best, expectimax(board, depth - 1, False, nodes))
            board[r][c] = EMPTY
        return best

    # CHANCE NODE (Human)
    total = 0
    for r, c in moves:
        board[r][c] = HUMAN
        total += expectimax(board, depth - 1, True, nodes)
        board[r][c] = EMPTY

    return total / len(moves) if moves else 0


def best_move_ai(board, algo_name, depth):
    moves = get_moves(board)
    nodes = [0]
    best_value = -99999
    best_move = None
    for r, c in moves:
        board[r][c] = AI
        if algo_name == "Minimax":
            value = minimax(board, depth - 1, False, nodes)
        elif algo_name == "Alpha-Beta":
            value = alphabeta(board, depth - 1, -99999, 99999, False, nodes)
        else:
            value = expectimax(board, depth - 1, False, nodes)
        board[r][c] = EMPTY
        if value > best_value:
            best_value = value
            best_move = (r, c)
    return best_move, nodes[0]


class CaroScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.algo_index = 1
        self.board = None
        self.turn = HUMAN
        self.game_over = False
        self.winner = None
        self.status = "Lượt của bạn (✕). Click vào ô trống!"
        self.nodes = 0
        self.ai_move = None
        self.history = []
        self.experiment_results = {}
        self.back_button = Button(pygame.Rect(20, 20, 100, 30), "BACK", font_size=13, on_click=self._go_to_level_select)
        self.reset_button = Button(pygame.Rect(560, 490, 120, 32), "RESET", font_size=13, on_click=self._reset)
        self.undo_button = Button(pygame.Rect(700, 490, 120, 32), "UNDO", font_size=13, on_click=self._undo)
        self.compare_button = Button(pygame.Rect(840, 490, 120, 32), "COMPARE", font_size=13, on_click=self._run_experiment)
        self._reset()

    def on_enter(self, **kwargs):
        self._reset()
        self.game_state.kit_index = 4

    def handle_event(self, event):
        self.back_button.handle_event(event)
        self.reset_button.handle_event(event)
        self.undo_button.handle_event(event)
        self.compare_button.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for idx in range(len(ALGORITHMS)):
                btn = self._algo_button_rect(idx)
                if btn.collidepoint(mx, my):
                    self.algo_index = idx
                    self._reset()
                    return
            if self.game_over:
                return
            if BOARD_X <= mx < BOARD_X + N * CELL and BOARD_Y <= my < BOARD_Y + N * CELL:
                col = (mx - BOARD_X) // CELL
                row = (my - BOARD_Y) // CELL
                if self.board[row][col] == EMPTY and self.turn == HUMAN:
                    self.board[row][col] = HUMAN
                    self.history.append((row, col, HUMAN))
                    self.ai_move = None
                    if check_win(self.board, HUMAN):
                        self.winner = HUMAN
                        self.game_over = True
                        self.status = "Bạn thắng! 🎉"
                    elif is_full(self.board):
                        self.game_over = True
                        self.status = "Hòa!"
                    else:
                        self.turn = AI
                        self.status = "AI đang suy nghĩ..."
                        self._ai_play()

    def update(self, dt):
        pass

    def draw(self, surface):
        draw_stadium_background(surface)
        draw_text(surface, "CARO DOI KHANG", (C.SCREEN_W // 2, 24), size=28, color=C.COL_GOLD_BRIGHT, align="center")
        draw_text(surface, "4 liên tiếp thắng. Chọn ô, đối đầu AI!", (C.SCREEN_W // 2, 56), size=16, color=C.COL_CREAM_TEXT, align="center")

        self.back_button.draw(surface)
        self.reset_button.draw(surface)
        self.undo_button.draw(surface)
        self.compare_button.draw(surface)

        self._draw_algorithm_tabs(surface)
        draw_wood_panel(surface, pygame.Rect(40, 110, N * CELL + 16, N * CELL + 16), border=3, corner=8, fill=(40, 34, 24))
        self._draw_board(surface)
        self._draw_info_panel(surface)
        self._draw_dialogue_panel(surface)

    def _algo_button_rect(self, index):
        return pygame.Rect(90 + index * 220, 74, 200, 32)

    def _draw_algorithm_tabs(self, surface):
        for idx, algo in enumerate(ALGORITHMS):
            rect = self._algo_button_rect(idx)
            selected = idx == self.algo_index
            base = (90, 60, 34) if selected else (64, 44, 30)
            border = C.COL_GOLD if selected else C.COL_WOOD_DARK
            pygame.draw.rect(surface, base, rect, border_radius=8)
            pygame.draw.rect(surface, border, rect, 2, border_radius=8)
            draw_text(surface, algo["name"], rect.center, size=14,
                      color=C.COL_GOLD_BRIGHT if selected else C.COL_CREAM_TEXT,
                      align="center")

    def _draw_board(self, surface):
        for r in range(N + 1):
            y = BOARD_Y + r * CELL
            pygame.draw.line(surface, C.COL_CREAM_TEXT, (BOARD_X, y), (BOARD_X + N * CELL, y), 2)
        for c in range(N + 1):
            x = BOARD_X + c * CELL
            pygame.draw.line(surface, C.COL_CREAM_TEXT, (x, BOARD_Y), (x, BOARD_Y + N * CELL), 2)

        mouse = pygame.mouse.get_pos()
        hover = None
        if BOARD_X <= mouse[0] < BOARD_X + N * CELL and BOARD_Y <= mouse[1] < BOARD_Y + N * CELL and not self.game_over:
            col = (mouse[0] - BOARD_X) // CELL
            row = (mouse[1] - BOARD_Y) // CELL
            if self.board[row][col] == EMPTY and self.turn == HUMAN:
                hover = (row, col)

        for r in range(N):
            for c in range(N):
                cell_rect = pygame.Rect(BOARD_X + c * CELL + 4, BOARD_Y + r * CELL + 4, CELL - 8, CELL - 8)
                if hover == (r, c):
                    pygame.draw.rect(surface, (45, 80, 48), cell_rect)
                else:
                    pygame.draw.rect(surface, (32, 24, 18), cell_rect)
                if self.board[r][c] == HUMAN:
                    pygame.draw.line(surface, C.COL_GOLD_BRIGHT,
                                     (cell_rect.left + 18, cell_rect.top + 18),
                                     (cell_rect.right - 18, cell_rect.bottom - 18), 6)
                    pygame.draw.line(surface, C.COL_GOLD_BRIGHT,
                                     (cell_rect.right - 18, cell_rect.top + 18),
                                     (cell_rect.left + 18, cell_rect.bottom - 18), 6)
                elif self.board[r][c] == AI:
                    pygame.draw.circle(surface, C.COL_HIGHLIGHT_PURPLE, cell_rect.center, 24, 6)
                if self.ai_move == (r, c) and self.turn == HUMAN:
                    pygame.draw.rect(surface, (120, 120, 255), cell_rect, 4)

    def _draw_info_panel(self, surface):
        panel = pygame.Rect(560, 120, 380, 340)
        draw_wood_panel(surface, panel, border=4, corner=10, fill=(42, 30, 24))
        algo = ALGORITHMS[self.algo_index]
        draw_text(surface, algo["name"], (panel.centerx, panel.top + 18), size=18, color=C.COL_GOLD_BRIGHT, align="center")
        draw_text(surface, algo["desc"], (panel.centerx, panel.top + 50), size=13, color=C.COL_CREAM_TEXT, align="center")
        draw_text(surface, f"Độ sâu: {algo['depth']}", (panel.left + 16, panel.top + 90), size=13, color=C.COL_CREAM_TEXT)
        draw_text(surface, f"Nodes AI: {self.nodes}", (panel.left + 16, panel.top + 118), size=13, color=C.COL_CREAM_TEXT)
        draw_text(surface, self.status, (panel.left + 16, panel.top + 154), size=14, color=C.COL_CREAM_TEXT, align="left", max_width=panel.width - 32)
        draw_text(surface, "Hướng dẫn:", (panel.left + 16, panel.top + 204), size=13, color=C.COL_GOLD_BRIGHT)
        draw_text(surface, "- Click ô trống để đánh.", (panel.left + 16, panel.top + 228), size=12, color=C.COL_CREAM_TEXT)
        draw_text(surface, "- AI sẽ đánh ngay sau bạn.", (panel.left + 16, panel.top + 250), size=12, color=C.COL_CREAM_TEXT)
        draw_text(surface, "- 4 quân thẳng hàng thắng.", (panel.left + 16, panel.top + 272), size=12, color=C.COL_CREAM_TEXT)

        if self.experiment_results:
            y = panel.top + 300
            draw_text(surface, "Thực nghiệm:", (panel.left + 16, y), size=13, color=C.COL_GOLD_BRIGHT)
            for idx, (algo_name, result) in enumerate(self.experiment_results.items()):
                move_text = "-" if result["move"] is None else f"{result['move']}"
                draw_text(surface, f"{algo_name}: {move_text} | nodes {result['nodes']}",
                          (panel.left + 16, y + 18 + idx * 16), size=11,
                          color=C.COL_CREAM_TEXT, max_width=panel.width - 32)

        if self.game_over:
            outcome = "BẠN THẮNG!" if self.winner == HUMAN else "AI THẮNG!" if self.winner == AI else "HÒA!"
            draw_text(surface, outcome, (panel.centerx, panel.bottom - 40), size=18, color=C.COL_HIGHLIGHT_PURPLE, align="center")

    def _draw_dialogue_panel(self, surface):
        dialog = pygame.Rect(40, 460, 500, 90)
        draw_wood_panel(surface, dialog, border=3, corner=8, fill=(30, 24, 18))
        draw_text(surface, "TIẾN TRÌNH GIẢI", (dialog.left + 14, dialog.top + 10), size=15, color=C.COL_GOLD_BRIGHT, align="topleft")
        draw_text(surface, f"Thuật toán: {ALGORITHMS[self.algo_index]['name']}",
                  (dialog.left + 14, dialog.top + 34), size=13, color=C.COL_CREAM_TEXT, align="topleft")
        draw_text(surface, f"Nodes AI: {self.nodes}",
                  (dialog.left + 14, dialog.top + 54), size=13, color=C.COL_CREAM_TEXT, align="topleft")
        if self.experiment_results:
            comparison = " | ".join(
                f"{name}:{result['move']}" for name, result in self.experiment_results.items()
            )
            draw_text(surface, comparison,
                      (dialog.left + 14, dialog.top + 72), size=11, color=C.COL_CREAM_TEXT, align="topleft", max_width=470)
        else:
            move_label = f"Nước đi AI: {self.ai_move}" if self.ai_move is not None else "Nước đi AI: Chưa có"
            draw_text(surface, move_label,
                      (dialog.left + 14, dialog.top + 72), size=13, color=C.COL_CREAM_TEXT, align="topleft")

    def _ai_play(self):
        algo = ALGORITHMS[self.algo_index]
        move, nodes = best_move_ai(self.board, algo["name"], algo["depth"])
        self.nodes = nodes
        if move is not None:
            r, c = move
            self.board[r][c] = AI
            self.ai_move = (r, c)
            self.history.append((r, c, AI))
            if check_win(self.board, AI):
                self.winner = AI
                self.game_over = True
                self.status = f"AI ({algo['name']}) thắng!"
            elif is_full(self.board):
                self.game_over = True
                self.status = "Hòa!"
            else:
                self.turn = HUMAN
                self.status = "Lượt của bạn (✕)."
        else:
            self.game_over = True
            self.status = "Không còn nước đi. Hòa!"

    def _reset(self):
        self.board = [[EMPTY] * N for _ in range(N)]
        self.turn = HUMAN
        self.game_over = False
        self.winner = None
        self.status = "Lượt của bạn (✕). Click vào ô trống!"
        self.nodes = 0
        self.ai_move = None
        self.history = []
        self.experiment_results = {}

    def _run_experiment(self):
        if self.board is None:
            return
        board_copy = [row[:] for row in self.board]
        self.experiment_results = {}
        for algo in ALGORITHMS:
            test_board = [row[:] for row in board_copy]
            move, nodes = best_move_ai(test_board, algo["name"], algo["depth"])
            self.experiment_results[algo["name"]] = {
                "move": move,
                "nodes": nodes,
            }
        self.status = "Đã chạy thực nghiệm so sánh thuật toán"

    def _undo(self):
        if len(self.history) >= 2 and not self.game_over:
            for _ in range(2):
                r, c, _ = self.history.pop()
                self.board[r][c] = EMPTY
            self.turn = HUMAN
            self.status = "Hoàn tác. Lượt bạn."

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)