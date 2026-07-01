"""
scenes/gameplay_scene.py
========================
Interactive grid/tutorial scene from the spec. It renders the stadium UI
layout at 1024x576, visualizes the selected search algorithm step by step,
and transitions to LevelUp, GameOver, or Victory scenes.
"""
import random
from collections import deque

import pygame

import config as C
from effects.fire_anim import FireAnimator
from entities.grid_cell import ORTHOGONAL_DIRECTIONS, GridModel
from entities.player import Player
from scenes.base_scene import BaseScene
from systems.algorithms.blind_search import bfs_steps, dfs_steps, ids_steps
from systems.algorithms.hill_climbing import (
    simple_hill_climbing_steps,
    simulated_annealing_steps,
    steepest_ascent_hill_climbing_steps,
    stochastic_hill_climbing_steps,
)
from systems.algorithms.informed_search import astar_steps, greedy_steps, ucs_steps
from systems.asset_manager import AssetManager, placeholder_trophy
from systems.audio_manager import AudioManager
from ui.button import Button, ToggleGroup
from ui.dialogue_box import DialogueBox
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_stadium_background, draw_wood_panel


def _factory_with_health(fn, *args, **kwargs):
    def _wrapped(grid, start=None, health=None):
        return fn(grid, start=start, health=health, *args, **kwargs)
    return _wrapped


def and_or_search_steps(grid, start=None, health=None):
    if start is None:
        start = grid.start

    right_branch = [(1, 5), (2, 5), (2, 4), (3, 4), (4, 4), (4, 3)]
    goal_branch = [(5, 3), (6, 3), (7, 3), (7, 2), (8, 2), (8, 1), (9, 1), (10, 1), (10, 0), (11, 0)]
    choice_up = (4, 2)
    choice_right = (5, 3)
    choice_down = (4, 4)
    branch_choices = {choice_up, choice_right, choice_down}

    # 1) Darken the screen first.
    yield {
        "current": start,
        "frontier": [],
        "visited": set(),
        "neighbor_scores": {},
        "chosen": None,
        "temperature": None,
        "dark": True,
    }

    # 2) Brighten the right branch gradually while approaching the decision node.
    for i in range(1, len(right_branch) + 1):
        status = "Xét 3 nhánh: U R D" if i == len(right_branch) else "Xét nhánh R..."
        step = {
            "current": start,
            "frontier": [],
            "visited": set(),
            "neighbor_scores": {},
            "chosen": None,
            "temperature": None,
            "dark": True,
            "highlight_branch": right_branch[:i],
            "status": status,
        }
        if i == len(right_branch):
            step["branch_choices"] = branch_choices
        yield step

    # 3) Select the right-hand branch and highlight the chosen option.
    yield {
        "current": start,
        "frontier": [],
        "visited": set(),
        "neighbor_scores": {},
        "chosen": None,
        "temperature": None,
        "dark": True,
        "highlight_branch": right_branch,
        "branch_choices": branch_choices,
        "selected_choice": choice_right,
        "status": "Nhánh R được chọn. Tím ô phải chứ không phải ô hiện tại.",
    }

    # 4) Light the OR branch cell by cell using A* style exploration.
    or_path = []
    for idx, pos in enumerate(goal_branch, 1):
        or_path.append(pos)
        yield {
            "current": start,
            "frontier": [],
            "visited": set(),
            "neighbor_scores": {},
            "chosen": None,
            "temperature": None,
            "dark": True,
            "highlight_branch": right_branch,
            "branch_choices": branch_choices,
            "selected_choice": choice_right,
            "or_path": list(or_path),
            "status": f"Giải nhánh OR theo A*... ({idx}/{len(goal_branch)})",
        }

    # 5) After solving R, return to the dark screen with 3 bright options.
    yield {
        "current": start,
        "frontier": [],
        "visited": set(),
        "neighbor_scores": {},
        "chosen": None,
        "temperature": None,
        "dark": True,
        "branch_choices": branch_choices,
        "status": "R đã giải, quay lại giao diện tối và chọn nhánh -4 phía trên.",
    }

    # 6) Try the upper -4 branch and show it as selected.
    yield {
        "current": start,
        "frontier": [],
        "visited": set(),
        "neighbor_scores": {},
        "chosen": None,
        "temperature": None,
        "dark": True,
        "branch_choices": branch_choices,
        "selected_choice": choice_up,
        "status": "Chọn ô U -4 ở trên để thử nhánh tiếp theo.",
    }

    # 7) If that branch fails, go back to the dark screen with all 3 options still lit.
    yield {
        "current": start,
        "frontier": [],
        "visited": set(),
        "neighbor_scores": {},
        "chosen": None,
        "temperature": None,
        "dark": True,
        "branch_choices": branch_choices,
        "status": "Nhánh U -4 bị sai. Quay lại 3 ô sáng và chọn bước khác.",
    }

    # 8) Final move along the OR path.
    yield {
        "current": start,
        "frontier": [],
        "visited": set(),
        "neighbor_scores": {},
        "chosen": None,
        "temperature": None,
        "dark": True,
        "highlight_branch": right_branch,
        "branch_choices": branch_choices,
        "selected_choice": choice_right,
        "or_path": list(or_path),
        "path": [start] + right_branch + goal_branch,
        "status": "Đã chọn nhánh OR. CR7 di chuyển theo giải pháp.",
    }


ALGORITHM_FACTORIES = {
    "BFS": bfs_steps,
    "DFS": dfs_steps,
    "IDS": ids_steps,
    "UCS": ucs_steps,
    "Greedy": greedy_steps,
    "A*": astar_steps,
    "Hill Climbing": simple_hill_climbing_steps,
    "Steepest Ascent HC": steepest_ascent_hill_climbing_steps,
    "Stochastic HC": _factory_with_health(stochastic_hill_climbing_steps, rng=random.Random(17)),
    "Simulated Annealing": _factory_with_health(simulated_annealing_steps, rng=random.Random(23)),
    "AND OR SEARCH": and_or_search_steps,
}

BLIND_SEARCH_ALGORITHMS = {"BFS", "DFS", "IDS"}
INFORMED_SEARCH_ALGORITHMS = {"UCS", "Greedy", "A*"}
TRACE_TABLE_ALGORITHMS = BLIND_SEARCH_ALGORITHMS | INFORMED_SEARCH_ALGORITHMS
HILL_CLIMBING_ALGORITHMS = {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}
EDITABLE_MATRIX_LEVELS = {0, 1, 2}
PROGRESS_HISTORY_LEVELS = {0, 1}


LEVEL_LAYOUTS = {
    0: {
        "start": (0, 2),
        "goal": (8, 0),
        "path": [],
        "danger": [],
        "fire": [],
        "wall": [],
        "fog": False,
    },
    1: {
        "start": (0, 2),
        "goal": (8, 0),
        "path": [(1, 2), (2, 2), (2, 1), (3, 1), (4, 1), (5, 1), (5, 2), (5, 3), (6, 3), (7, 3)],
        "danger": [(6, 1), (7, 1), (8, 1), (6, 4), (7, 4), (8, 3)],
        "fire": [(7, 0), (7, 2), (8, 2)],
        "wall": [(6, 0), (6, 2)],
        "fog": False,
    },
    2: {
        "start": (0, 2),
        "goal": (8, 0),
        "path": [(1, 2), (2, 2), (2, 1), (3, 1), (4, 1), (5, 1), (5, 2), (5, 3), (6, 3), (7, 3)],
        "danger": [(6, 1), (7, 1), (8, 1), (6, 4), (7, 4), (8, 3)],
        "fire": [(7, 0), (7, 2), (8, 2)],
        "wall": [(6, 0), (6, 2)],
        "fog": False,
    },
    3: {
        "start": (0, 5),
        "goal": (11, 0),
        "path": [(1, 5), (2, 5), (2, 4), (3, 4), (4, 4), (4, 3), (5, 3), (6, 3),
                 (7, 3), (7, 2), (8, 2), (8, 1), (9, 1), (10, 1), (10, 0)],
        "danger": [(3, 5), (5, 4), (6, 2), (8, 3), (9, 2), (10, 2), (11, 1)],
        "fire": [(4, 2), (7, 1), (9, 3), (11, 3)],
        "wall": [(1, 3), (3, 3), (5, 2), (6, 1)],
        "fog": False,
    },
}


class GameplayScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.dialogue = DialogueBox(on_skip=self._on_dialogue_advance)
        self.player = Player()
        self.fire = FireAnimator()
        self.grid = None
        self.grid_rect = pygame.Rect(C.GRID_RECT)
        self.cell_size = C.GRID_CELL_SIZE
        self.algorithm_name = "BFS"
        self.generator = None
        self.algorithm_buttons = []
        self.randomize_button = None
        self.matrix_edit_button = None
        self.matrix_edit_mode = False
        self.belief_button = None
        self.and_or_button = None
        self.back_button = None
        self.return_button = None
        self.level4_toggle = None
        self.level4_tab = 0
        self.visited = set()
        self.frontier = set()
        self.final_path = []
        self.follow_path = []
        self.current = None
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.depth_limit = None
        self.restarting = False
        self.algorithm_health = 100
        self.auto_play = True
        self.step_timer = 0.0
        self.finished = False
        self.searching = False
        self.and_or_dark = False
        self.and_or_branch = set()
        self.and_or_goal = None
        self.and_or_path = []
        self.search_trace_rows = []
        self.last_search_step = None
        self.algorithm_history = []
        self.algorithm_history_index = -1
        self.progress_prev_button = None
        self.progress_next_button = None
        self.progress_auto_button = None
        self.hill_trace_rows = []
        self.hill_status_message = ""
        self.hill_path_history = []
        self.search_start_pos = None
        self.celebration_timer = 0.0

    def on_enter(self, **kwargs):
        if self.game_state.level == 4:
            self.manager.change(C.STATE_CARO)
            return

        self.finished = False
        self.celebration_timer = 0.0
        self.auto_play = True
        self.step_timer = 0.0
        self.depth_limit = None
        self.restarting = False
        self.player.set_kit(self.game_state.kit_index)
        self.player.set_variant(Player.variant_for_level(self.game_state.level))
        self.dialogue.set_text(C.LEVEL_INTRO_LINES[self.game_state.level], kit_index=self.game_state.kit_index)

        level_algorithms = C.LEVEL_ALGORITHMS[self.game_state.level]
        if self.game_state.level == 3:
            self.level4_tab = 0
            algorithms = level_algorithms
        else:
            algorithms = level_algorithms
        suggested = self.game_state.suggest_algorithm
        self.algorithm_name = suggested if suggested in algorithms else algorithms[0]
        self.game_state.suggest_algorithm = None
        self._create_algorithm_buttons()
        self._reset_algorithm_run(reset_energy=False)
        AudioManager.instance().play_bgm("gameplay_search", volume=0.42)

    def handle_event(self, event):
        self.dialogue.handle_event(event)
        if self.randomize_button is not None:
            self.randomize_button.handle_event(event)
        if self.matrix_edit_button is not None:
            self.matrix_edit_button.handle_event(event)
        if self.belief_button is not None:
            self.belief_button.handle_event(event)
        if self.and_or_button is not None:
            self.and_or_button.handle_event(event)
        if self.back_button is not None:
            self.back_button.handle_event(event)
        if self.return_button is not None:
            self.return_button.handle_event(event)
        if self.progress_prev_button is not None:
            self.progress_prev_button.handle_event(event)
        if self.progress_next_button is not None:
            self.progress_next_button.handle_event(event)
        if self.progress_auto_button is not None:
            self.progress_auto_button.handle_event(event)
        if self.level4_toggle is not None:
            self.level4_toggle.handle_event(event)
        for button in self.algorithm_buttons:
            button.handle_event(event)

        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.matrix_edit_mode
            and self.game_state.level in EDITABLE_MATRIX_LEVELS
        ):
            if self._handle_matrix_edit_click(event.pos):
                return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                self._handle_player_move(event.key)
            elif event.key == pygame.K_s:
                self._on_dialogue_advance()
            elif event.key == pygame.K_a:
                self.auto_play = not self.auto_play
            elif event.key == pygame.K_r:
                self.game_state.restart_level()
                self._reset_algorithm_run(reset_energy=False)

    def update(self, dt):
        self.dialogue.update(dt)
        self.player.update(dt)
        self.fire.update(dt)

        if self.celebration_timer > 0:
            self.celebration_timer = max(0.0, self.celebration_timer - dt)
            if self.celebration_timer == 0.0:
                self._complete_level_transition()
            return

        if self.follow_path and not self.player.is_moving:
            next_pos = self.follow_path.pop(0)
            if next_pos != (self.player.col, self.player.row):
                if not self._move_player(next_pos):
                    self.follow_path = []
                    self.auto_play = False
                    if self.algorithm_name in HILL_CLIMBING_ALGORITHMS and "loop" in self.hill_status_message.lower():
                        return
                    self._go_gameover("stuck")
                    return
            if not self.follow_path:
                self.dialogue.set_status("")
            return

        if self.finished or self.player.is_moving:
            return
        if not self.dialogue.fully_revealed and not self._should_draw_hill_climbing_table():
            return

        if self.auto_play:
            self.step_timer += dt
            if self.step_timer >= 0.48:
                self.step_timer = 0.0
                self._advance_algorithm()

    def draw(self, surface):
        draw_stadium_background(surface)
        self._draw_headers(surface)
        self._draw_thumbnail(surface)
        self._draw_grid(surface)
        self._draw_side_panel(surface)
        if self._should_draw_blind_search_table():
            self._draw_blind_search_table(surface)
        elif self._should_draw_hill_climbing_table():
            self._draw_hill_climbing_table(surface)
        else:
            self.dialogue.draw(surface)
        draw_outer_frame(surface)

    # ------------------------------------------------------------------
    def _create_algorithm_buttons(self):
        panel = C.SIDE_PANEL_RECT
        button_h = 28
        gap = 5
        self.level4_toggle = None
        if self.game_state.level == 3:
            self.level4_toggle = ToggleGroup(
                pygame.Rect(panel.left + 12, panel.top + 18, panel.width - 24, button_h),
                ["4.1", "4.2", "4.3"],
                on_select=self._select_level4_tab,
                font_size=11,
            )
            self.level4_toggle.selected = self.level4_tab
            top = panel.top + 58
            if self.level4_tab == 2:
                algorithms = []
                columns = 1
                btn_width = panel.width - 24
            else:
                algorithms = C.LEVEL_ALGORITHMS[3]
                columns = 2
                btn_width = int((panel.width - 24 - gap) / columns)
        else:
            algorithms = C.LEVEL_ALGORITHMS[self.game_state.level]
            total_h = len(algorithms) * button_h + (len(algorithms) - 1) * gap
            if self.game_state.level in EDITABLE_MATRIX_LEVELS:
                top = panel.bottom - 3 * button_h - 2 * gap - 12 - total_h - 14
            else:
                top = panel.bottom - total_h - 12
            columns = 1
            btn_width = panel.width - 24

        self.randomize_button = None
        self.matrix_edit_button = None
        self.matrix_edit_mode = False
        self.belief_button = None
        self.and_or_button = None
        self.progress_prev_button = None
        self.progress_next_button = None
        self.progress_auto_button = None
        self.return_button = None
        self.back_button = Button(
            pygame.Rect(panel.left + 12, panel.bottom - 3 * button_h - 2 * gap - 12, panel.width - 24, button_h),
            "BACK",
            font_size=11,
            on_click=self._back_to_level_select,
        )

        if self.game_state.level in EDITABLE_MATRIX_LEVELS:
            bottom_gap = 5
            bottom_w = (panel.width - 24 - bottom_gap) // 2
            self.return_button = Button(
                pygame.Rect(panel.left + 12, panel.bottom - button_h - 12, bottom_w, button_h),
                "RETURN",
                font_size=10,
                on_click=self._return_to_start,
            )
            self.back_button = Button(
                pygame.Rect(panel.left + 12 + bottom_w + bottom_gap, panel.bottom - button_h - 12,
                            panel.width - 24 - bottom_w - bottom_gap, button_h),
                "BACK",
                font_size=10,
                on_click=self._back_to_level_select,
            )
            control_y = panel.bottom - 2 * button_h - gap - 12
            if self.game_state.level in PROGRESS_HISTORY_LEVELS:
                control_w = (panel.width - 24 - gap * 2) // 3
                self.progress_prev_button = Button(
                    pygame.Rect(panel.left + 12, control_y, control_w, button_h),
                    "PREV",
                    font_size=10,
                    on_click=self._rewind_algorithm_progress,
                )
                self.progress_next_button = Button(
                    pygame.Rect(panel.left + 12 + control_w + gap, control_y, control_w, button_h),
                    "NEXT",
                    font_size=10,
                    on_click=self._advance_algorithm_progress,
                )
                self.progress_auto_button = Button(
                    pygame.Rect(panel.left + 12 + (control_w + gap) * 2, control_y, control_w, button_h),
                    "AUTO",
                    font_size=10,
                    on_click=self._toggle_algorithm_auto,
                )
            else:
                control_w = (panel.width - 24 - gap) // 2
                self.progress_next_button = Button(
                    pygame.Rect(panel.left + 12, control_y, control_w, button_h),
                    "NEXT",
                    font_size=10,
                    on_click=self._advance_algorithm_progress,
                )
                self.progress_auto_button = Button(
                    pygame.Rect(panel.left + 12 + control_w + gap, control_y, control_w, button_h),
                    "AUTO",
                    font_size=10,
                    on_click=self._toggle_algorithm_auto,
                )
            edit_y = panel.bottom - 3 * button_h - 2 * gap - 12
            edit_w = (panel.width - 24 - gap) // 2
            self.randomize_button = Button(
                pygame.Rect(panel.left + 12, edit_y, edit_w, button_h),
                "RANDOM",
                font_size=10,
                on_click=self._toggle_random_demo,
            )
            self.matrix_edit_button = Button(
                pygame.Rect(panel.left + 12 + edit_w + gap, edit_y, edit_w, button_h),
                "EDIT",
                font_size=10,
                on_click=self._toggle_matrix_edit_mode,
            )
        elif self.game_state.level == 3 and self.level4_tab == 2:
            self.back_button = Button(
                pygame.Rect(panel.left + 12, panel.bottom - 2 * button_h - gap - 12, panel.width - 24, button_h),
                "BACK",
                font_size=11,
                on_click=self._back_to_level_select,
            )
            self.and_or_button = Button(
                pygame.Rect(panel.left + 12, panel.bottom - button_h - 12, panel.width - 24, button_h),
                "AND OR SEARCH",
                font_size=12,
                on_click=self._run_and_or_search,
            )
        else:
            if self.game_state.level == 2 or (self.game_state.level == 3 and self.level4_tab != 2):
                self.randomize_button = Button(
                    pygame.Rect(panel.left + 12, panel.bottom - 2 * button_h - gap - 12, panel.width - 24, button_h),
                    "RANDOMIZE",
                    font_size=11,
                    on_click=self._toggle_random_demo,
                )
            if self.game_state.level == 3:
                self.belief_button = Button(
                    pygame.Rect(panel.left + 12, panel.bottom - button_h - 12, panel.width - 24, button_h),
                    "BELIEF",
                    font_size=11,
                    on_click=self._reveal_belief,
                )
        self.algorithm_buttons = []
        for i, name in enumerate(algorithms):
            col_index = i % columns
            row_index = i // columns
            rect = pygame.Rect(
                panel.left + 12 + col_index * (btn_width + gap),
                top + row_index * (button_h + gap),
                btn_width,
                button_h,
            )
            self.algorithm_buttons.append(Button(rect, name, font_size=11, on_click=lambda n=name: self._select_algorithm(n)))

    def _select_algorithm(self, name):
        if not name:
            return
        if self.grid is None:
            self._reset_algorithm_run(reset_energy=False)
        if self.grid is None:
            return
        if name not in ALGORITHM_FACTORIES:
            self.dialogue.set_status(f"Thuật toán {name} chưa hỗ trợ")
            return

        # Mỗi lần chọn thuật toán, bắt đầu từ đúng ô CR7 đang đứng.
        # Không đưa nhân vật về grid.start và không hồi lại năng lượng ngầm.
        start_pos = (self.player.col, self.player.row)
        if start_pos not in self.grid.cells or not self.grid.get(*start_pos).passable:
            start_pos = self.grid.start
            self.player.place_at_grid(*start_pos, self.grid_rect.topleft, self.cell_size)

        self.algorithm_name = name
        self.game_state.suggest_algorithm = None
        self.matrix_edit_mode = False
        self.follow_path = []
        self.player._tween_x = None
        self.player._tween_y = None
        self.player.state = "idle"
        self.current = start_pos
        self.search_start_pos = start_pos
        self._clear_algorithm_scores()
        if self.game_state.level == 2:
            self._apply_hill_climbing_h_values(self.grid)

        self.algorithm_health = self.game_state.current_health
        try:
            self.generator = ALGORITHM_FACTORIES[self.algorithm_name](
                self.grid,
                start=start_pos,
                health=self.algorithm_health,
            )
        except Exception as exc:
            self.generator = None
            self.auto_play = False
            self.searching = False
            self.dialogue.set_status(f"Không thể khởi chạy {name}: {exc}")
            print(f"[Gameplay] failed to start algorithm {name}: {exc}")
            return

        self.visited = {start_pos}
        self.frontier = set()
        self.final_path = []
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.depth_limit = None
        self.restarting = False
        self.search_trace_rows = []
        self.last_search_step = None
        self.algorithm_history = []
        self.algorithm_history_index = -1
        self.hill_trace_rows = []
        self.hill_status_message = ""
        self.hill_path_history = [start_pos]
        self.finished = False
        self.searching = False
        self.auto_play = True
        self.step_timer = 0.0
        self.dialogue.set_status(
            f"Đang chạy {name} từ vị trí hiện tại {start_pos}..."
        )

    def _run_and_or_search(self):
        if self.grid is None:
            return
        self.algorithm_name = "AND OR SEARCH"
        self.game_state.suggest_algorithm = None
        self.generator = ALGORITHM_FACTORIES[self.algorithm_name](self.grid, start=(self.player.col, self.player.row), health=self.algorithm_health)
        self.visited = {self.current}
        self.frontier = set()
        self.final_path = []
        self.follow_path = []
        self.neighbor_scores = {}
        self.and_or_dark = True
        self.and_or_branch = set()
        self.and_or_goal = None
        self.and_or_path = []
        self.chosen = None
        self.temperature = None
        self.finished = False
        self.auto_play = True
        self.step_timer = 0.0
        self.dialogue.set_text("And-Or search đang chạy...", kit_index=self.game_state.kit_index)

    def _handle_player_move(self, key):
        if not self._can_control_player():
            return

        direction_map = {
            pygame.K_LEFT: (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_UP: (0, -1),
            pygame.K_DOWN: (0, 1),
        }
        if direction_map.get(key) is None:
            return
        delta = direction_map.get(key)
        if delta is None:
            return

        target = (self.player.col + delta[0], self.player.row + delta[1])
        self.auto_play = False
        self._move_player(target)

    def _can_control_player(self):
        return (
            self.grid is not None
            and not self.finished
            and not self.player.is_moving
            and (self.dialogue.fully_revealed or self._should_draw_hill_climbing_table())
        )

    def _is_orthogonal_step(self, pos):
        if self.grid is None or pos is None:
            return False
        dx = abs(pos[0] - self.player.col)
        dy = abs(pos[1] - self.player.row)
        return (dx + dy) == 1 and (dx == 0 or dy == 0)

    def _next_step_towards(self, target):
        if self.grid is None or target is None:
            return None

        start = (self.player.col, self.player.row)
        if start == target:
            return target

        queue = deque([start])
        parents = {start: None}
        while queue:
            current = queue.popleft()
            for cell in self.grid.neighbors(*current):
                pos = (cell.col, cell.row)
                if pos in parents:
                    continue
                parents[pos] = current
                if pos == target:
                    path = [pos]
                    while parents[path[-1]] is not None:
                        path.append(parents[path[-1]])
                    path.reverse()
                    return path[1] if len(path) > 1 else target
                queue.append(pos)
        return None

    def _reset_algorithm_run(self, reset_energy=True):
        if reset_energy:
            self.game_state.restart_level()
        self.game_state.reset_health()
        if self.game_state.level == 3:
            self.grid = self._build_level4_grid()
        else:
            self.grid = self._build_grid(self.game_state.level)
        self._clear_algorithm_scores()
        if self.game_state.level == 1:
            self._apply_informed_default_values(self.grid)
        if self.game_state.level == 2:
            self._randomize_hill_matrix(self.grid)
            self._apply_hill_climbing_h_values(self.grid)
        self.grid_rect, self.cell_size = self._grid_geometry(self.grid.cols, self.grid.rows)
        self.player.set_variant(Player.variant_for_level(self.game_state.level))
        self.player.place_at_grid(*self.grid.start, self.grid_rect.topleft, self.cell_size)
        if self.game_state.level not in {0, 2, 3}:
            self.grid.reveal_around(*self.grid.start, radius=1)
        self.visited = {self.grid.start}
        self.frontier = set()
        self.final_path = []
        self.follow_path = []
        self.current = self.grid.start
        self.search_start_pos = self.grid.start
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.depth_limit = None
        self.restarting = False
        self.algorithm_health = self.game_state.current_health
        self.finished = False
        self.celebration_timer = 0.0
        self.auto_play = False
        self.step_timer = 0.0
        self.searching = False
        self.and_or_dark = False
        self.and_or_branch = set()
        self.and_or_goal = None
        self.and_or_path = []
        self.and_or_choices = set()
        self.and_or_selected_choice = None
        self.search_trace_rows = []
        self.last_search_step = None
        self.algorithm_history = []
        self.algorithm_history_index = -1
        self.hill_trace_rows = []
        self.hill_status_message = ""
        self.hill_path_history = [self.current] if self.current is not None else []
        self.generator = ALGORITHM_FACTORIES[self.algorithm_name](self.grid, start=self.current, health=self.algorithm_health)

    def _build_grid(self, level):
        cols, rows = C.LEVEL_GRID_SIZE[level]
        layout = LEVEL_LAYOUTS[level]
        grid = GridModel(cols, rows, layout["start"], layout["goal"], fog=layout.get("fog", False))
        for kind in ("path", "danger", "fire", "wall"):
            for col, row in layout.get(kind, []):
                if (col, row) not in (grid.start, grid.goal):
                    grid.set_kind(col, row, kind)
        grid.set_kind(*grid.start, "start")
        grid.set_kind(*grid.goal, "trophy")
        return grid

    def _clear_algorithm_scores(self):
        if self.grid is None:
            return
        for cell in self.grid.cells.values():
            cell.g = 0
            cell.h = 0
            cell.f = 0

    def _apply_informed_default_values(self, grid):
        for pos, cell in grid.cells.items():
            if pos == grid.start:
                cell.value = 0
                cell.kind = "start"
            elif pos == grid.goal:
                cell.value = 0
                cell.kind = "trophy"
            elif cell.kind == "wall":
                cell.value = None
            elif cell.kind == "fire":
                cell.value = -35
            elif cell.kind == "danger":
                cell.value = -20
            elif cell.kind == "path":
                cell.value = 8
            else:
                cell.value = 0

    def _build_level4_grid(self):
        grid = self._build_grid(3)
        self._randomize_value_cells(grid)
        if self.level4_tab == 0:
            # No observation: tất cả ô trừ start/goal đều là ?
            for pos, cell in grid.cells.items():
                if pos not in (grid.start, grid.goal):
                    cell.revealed = False
        elif self.level4_tab == 1:
            # Partial observation: để lộ một vài ô, còn lại là ?
            for pos, cell in grid.cells.items():
                if pos in (grid.start, grid.goal):
                    continue
                cell.revealed = random.random() < 0.25
        else:
            # Full observation: tất cả ô đều lộ ra ngay từ đầu
            for cell in grid.cells.values():
                cell.revealed = True
        grid.set_kind(*grid.start, "start")
        grid.set_kind(*grid.goal, "trophy")
        return grid

    def _grid_geometry(self, cols, rows):
        cell = min(C.GRID_CELL_SIZE, C.GRID_RECT.width // cols, C.GRID_RECT.height // rows)
        rect = pygame.Rect(C.GRID_ORIGIN[0], C.GRID_ORIGIN[1], cols * cell, rows * cell)
        return rect, cell

    def _on_dialogue_advance(self):
        if not self.dialogue.fully_revealed:
            return
        self.auto_play = False
        if self.generator is None:
            return
        self._advance_algorithm()

    def _advance_algorithm_progress(self):
        self.auto_play = False
        if self._can_restore_next_progress_step():
            self._restore_algorithm_progress(self.algorithm_history_index + 1)
            return
        self._advance_algorithm()

    def _rewind_algorithm_progress(self):
        self.auto_play = False
        if not self.algorithm_history:
            self.dialogue.set_status("Chua co tien trinh de tua lai")
            return
        if self.algorithm_history_index <= 0:
            self._restore_algorithm_progress(0)
            self.dialogue.set_status("Dang o buoc dau tien")
            return
        self._restore_algorithm_progress(self.algorithm_history_index - 1)

    def _toggle_algorithm_auto(self):
        if self.finished:
            return
        self.auto_play = not self.auto_play
        self.step_timer = 0.0
        self.dialogue.set_status("Tu dong" if self.auto_play else "Tam dung")

    def _can_restore_next_progress_step(self):
        return (
            self.game_state.level in {0, 1}
            and self.algorithm_name in TRACE_TABLE_ALGORITHMS
            and 0 <= self.algorithm_history_index < len(self.algorithm_history) - 1
        )

    def _advance_algorithm(self):
        if self.finished or self.player.is_moving or self.generator is None:
            return
        try:
            step = next(self.generator)
        except StopIteration:
            if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                self.generator = None
                self.auto_play = False
                self.searching = False
                self.hill_status_message = "Thuật toán đã dừng. Hãy RANDOM hoặc EDIT ma trận để thử lại."
                self.dialogue.set_status(self.hill_status_message)
            else:
                self._go_gameover("stuck")
            return
        except Exception as exc:
            self.generator = None
            self.auto_play = False
            self.searching = False
            self.dialogue.set_status(f"Thuật toán dừng do lỗi: {exc}")
            print(f"[Gameplay] algorithm step failed: {exc}")
            return
        if self.game_state.level in {0, 1} and self.algorithm_name in TRACE_TABLE_ALGORITHMS:
            self._store_algorithm_progress_step(step)

        try:
            self.current = step.get("current") or self.current
            self.neighbor_scores = step.get("neighbor_scores", {})
            self.chosen = step.get("chosen")
            self.temperature = step.get("temperature")
            self.depth_limit = step.get("depth_limit", self.depth_limit)
            self.restarting = step.get("restarting", False)

            if self.algorithm_name == "AND OR SEARCH":
                self.and_or_dark = step.get("dark", self.and_or_dark)
                self.and_or_branch = set(step.get("highlight_branch", self.and_or_branch))
                self.and_or_goal = step.get("goal", self.and_or_goal)
                self.and_or_path = list(step.get("or_path", self.and_or_path))
                self.and_or_choices = set(step.get("branch_choices", self.and_or_choices))
                self.and_or_selected_choice = step.get("selected_choice", self.and_or_selected_choice)
            elif self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                self.frontier = set(self.neighbor_scores.keys())
                self.visited = set(self.hill_path_history)
                self._record_hill_climbing_step(step)
            else:
                self.frontier = set(step.get("frontier", []))
                if self.game_state.level == 1 and self.algorithm_name in INFORMED_SEARCH_ALGORITHMS:
                    self.visited = set(step.get("expanded", []))
                else:
                    self.visited = set(step.get("visited", self.visited))
                if self.game_state.level in {0, 1} and self.algorithm_name in TRACE_TABLE_ALGORITHMS:
                    self._record_blind_search_step(step)

            if self.algorithm_name == "IDS" and self.depth_limit is not None:
                label = f"IDS depth={self.depth_limit}"
                if self.restarting:
                    label += " (restart)"
                self.dialogue.set_status(label)

            if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                self._set_hill_climbing_dialogue(step)
                loop_detected = bool(step.get("loop")) or (
                    self.chosen is not None and self.chosen in self.hill_path_history
                )
                if loop_detected:
                    self.generator = None
                    self.auto_play = False
                    self.searching = False
                    self.chosen = step.get("candidate") or self.chosen
                    self.hill_status_message = (
                        "Đã dính loop: thuật toán quay lại ô đã đi qua. "
                        "Hãy RANDOM hoặc EDIT ma trận rồi chạy lại."
                    )
                    self.dialogue.set_status(self.hill_status_message)
                    return

            if step.get("stuck"):
                if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                    self.generator = None
                    self.auto_play = False
                    self.searching = False
                    self.hill_status_message = (
                        "Đã kẹt tại cực trị cục bộ: không còn neighbor nào có h(n) tốt hơn. "
                        "Hãy RANDOM hoặc EDIT ma trận để thử lại."
                    )
                    self.dialogue.set_status(self.hill_status_message)
                else:
                    self._go_gameover("stuck")
                return

            path = step.get("path")
            if path is not None:
                if path:
                    self.final_path = path
                    self.searching = False
                    self.follow_path = list(path)
                    self.auto_play = False
                    self.step_timer = 0.0
                    self.dialogue.set_status("Đã tìm được đường đi. CR7 sẽ di chuyển.")
                else:
                    self._go_gameover("stuck")
                return

            if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                if self.chosen and self.chosen != (self.player.col, self.player.row):
                    self.searching = False
                    self.follow_path = [self.chosen]
                    self.step_timer = 0.0
                    self.dialogue.set_status("Đã chọn Next Node. CR7 sẽ di chuyển.")
                    return
                self.searching = True
            elif self.algorithm_name == "AND OR SEARCH":
                if step.get("status") is not None:
                    self.dialogue.set_status(step.get("status"))
                else:
                    self.dialogue.set_status("And-Or search đang tiến hành...")
                return
            else:
                self.searching = True

            if self.game_state.level in {0, 1} and self.algorithm_name in TRACE_TABLE_ALGORITHMS:
                self.dialogue.set_status("")
            else:
                self.dialogue.set_status("Đang suy nghĩ...")
            return
        except Exception as exc:
            self.generator = None
            self.auto_play = False
            self.searching = False
            self.dialogue.set_status(f"Xử lý thuật toán bị lỗi: {exc}")
            print(f"[Gameplay] algorithm processing failed: {exc}")
            return

    def _toggle_random_demo(self):
        if self.grid is None:
            return
        if self.game_state.level == 0:
            self._randomize_blind_matrix(self.grid)
        elif self.game_state.level == 1:
            self._randomize_informed_matrix(self.grid)
        elif self.game_state.level == 2:
            self._randomize_hill_matrix(self.grid)
            self._apply_hill_climbing_h_values(self.grid)
        else:
            self._randomize_value_cells(self.grid)
            self.grid.reveal_around(*self.grid.start, radius=1)
        self.matrix_edit_mode = False
        self._restart_algorithm_on_current_grid(reset_health=True)
        if self.game_state.level == 2:
            self.hill_status_message = "Đã tạo ma trận ngẫu nhiên mới. h(n) được tính lại theo Goal."
        self.dialogue.set_status("Da tao ma tran moi")

    def _toggle_matrix_edit_mode(self):
        if self.game_state.level not in EDITABLE_MATRIX_LEVELS:
            return
        self.matrix_edit_mode = not self.matrix_edit_mode
        self.auto_play = False
        message = "EDIT: bấm ô để đổi Safe → Danger → Fire → Wall" if self.matrix_edit_mode else "Đã tắt EDIT"
        if self.game_state.level == 2:
            self.hill_status_message = message
        self.dialogue.set_status(message)

    def _handle_matrix_edit_click(self, mouse_pos):
        if self.grid is None or not self.grid_rect.collidepoint(mouse_pos):
            return False
        col = (mouse_pos[0] - self.grid_rect.left) // self.cell_size
        row = (mouse_pos[1] - self.grid_rect.top) // self.cell_size
        pos = (int(col), int(row))
        if pos not in self.grid.cells:
            return False
        if pos in (self.grid.start, self.grid.goal):
            self.dialogue.set_status("Khong sua o Start/Goal")
            return True

        cell = self.grid.cells[pos]
        if self.game_state.level == 0:
            cell.kind = "grass" if cell.kind == "wall" else "wall"
            cell.value = None
            cell.revealed = True
        elif self.game_state.level == 1:
            self._cycle_informed_cell(cell)
        elif self.game_state.level == 2:
            self._cycle_hill_cell(cell)
            self._apply_hill_climbing_h_values(self.grid)

        self._restart_algorithm_on_current_grid(reset_health=True)
        self.matrix_edit_mode = True
        if self.game_state.level == 2:
            self.hill_status_message = "Đã cập nhật ma trận và tính lại h(n)."
        self.dialogue.set_status("Da cap nhat ma tran")
        return True

    def _cycle_informed_cell(self, cell):
        if cell.kind == "wall":
            self._set_value_cell(cell, 8)
        elif cell.value is None or cell.value > 0:
            self._set_value_cell(cell, 0)
        elif cell.value == 0:
            self._set_value_cell(cell, -25)
        else:
            cell.kind = "wall"
            cell.value = None
            cell.revealed = True

    def _cycle_hill_cell(self, cell):
        """Cycle signed Level-3 values: +10 -> +5 -> -5 -> -10 -> wall."""
        if cell.kind == "wall" or cell.value is None:
            self._set_value_cell(cell, 10)
        elif cell.value >= 10:
            self._set_value_cell(cell, 5)
        elif cell.value > 0:
            self._set_value_cell(cell, -5)
        elif cell.value >= -5:
            self._set_value_cell(cell, -10)
        else:
            cell.kind = "wall"
            cell.value = None
            cell.revealed = True

    def _set_value_cell(self, cell, value):
        cell.value = value
        cell.revealed = True
        if value > 0:
            cell.kind = "path"
        elif value == 0:
            cell.kind = "path"
        else:
            cell.kind = "fire"

    def _restart_algorithm_on_current_grid(self, reset_health=True):
        if self.grid is None:
            return
        if reset_health:
            self.game_state.reset_health()
        self._clear_algorithm_scores()
        self.player.place_at_grid(*self.grid.start, self.grid_rect.topleft, self.cell_size)
        self.player._tween_x = None
        self.player._tween_y = None
        self.player.state = "idle"
        self.visited = {self.grid.start}
        self.frontier = set()
        self.final_path = []
        self.follow_path = []
        self.current = self.grid.start
        self.search_start_pos = self.grid.start
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.depth_limit = None
        self.restarting = False
        self.algorithm_health = self.game_state.current_health
        self.finished = False
        self.auto_play = False
        self.step_timer = 0.0
        self.searching = False
        self.search_trace_rows = []
        self.last_search_step = None
        self.algorithm_history = []
        self.algorithm_history_index = -1
        self.hill_trace_rows = []
        self.hill_status_message = ""
        self.hill_path_history = [self.current] if self.current is not None else []
        if self.game_state.level == 2:
            self._apply_hill_climbing_h_values(self.grid)
        self.generator = ALGORITHM_FACTORIES[self.algorithm_name](
            self.grid,
            start=self.current,
            health=self.algorithm_health,
        )

    def _randomize_blind_matrix(self, grid):
        for _ in range(80):
            for pos, cell in grid.cells.items():
                cell.value = None
                cell.revealed = True
                if pos == grid.start:
                    cell.kind = "start"
                elif pos == grid.goal:
                    cell.kind = "trophy"
                else:
                    cell.kind = "wall" if random.random() < 0.18 else "grass"
            if self._has_route(grid):
                return
        for pos, cell in grid.cells.items():
            if pos == grid.start:
                cell.kind = "start"
            elif pos == grid.goal:
                cell.kind = "trophy"
            else:
                cell.kind = "grass"
                cell.value = None

    def _randomize_informed_matrix(self, grid):
        value_choices = [-35, -25, -15, 0, 8, 12, 16]
        weights = [12, 14, 12, 20, 17, 15, 10]
        for pos, cell in grid.cells.items():
            cell.revealed = True
            if pos == grid.start:
                cell.kind = "start"
                cell.value = 0
            elif pos == grid.goal:
                cell.kind = "trophy"
                cell.value = 0
            elif random.random() < 0.13:
                cell.kind = "wall"
                cell.value = None
            else:
                self._set_value_cell(cell, random.choices(value_choices, weights=weights, k=1)[0])

        for pos in self._simple_route(grid.start, grid.goal):
            if pos in (grid.start, grid.goal):
                continue
            cell = grid.cells[pos]
            self._set_value_cell(cell, random.choice([0, 8, 12]))

        grid.set_kind(*grid.start, "start")
        grid.set_kind(*grid.goal, "trophy")

    def _randomize_hill_matrix(self, grid):
        """Create Level-3 cells with signed values while keeping h(n) separate.

        The signed value changes health/energy when CR7 enters a cell. Hill
        Climbing still compares candidates only with the shared h(n), so this
        Level-3 display does not change Levels 1 or 2.
        """
        signed_values = [-20, -10, -5, 5, 10, 15, 20]
        signed_weights = [5, 9, 13, 18, 20, 18, 17]
        for _ in range(80):
            for pos, cell in grid.cells.items():
                cell.revealed = True
                if pos == grid.start:
                    cell.kind = "start"
                    cell.value = 0
                elif pos == grid.goal:
                    cell.kind = "trophy"
                    cell.value = 0
                elif random.random() < 0.12:
                    cell.kind = "wall"
                    cell.value = None
                else:
                    self._set_value_cell(
                        cell,
                        random.choices(signed_values, weights=signed_weights, k=1)[0],
                    )
            if self._has_route(grid):
                break
        else:
            for pos, cell in grid.cells.items():
                if pos == grid.start:
                    cell.kind, cell.value = "start", 0
                elif pos == grid.goal:
                    cell.kind, cell.value = "trophy", 0
                else:
                    cell.kind, cell.value = "path", 0
                cell.revealed = True

        grid.set_kind(*grid.start, "start")
        grid.set_kind(*grid.goal, "trophy")

    def _apply_hill_climbing_h_values(self, grid):
        """Cache the shared h(n) on every cell for display and inspection."""
        for (col, row), cell in grid.cells.items():
            cell.h = float(grid.heuristic_value(col, row)) if cell.passable else 0.0

    def _simple_route(self, start, goal):
        if start is None or goal is None:
            return []
        col, row = start
        route = [(col, row)]
        while col != goal[0]:
            col += 1 if goal[0] > col else -1
            route.append((col, row))
        while row != goal[1]:
            row += 1 if goal[1] > row else -1
            route.append((col, row))
        return route

    def _has_route(self, grid):
        if grid.start is None or grid.goal is None:
            return True
        queue = deque([grid.start])
        reached = {grid.start}
        while queue:
            current = queue.popleft()
            if current == grid.goal:
                return True
            for cell in grid.neighbors(*current):
                pos = (cell.col, cell.row)
                if pos not in reached:
                    reached.add(pos)
                    queue.append(pos)
        return False

    def _reveal_belief(self):
        if self.grid is None:
            return
        for (col, row), cell in self.grid.cells.items():
            if (col, row) in {self.grid.start, self.grid.goal}:
                continue
            if cell.value is None and cell.kind != "wall":
                cell.value = random.choice([-4, -2, 0, 2, 4])
                if cell.value >= 0:
                    cell.kind = "path"
                else:
                    cell.kind = "danger" if cell.value >= -2 else "fire"
            cell.revealed = True
        self.generator = ALGORITHM_FACTORIES[self.algorithm_name](self.grid, start=(self.player.col, self.player.row), health=self.algorithm_health)
        self.visited = {self.current}
        self.frontier = set()
        self.final_path = []
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.finished = False
        self.auto_play = False
        self.step_timer = 0.0

    def _select_level4_tab(self, index):
        self.level4_tab = index
        if self.algorithm_name not in C.LEVEL_ALGORITHMS[3]:
            self.algorithm_name = C.LEVEL_ALGORITHMS[3][0]
        self._create_algorithm_buttons()
        self._reset_algorithm_run(reset_energy=False)

    def _return_to_start(self):
        """Return CR7 to the original start cell and prepare the selected algorithm again."""
        if self.grid is None or self.grid.start is None:
            return
        self.auto_play = False
        self.finished = False
        self.searching = False
        self.follow_path = []
        self.final_path = []
        self.player._tween_x = None
        self.player._tween_y = None
        self.player.state = "idle"
        self.player.place_at_grid(*self.grid.start, self.grid_rect.topleft, self.cell_size)
        self.game_state.reset_health()
        self.algorithm_health = self.game_state.current_health
        self.current = self.grid.start
        self.search_start_pos = self.grid.start
        self.visited = {self.grid.start}
        self.frontier = set()
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.depth_limit = None
        self.restarting = False
        self.search_trace_rows = []
        self.last_search_step = None
        self.algorithm_history = []
        self.algorithm_history_index = -1
        self.hill_trace_rows = []
        self.hill_status_message = ""
        self.hill_path_history = [self.grid.start]
        self._clear_algorithm_scores()
        if self.game_state.level == 2:
            self._apply_hill_climbing_h_values(self.grid)
        self.generator = ALGORITHM_FACTORIES[self.algorithm_name](
            self.grid, start=self.grid.start, health=self.algorithm_health
        )
        self.dialogue.set_status("Đã RETURN về vị trí xuất phát. Nhấn NEXT/AUTO hoặc chọn thuật toán để chơi lại.")

    def _back_to_level_select(self):
        # Preserve current game state but go back to level selection for customization
        self.game_state.suggest_algorithm = None
        self.manager.change(C.STATE_LEVEL_SELECT)

    def _randomize_value_cells(self, grid):
        max_dist = grid.cols + grid.rows
        for (col, row), cell in grid.cells.items():
            if cell.kind == "wall":
                continue
            if (col, row) == grid.goal:
                continue
            dist = grid.manhattan((col, row), grid.goal)
            value_candidates = [-6, -4, -2, 0, 2, 4]
            weights = []
            for value in value_candidates:
                if value < 0:
                    weights.append(12 + max(0, max_dist - dist) + abs(value))
                elif value == 0:
                    weights.append(8)
                else:
                    weights.append(5 + dist // 2)
            value = random.choices(population=value_candidates, weights=weights, k=1)[0]
            cell.value = value
            if value >= 6:
                cell.kind = "grass"
            elif value > 0:
                cell.kind = "path"
            elif value == 0:
                cell.kind = "path"
            elif value >= -4:
                cell.kind = "danger"
            else:
                cell.kind = "fire"
        if grid.start in grid.cells:
            grid.cells[grid.start].value = random.choice([0, 2, 4])
            grid.cells[grid.start].kind = "start"
        grid.set_kind(*grid.goal, "trophy")

    def _set_hill_climbing_dialogue(self, step):
        current = step.get("current")
        candidate = step.get("candidate")
        chosen = step.get("chosen")
        decision = step.get("decision")
        phase = step.get("phase")
        current_h = self.grid.heuristic_value(*current) if self.grid and current else None
        candidate_h = self.grid.heuristic_value(*candidate) if self.grid and candidate else None

        if decision == "loop":
            message = "Đã dính loop: Next Node đã xuất hiện trong đường đi trước đó."
        elif decision == "stuck":
            message = "Không còn neighbor nào có h(n) nhỏ hơn Current Node."
        elif self.algorithm_name == "Hill Climbing":
            if decision == "reject":
                message = f"{self._node_label(candidate)} h={candidate_h:.0f} không tốt hơn h={current_h:.0f} → LOẠI."
            else:
                message = f"{self._node_label(candidate)} h={candidate_h:.0f} tốt hơn h={current_h:.0f} → NHẬN."
        elif self.algorithm_name == "Steepest Ascent HC":
            if phase == "evaluate_all":
                message = "Đã bật sáng và xuất toàn bộ neighbor để so sánh h(n)."
            else:
                selected = chosen or candidate
                message = f"Chọn {self._node_label(selected)} vì có h(n) nhỏ nhất trong tập neighbor tốt hơn."
        else:
            selected = chosen or candidate
            message = f"Random chọn {self._node_label(selected)} trong tập neighbor có h(n) tốt hơn."

        self.hill_status_message = message
        self.dialogue.set_status(message)

    def _move_player(self, pos):
        if self.grid is None:
            return False

        if not self._is_orthogonal_step(pos):
            next_step = self._next_step_towards(pos)
            if next_step is None:
                return False
            pos = next_step

        cell = self.grid.get(*pos)
        if cell is None or not cell.passable:
            return False
        if self.algorithm_name in HILL_CLIMBING_ALGORITHMS and pos in self.hill_path_history:
            self.generator = None
            self.auto_play = False
            self.searching = False
            self.hill_status_message = (
                "Đã dính loop: không thể quay lại node đã đi qua. "
                "Hãy RANDOM hoặc EDIT ma trận rồi chạy lại."
            )
            self.dialogue.set_status(self.hill_status_message)
            return False
        health_delta = self.grid.health_delta(*pos)
        if self.game_state.current_health + health_delta < 0:
            return False
        self.player.move_to_grid(pos[0], pos[1], self.grid_rect.topleft, self.cell_size)
        self.current = pos
        self.game_state.current_health += health_delta
        self.algorithm_health = self.game_state.current_health
        if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
            self.hill_path_history.append(pos)
            # The previous neighborhood leaves the light cone after movement.
            self.frontier = set()
            self.neighbor_scores = {}
            self.chosen = None
        if self.game_state.level not in {0, 3}:
            self.grid.reveal_around(*pos, radius=1)
        if cell.kind in ("danger", "fire"):
            AudioManager.instance().play_sfx("danger_trigger", volume=0.8)
        else:
            AudioManager.instance().play_sfx("cell_step", volume=0.7)
        if pos == self.grid.goal:
            self._finish_level()
        return True

    def _finish_level(self):
        if self.finished:
            return
        self.finished = True
        if self.game_state.level in {0, 1, 2}:
            self.auto_play = False
            self.searching = False
            self.follow_path = []
            self.player.celebrate()
            self.celebration_timer = 1.65
            AudioManager.instance().play_sfx("siuuu", volume=0.85)
            self.dialogue.set_status("SIUUU! CR7 da cham cup, chuan bi sang man tiep theo.")
            return
        self._complete_level_transition()

    def _complete_level_transition(self):
        if self.game_state.level >= max(C.LEVEL_NAMES.keys()):
            self.manager.change(C.STATE_VICTORY)
            return
        self.game_state.advance_level()
        self.manager.change(C.STATE_LEVELUP)

    def _go_gameover(self, reason):
        self.finished = True
        self.game_state.gameover_reason = reason
        if reason == "stuck":
            if self.game_state.level == 1:
                self.game_state.suggest_algorithm = "A*"
            else:
                self.game_state.suggest_algorithm = "Stochastic HC"
        self.manager.change(C.STATE_GAMEOVER)

    # ------------------------------------------------------------------
    def _draw_headers(self, surface):
        title = C.LEVEL_TITLES.get(self.game_state.level, f"Level {self.game_state.level}")
        draw_text(surface, title, (C.HEADER_TITLE_RECT.centerx, C.HEADER_TITLE_RECT.top + 6),
                  size=21, color=C.COL_CREAM_TEXT, align="center")

        trophy = AssetManager.instance().get_image(
            "sprites/ui/trophy_worldcup.png",
            size=(C.LEVEL_BADGE_ICON_RECT.width, C.LEVEL_BADGE_ICON_RECT.height),
            placeholder=placeholder_trophy,
        )
        surface.blit(trophy, C.LEVEL_BADGE_ICON_RECT.topleft)

    def _draw_thumbnail(self, surface):
        rect = C.THUMBNAIL_MAP_RECT
        draw_wood_panel(surface, rect, border=3, corner=6, fill=(52, 40, 24))
        cell_w = max(2, (rect.width - 14) // self.grid.cols)
        cell_h = max(2, (rect.height - 14) // self.grid.rows)
        ox, oy = rect.left + 7, rect.top + 7
        for (col, row), cell in self.grid.cells.items():
            mini = pygame.Rect(ox + col * cell_w, oy + row * cell_h, cell_w, cell_h)
            pygame.draw.rect(surface, self._cell_color(cell.kind, cell.value), mini)
        draw_text(surface, "path", (rect.centerx, rect.bottom + 3), size=13, color=C.COL_CREAM_TEXT, align="center")

    def _draw_grid(self, surface):
        pygame.draw.rect(surface, C.COL_GOLD, self.grid_rect.inflate(6, 6), 2)
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                cell = self.grid.get(col, row)
                rect = pygame.Rect(
                    self.grid_rect.left + col * self.cell_size,
                    self.grid_rect.top + row * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                self._draw_cell(surface, rect, cell)

        if self.level4_tab == 2 and self.algorithm_name != "AND OR SEARCH" and self.current is not None:
            self._draw_current_overlay(surface, self.current)
        if self.algorithm_name == "AND OR SEARCH" and self.and_or_selected_choice is not None:
            self._draw_current_overlay(surface, self.and_or_selected_choice)
        if self.chosen:
            self._draw_choice_arrow(surface, self.chosen)

        self.player.draw(surface)

    def _draw_cell(self, surface, rect, cell):
        pos = (cell.col, cell.row)
        if not cell.revealed and self.game_state.level == 3 and pos not in (self.grid.start, self.grid.goal):
            pygame.draw.rect(surface, (255, 255, 255), rect)
            pygame.draw.rect(surface, (0, 0, 0), rect, 1)
            draw_text(surface, "?", rect.center, size=24, color=(0, 0, 0), align="center")
            if pos == self.current:
                pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, rect.inflate(-4, -4), 2)
            return

        pygame.draw.rect(surface, self._cell_color(cell.kind, cell.value), rect)
        pygame.draw.rect(surface, (48, 72, 42), rect, 1)

        if (
            self.game_state.level in {0, 1}
            and self.algorithm_name in TRACE_TABLE_ALGORITHMS
            and pos in self.frontier
        ):
            self._overlay(surface, rect, (*C.COL_FRONTIER, 95))
        elif pos in self.frontier and self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
            self._overlay(surface, rect, (*C.COL_FRONTIER, 100))
        elif pos in self.visited:
            self._overlay(surface, rect, (*C.COL_VISITED, 75))
        if pos in self.final_path:
            self._overlay(surface, rect, (*C.COL_PATH_FINAL, 120))

        highlighted_pos = (self.player.col, self.player.row)
        if pos == highlighted_pos:
            pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, rect.center, max(8, min(rect.width, rect.height) // 2 - 4), 3)
        elif pos == self.current:
            pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, rect.inflate(-4, -4), 2)
        if pos == self.chosen and pos != self.current:
            pygame.draw.rect(surface, C.COL_GOLD, rect.inflate(-10, -10), 3)

        if cell.kind == "fire":
            self.fire.draw(surface, rect.inflate(-10, -8))
        elif cell.kind == "trophy":
            trophy = AssetManager.instance().get_image(
                "sprites/ui/trophy_worldcup.png",
                size=(int(self.cell_size * 0.75), int(self.cell_size * 0.85)),
                placeholder=placeholder_trophy,
            )
            surface.blit(trophy, trophy.get_rect(center=rect.center))

        if self._should_draw_cell_value(cell):
            if self.game_state.level == 2 and self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                h_value = self.grid.heuristic_value(cell.col, cell.row)
                signed_value = cell.value if cell.value is not None else 0
                value_label = f"{signed_value:+d}"
                text_color = C.COL_BLACK if cell.kind in {"path", "start", "trophy"} else C.COL_CREAM_TEXT
                draw_text(surface, value_label, (rect.centerx, rect.centery - 9), size=17,
                          color=text_color, align="center")
                draw_text(surface, f"h={h_value:.0f}", (rect.left + 4, rect.top + 3), size=10,
                          color=text_color, align="left", shadow=False)
            else:
                label = str(cell.value if cell.value is not None else cell.cost)
                text_color = C.COL_BLACK if cell.value == 0 else C.COL_CREAM_TEXT
                draw_text(surface, label, (rect.centerx, rect.centery - 11), size=18,
                          color=text_color, align="center")

        if not cell.revealed and self.game_state.level == 3:
            if pos not in (self.grid.start, self.grid.goal):
                draw_text(surface, "?", rect.center, size=24, color=C.COL_CREAM_TEXT, align="center")

        if self.algorithm_name == "AND OR SEARCH" and self.and_or_dark:
            self._overlay(surface, rect, (0, 0, 0, 180))
        if self.algorithm_name == "AND OR SEARCH" and pos in self.and_or_choices:
            self._overlay(surface, rect, (250, 220, 140, 180))
        if self.algorithm_name == "AND OR SEARCH" and pos == self.and_or_selected_choice:
            self._overlay(surface, rect, (*C.COL_HIGHLIGHT_PURPLE, 220))
        if self.algorithm_name == "AND OR SEARCH" and pos in self.and_or_branch:
            self._overlay(surface, rect, (250, 220, 140, 180))
        if self.algorithm_name == "AND OR SEARCH" and self.and_or_goal == pos:
            self._overlay(surface, rect, (*C.COL_HIGHLIGHT_PURPLE, 220))
        if self.algorithm_name == "AND OR SEARCH" and pos in self.and_or_path:
            self._overlay(surface, rect, (170, 250, 180, 180))

        if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
            if pos not in self.frontier and pos != self.current and pos != self.chosen and pos not in self.final_path:
                self._overlay(surface, rect, (0, 0, 0, 150))

        if self.level4_tab == 2 and pos == self.current:
            self._overlay(surface, rect, (*C.COL_HIGHLIGHT_PURPLE, 180))

        if self._should_dim_level_one_cell(pos):
            self._overlay(surface, rect, (0, 0, 0, 178))

        if not cell.revealed and self.game_state.level != 3:
            self._overlay(surface, rect, (*C.COL_FOG, 185))

    def _draw_choice_arrow(self, surface, pos):
        rect = pygame.Rect(
            self.grid_rect.left + pos[0] * self.cell_size,
            self.grid_rect.top + pos[1] * self.cell_size,
            self.cell_size,
            self.cell_size,
        )
        cx, cy = rect.center
        arrow_path = C.ASSETS_DIR / "sprites/ui/path_arrow.png"
        if arrow_path.exists():
            arrow = AssetManager.instance().get_image(
                "sprites/ui/path_arrow.png",
                size=(int(self.cell_size * 0.72), int(self.cell_size * 0.72)),
            )
            surface.blit(arrow, arrow.get_rect(center=(cx, cy)))
            return
        points = [(cx, rect.top + 8), (rect.right - 10, cy), (cx + 8, cy), (cx + 8, rect.bottom - 8),
                  (cx - 8, rect.bottom - 8), (cx - 8, cy), (rect.left + 10, cy)]
        pygame.draw.polygon(surface, (250, 240, 120), points)
        pygame.draw.polygon(surface, (38, 72, 32), points, 3)

    def _draw_current_overlay(self, surface, pos):
        rect = pygame.Rect(
            self.grid_rect.left + pos[0] * self.cell_size,
            self.grid_rect.top + pos[1] * self.cell_size,
            self.cell_size,
            self.cell_size,
        )
        self._overlay(surface, rect, (*C.COL_HIGHLIGHT_PURPLE, 180))
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(surface, C.COL_HIGHLIGHT_PURPLE, inner, 2, border_radius=4)

    def _should_draw_hill_climbing_table(self):
        return self.game_state.level == 2 and self.algorithm_name in HILL_CLIMBING_ALGORITHMS

    def _record_hill_climbing_step(self, step):
        current = step.get("current")
        current_h = self.grid.heuristic_value(*current) if self.grid and current else None
        scores = step.get("neighbor_scores", {})
        improving = set(step.get("improving_neighbors", []))
        chosen = step.get("chosen") or (step.get("candidate") if step.get("loop") else None)
        phase = step.get("phase")
        decision = step.get("decision")

        def append_row(next_pos, action):
            next_h = scores.get(next_pos) if next_pos is not None else None
            self.hill_trace_rows.append({
                "current": current,
                "next": next_pos,
                "current_h": current_h,
                "next_h": next_h,
                "action": action,
            })

        if self.algorithm_name == "Hill Climbing":
            candidate = step.get("candidate")
            action = {
                "reject": "LOẠI",
                "accept": "NHẬN",
                "loop": "LOOP",
                "stuck": "KẸT",
            }.get(decision, "XÉT")
            append_row(candidate, action)

        elif self.algorithm_name == "Steepest Ascent HC":
            if phase == "evaluate_all":
                for pos in scores:
                    append_row(pos, "ỨNG VIÊN" if pos in improving else "LOẠI")
            elif decision in {"best", "loop"} and chosen is not None:
                updated = False
                for row in reversed(self.hill_trace_rows):
                    if row["current"] == current and row["next"] == chosen:
                        row["action"] = "LOOP" if decision == "loop" else "CHỌN TỐT NHẤT"
                        updated = True
                        break
                if not updated:
                    append_row(chosen, "LOOP" if decision == "loop" else "CHỌN TỐT NHẤT")
            elif decision == "stuck":
                append_row(None, "KẸT")

        else:  # Stochastic HC
            for pos in scores:
                if pos == chosen:
                    action = "LOOP" if decision == "loop" else "RANDOM → NHẬN"
                elif pos in improving:
                    action = "TRONG TẬP"
                else:
                    action = "LOẠI"
                append_row(pos, action)
            if not scores and decision == "stuck":
                append_row(None, "KẸT")

        self.hill_trace_rows = self.hill_trace_rows[-12:]

    def _draw_hill_climbing_table(self, surface):
        panel = pygame.Rect(C.DIALOG_PANEL_RECT)
        draw_wood_panel(surface, panel, border=5, corner=10, fill=(34, 28, 20))
        inner = panel.inflate(-14, -12)
        header_h = 20
        status_h = 16
        split_x = inner.centerx

        pygame.draw.rect(surface, (232, 224, 198), inner, border_radius=3)
        pygame.draw.rect(surface, C.COL_WOOD_DARK, inner, 2, border_radius=3)
        pygame.draw.line(surface, C.COL_WOOD_DARK, (split_x, inner.top), (split_x, inner.bottom - status_h), 2)
        pygame.draw.line(surface, C.COL_WOOD_DARK, (inner.left, inner.top + header_h), (inner.right, inner.top + header_h), 2)
        pygame.draw.line(surface, C.COL_WOOD_DARK, (inner.left, inner.bottom - status_h), (inner.right, inner.bottom - status_h), 1)

        draw_text(surface, "Current Node", (inner.left + 10, inner.top + 2), size=13, color=C.COL_BLACK, shadow=False)
        draw_text(surface, "Next Node", (split_x + 10, inner.top + 2), size=13, color=C.COL_BLACK, shadow=False)

        rows = self.hill_trace_rows[-4:]
        content_top = inner.top + header_h
        content_bottom = inner.bottom - status_h
        row_h = max(12, (content_bottom - content_top) // 4)
        for index, row in enumerate(rows):
            y = content_top + index * row_h
            if index:
                pygame.draw.line(surface, (150, 136, 110), (inner.left, y), (inner.right, y), 1)
            current_text = self._hill_node_text(row.get("current"), row.get("current_h"))
            next_text = self._hill_node_text(row.get("next"), row.get("next_h"))
            action = row.get("action", "")
            if action:
                next_text = f"{next_text}  |  {action}"
            action_color = (150, 35, 35) if action in {"LOẠI", "LOOP", "KẸT"} else (24, 100, 45)
            draw_text(surface, current_text, (inner.left + 10, y + 1), size=10, color=C.COL_BLACK, shadow=False)
            draw_text(surface, next_text, (split_x + 10, y + 1), size=10,
                      color=action_color if action else C.COL_BLACK, shadow=False)

        status = self.hill_status_message
        if not status:
            status = {
                "Hill Climbing": "Simple: xét từng neighbor; tốt hơn thì NHẬN, ngược lại LOẠI.",
                "Steepest Ascent HC": "Steepest: bật sáng toàn bộ neighbor rồi chọn h(n) nhỏ nhất.",
                "Stochastic HC": "Stochastic: random trong tập neighbor có h(n) tốt hơn.",
            }.get(self.algorithm_name, "")
        draw_text(surface, status, (inner.left + 8, inner.bottom - status_h + 2), size=9,
                  color=C.COL_BLACK, max_width=inner.width - 16, shadow=False)

    def _hill_node_text(self, pos, score):
        if pos is None:
            return "-"
        label = self._node_label(pos)
        if score is None and self.grid is not None:
            score = self.grid.heuristic_value(*pos)
        return f"{label}  h={score:.0f}" if score is not None else label

    def _should_draw_blind_search_table(self):
        return (
            self.game_state.level in {0, 1}
            and self.algorithm_name in TRACE_TABLE_ALGORITHMS
            and bool(self.search_trace_rows)
        )

    def _record_blind_search_step(self, step):
        self.last_search_step = step
        self.search_trace_rows.append({
            "node": step.get("current"),
            "frontier": list(step.get("frontier", [])),
            "reached": list(step.get("expanded", step.get("reached_order", step.get("visited", [])))),
            "depth_limit": step.get("depth_limit"),
            "restarting": step.get("restarting", False),
            "children": list(step.get("children", [])),
            "added_children": list(step.get("added_children", [])),
            "scores": dict(step.get("scores", {})),
        })
        self.search_trace_rows = self.search_trace_rows[-4:]

    def _store_algorithm_progress_step(self, step):
        if self.algorithm_history_index < len(self.algorithm_history) - 1:
            self.algorithm_history = self.algorithm_history[:self.algorithm_history_index + 1]
        self.algorithm_history.append(step)
        self.algorithm_history_index = len(self.algorithm_history) - 1

    def _restore_algorithm_progress(self, index):
        if not self.algorithm_history:
            return
        self.algorithm_history_index = max(0, min(index, len(self.algorithm_history) - 1))
        step = self.algorithm_history[self.algorithm_history_index]
        self.follow_path = []
        self.searching = True
        self.finished = False
        restore_pos = self.search_start_pos or self.grid.start
        self.player.place_at_grid(*restore_pos, self.grid_rect.topleft, self.cell_size)
        self.player._tween_x = None
        self.player._tween_y = None
        self.player.state = "idle"
        self.current = step.get("current") or restore_pos
        self.frontier = set(step.get("frontier", []))
        if self.game_state.level == 1 and self.algorithm_name in INFORMED_SEARCH_ALGORITHMS:
            self.visited = set(step.get("expanded", []))
        else:
            self.visited = set(step.get("visited", self.visited))
        self.final_path = list(step.get("path") or [])
        self.depth_limit = step.get("depth_limit", self.depth_limit)
        self.restarting = step.get("restarting", False)
        self.last_search_step = step
        self._apply_score_snapshot(step.get("scores", {}))
        self.search_trace_rows = []
        for old_step in self.algorithm_history[max(0, self.algorithm_history_index - 3):self.algorithm_history_index + 1]:
            self._record_blind_search_step(old_step)
        self.dialogue.set_status(f"Buoc {self.algorithm_history_index + 1}/{len(self.algorithm_history)}")

    def _apply_score_snapshot(self, scores):
        if self.grid is None:
            return
        self._clear_algorithm_scores()
        for pos, data in scores.items():
            if pos not in self.grid.cells:
                continue
            cell = self.grid.cells[pos]
            cell.g = data.get("g", 0)
            cell.h = data.get("h", 0)
            cell.f = data.get("f", 0)

    def _draw_blind_search_table(self, surface):
        panel = pygame.Rect(C.DIALOG_PANEL_RECT)
        draw_wood_panel(surface, panel, border=5, corner=10, fill=(34, 28, 20))
        inner = panel.inflate(-14, -12)
        header_h = 20
        col_w = [122, 380, inner.width - 122 - 380]
        x0 = inner.left
        x1 = x0 + col_w[0]
        x2 = x1 + col_w[1]

        pygame.draw.rect(surface, (232, 224, 198), inner, border_radius=3)
        pygame.draw.rect(surface, C.COL_WOOD_DARK, inner, 2, border_radius=3)
        for x in (x1, x2):
            pygame.draw.line(surface, C.COL_WOOD_DARK, (x, inner.top), (x, inner.bottom), 2)
        pygame.draw.line(surface, C.COL_WOOD_DARK, (inner.left, inner.top + header_h), (inner.right, inner.top + header_h), 2)

        headers = ("Node", "Frontier", "Reached")
        xs = (x0 + 8, x1 + 8, x2 + 8)
        for text, x in zip(headers, xs):
            draw_text(surface, text, (x, inner.top + 2), size=13, color=C.COL_BLACK, shadow=False)

        rows = self.search_trace_rows[-2:]
        detail_h = 16
        row_h = (inner.height - header_h - detail_h) // max(1, len(rows))
        y = inner.top + header_h
        for row in rows:
            pygame.draw.line(surface, (110, 96, 70), (inner.left, y), (inner.right, y), 1)
            self._draw_search_table_text(surface, self._trace_node_text(row), (x0 + 8, y + 4), col_w[0] - 14)
            self._draw_search_table_text(surface, self._node_list_text(row["frontier"], frontier=True, scores=row.get("scores")), (x1 + 8, y + 4), col_w[1] - 14)
            self._draw_search_table_text(surface, self._node_list_text(row["reached"], reached=True, scores=row.get("scores")), (x2 + 8, y + 4), col_w[2] - 14)
            y += row_h

        if self.last_search_step:
            detail = self._blind_step_detail(self.last_search_step)
            draw_text(surface, detail, (inner.left + 10, inner.bottom - 14), size=10,
                      color=C.COL_BLACK, max_width=inner.width - 20, shadow=False)

    def _draw_search_table_text(self, surface, text, pos, max_width):
        draw_text(surface, text, pos, size=11, color=C.COL_BLACK,
                  max_width=max_width, shadow=False)

    def _trace_node_text(self, row):
        if row["restarting"]:
            return f"IDS d={row['depth_limit']}"
        if self.algorithm_name in INFORMED_SEARCH_ALGORITHMS:
            return self._scored_node_label(row["node"], row.get("scores", {}))
        return self._node_label(row["node"])

    def _node_list_text(self, values, frontier=False, reached=False, scores=None):
        if not values:
            return "{ }" if frontier else "[ ]"
        if frontier and self.algorithm_name in {"DFS", "IDS"}:
            # Stack top is the rightmost item internally; display it first.
            values = list(reversed(values))
        if self.algorithm_name in INFORMED_SEARCH_ALGORITHMS:
            scores = scores or {}
            labels = [self._scored_node_label(pos, scores) for pos in values]
            limit = 7
        else:
            labels = [self._node_label(pos) for pos in values]
            limit = 12
        open_char, close_char = ("{", "}") if frontier else ("[", "]")
        text = ", ".join(labels[:limit])
        if len(labels) > limit:
            text += ", ..."
        return f"{open_char}{text}{close_char}"

    def _blind_step_detail(self, step):
        if self.algorithm_name in INFORMED_SEARCH_ALGORITHMS:
            return self._informed_step_detail(step)
        current = self._node_label(step.get("current"))
        children = [self._node_label(pos) for pos in step.get("children", [])]
        added = [self._node_label(pos) for pos in step.get("added_children", [])]
        structure = "queue" if self.algorithm_name == "BFS" else "stack"
        if self.algorithm_name == "IDS":
            structure = f"stack, depth={step.get('depth_limit')}"
        children_text = ", ".join(children) if children else "khong co"
        added_text = ", ".join(added) if added else "khong them moi"
        return f"Mo rong {current}; sinh con L,R,U,D: {children_text}; them vao {structure}: {added_text}."

    def _informed_step_detail(self, step):
        scores = step.get("scores", {})
        current = step.get("current")
        current_text = self._full_score_label(current, scores)
        children = [self._full_score_label(pos, scores) for pos in step.get("children", [])]
        added = [self._full_score_label(pos, scores) for pos in step.get("added_children", [])]
        priority = {"UCS": "g(n)", "Greedy": "h(n)", "A*": "f(n)"}.get(self.algorithm_name, "f(n)")
        children_text = ", ".join(children) if children else "khong co"
        added_text = ", ".join(added) if added else "khong them moi"
        return (
            f"{self.algorithm_name} uu tien {priority}. Current {current_text}. "
            f"Sinh L,R,U,D: {children_text}. Frontier them/cap nhat: {added_text}."
        )

    def _scored_node_label(self, pos, scores):
        label = self._node_label(pos)
        data = scores.get(pos)
        if not data:
            return label
        key = {"UCS": "g", "Greedy": "h", "A*": "f"}.get(self.algorithm_name, "f")
        return f"{label} {key}={data.get(key, 0):.0f}"

    def _full_score_label(self, pos, scores):
        label = self._node_label(pos)
        data = scores.get(pos)
        if not data:
            return label
        return (
            f"{label}(g={data.get('g', 0):.0f},"
            f"h={data.get('h', 0):.0f},"
            f"f={data.get('f', 0):.0f})"
        )

    def _node_label(self, pos):
        if pos is None:
            return "-"
        if self.grid is not None:
            if pos == self.grid.start:
                return "S"
            if pos == self.grid.goal:
                return "G"
        col, row = pos
        index = row * self.grid.cols + col if self.grid is not None else row * 20 + col
        letters = []
        index += 1
        while index:
            index, rem = divmod(index - 1, 26)
            letters.append(chr(ord("A") + rem))
        return "".join(reversed(letters))

    def _draw_side_panel(self, surface):
        panel = C.SIDE_PANEL_RECT
        draw_wood_panel(surface, panel, border=5, corner=8, fill=(54, 32, 24))
        hill_panel = self.game_state.level == 2 and self.algorithm_name in HILL_CLIMBING_ALGORITHMS
        if hill_panel:
            current_h = self.grid.heuristic_value(*self.current) if self.grid and self.current else 0
            draw_text(surface, self.algorithm_name, (panel.centerx, panel.top + 12),
                      size=14, color=C.COL_GOLD_BRIGHT, align="center")
            draw_text(surface, f"Current: {self._node_label(self.current)} | h(n)={current_h:.0f}",
                      (panel.centerx, panel.top + 38), size=12,
                      color=C.COL_CREAM_TEXT, align="center", shadow=False)
            y = panel.top + 64
            for pos, score in sorted(self.neighbor_scores.items(), key=lambda item: item[1])[:2]:
                color = C.COL_GOLD_BRIGHT if pos == self.chosen else C.COL_CREAM_TEXT
                draw_text(surface, f"{self._node_label(pos)}: h(n)={score:.0f}",
                          (panel.left + 24, y), size=11, color=color, shadow=False)
                y += 18
        elif self.neighbor_scores:
            draw_text(surface, "DANH GIA", (panel.centerx, panel.top + 12),
                      size=15, color=C.COL_CREAM_TEXT, align="center")
            if self.algorithm_name in {"BFS", "DFS", "IDS"}:
                draw_text(surface, "KHONG CO HEURISTIC", (panel.centerx, panel.top + 34),
                          size=11, color=C.COL_CREAM_TEXT, align="center", shadow=False)
                if self.algorithm_name == "IDS" and self.depth_limit is not None:
                    label = f"Depth = {self.depth_limit}"
                    if self.restarting:
                        label += " (restart)"
                    draw_text(surface, label, (panel.centerx, panel.top + 52),
                              size=11, color=C.COL_CREAM_TEXT, align="center", shadow=False)
            else:
                draw_text(surface, "HEURISTIC LAN CAN", (panel.centerx, panel.top + 34),
                          size=11, color=C.COL_CREAM_TEXT, align="center", shadow=False)
                if self.algorithm_name in {"UCS", "Greedy", "A*"} and self.current and self.grid is not None:
                    current_cell = self.grid.get(*self.current)
                    if current_cell is not None:
                        draw_text(surface, f"g(n): {current_cell.g:.0f}",
                                  (panel.left + 22, panel.top + 34), size=12,
                                  color=C.COL_CREAM_TEXT)
                        draw_text(surface, f"h(n): {current_cell.h:.0f}",
                                  (panel.left + 112, panel.top + 34), size=12,
                                  color=C.COL_CREAM_TEXT)
                        draw_text(surface, f"f(n): {current_cell.f:.0f}",
                                  (panel.left + 202, panel.top + 34), size=12,
                                  color=C.COL_GOLD_BRIGHT)
            y = panel.top + 64
            if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                sorted_neighbors = sorted(self.neighbor_scores.items(), key=lambda item: item[1])
            else:
                sorted_neighbors = sorted(self.neighbor_scores.items(), key=lambda item: item[1], reverse=True)

            for pos, score in sorted_neighbors[:5]:
                color = C.COL_GOLD_BRIGHT if pos == self.chosen else C.COL_CREAM_TEXT
                if self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                    label = f"{self._node_label(pos)}: h(n)={score:.0f}"
                else:
                    label = f"{pos}: {score}"
                draw_text(surface, label, (panel.left + 22, y), size=13, color=color)
                y += 24
            if self.temperature is not None:
                draw_text(surface, f"Temp: {self.temperature:.1f}", (panel.left + 22, y + 4), size=12, color=C.COL_GOLD_BRIGHT)
        else:
            draw_text(surface, "LUA CHON KE TIEP", (panel.centerx, panel.top + 14),
                      size=14, color=C.COL_CREAM_TEXT, align="center")
            draw_text(surface, f"({self.algorithm_name})", (panel.centerx, panel.top + 38),
                      size=12, color=C.COL_GOLD_BRIGHT, align="center", shadow=False)
            if self.algorithm_name in {"BFS", "DFS", "IDS"}:
                draw_text(surface, "Blind search khong co heuristic.",
                          (panel.centerx, panel.top + 62), size=11,
                          color=C.COL_CREAM_TEXT, align="center", shadow=False)
            elif self.algorithm_name in {"UCS", "Greedy", "A*"}:
                draw_text(surface, "Heuristic / g/h/f se hien khi chay.",
                          (panel.centerx, panel.top + 62), size=11,
                          color=C.COL_CREAM_TEXT, align="center", shadow=False)
                if self.current and self.grid is not None:
                    current_cell = self.grid.get(*self.current)
                    if current_cell is not None:
                        draw_text(surface, f"g(n): {getattr(current_cell, 'g', 0):.0f}",
                                  (panel.left + 22, panel.top + 82), size=12,
                                  color=C.COL_CREAM_TEXT)
                        draw_text(surface, f"h(n): {getattr(current_cell, 'h', 0):.0f}",
                                  (panel.left + 112, panel.top + 82), size=12,
                                  color=C.COL_CREAM_TEXT)
                        draw_text(surface, f"f(n): {getattr(current_cell, 'f', 0):.0f}",
                                  (panel.left + 202, panel.top + 82), size=12,
                                  color=C.COL_GOLD_BRIGHT)
            elif self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
                current_h = self.grid.heuristic_value(*self.current) if self.grid and self.current else 0
                draw_text(surface, f"Current Node: {self._node_label(self.current)} | h(n)={current_h:.0f}",
                          (panel.centerx, panel.top + 62), size=11,
                          color=C.COL_CREAM_TEXT, align="center", shadow=False)
                draw_text(surface, "Chỉ vùng neighbor hiện tại được chiếu sáng.",
                          (panel.centerx, panel.top + 82), size=10,
                          color=C.COL_CREAM_TEXT, align="center", shadow=False)
            draw_text(surface, "Trang thai:", (panel.centerx, panel.top + 110),
                      size=14, color=C.COL_CREAM_TEXT, align="center")
            status = "Tu dong" if self.auto_play else "Tung buoc"
            draw_text(surface, status, (panel.centerx, panel.top + 134),
                      size=15, color=C.COL_GOLD_BRIGHT, align="center")

        if self.game_state.level != 0:
            health_ratio = max(0.0, min(1.0, self.game_state.current_health / max(1, self.game_state.max_health)))
            bar_rect = pygame.Rect(24, 20, 180, 16)
            pygame.draw.rect(surface, (70, 30, 20), bar_rect)
            fill_width = int(bar_rect.width * health_ratio)
            pygame.draw.rect(surface, (90, 180, 95) if health_ratio > 0.5 else (220, 120, 70), pygame.Rect(bar_rect.left, bar_rect.top, fill_width, bar_rect.height))
            pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, bar_rect, 2)
            draw_text(surface, f"Máu: {self.game_state.current_health}/{self.game_state.max_health}", (bar_rect.centerx, bar_rect.top - 10), size=11, color=C.COL_CREAM_TEXT, align="center")
        if self.game_state.level not in EDITABLE_MATRIX_LEVELS:
            draw_text(surface, "Mui ten: dieu khien", (panel.centerx, panel.bottom - 32),
                      size=12, color=C.COL_CREAM_TEXT, align="center")

        if self.return_button is not None:
            self.return_button.draw(surface)
        if self.back_button is not None:
            self.back_button.draw(surface)
        if self.progress_prev_button is not None:
            self.progress_prev_button.draw(surface)
        if self.progress_next_button is not None:
            self.progress_next_button.draw(surface)
        if self.progress_auto_button is not None:
            self.progress_auto_button.text = "STOP" if self.auto_play else "AUTO"
            self.progress_auto_button.draw(surface)
        if self.level4_toggle is not None:
            self.level4_toggle.draw(surface)
        if self.and_or_button is not None:
            self.and_or_button.draw(surface)
        if self.randomize_button is not None:
            self.randomize_button.draw(surface)
        if self.matrix_edit_button is not None:
            self.matrix_edit_button.text = "EDIT ON" if self.matrix_edit_mode else "EDIT"
            self.matrix_edit_button.draw(surface)
        if self.belief_button is not None:
            self.belief_button.draw(surface)

        for button in self.algorithm_buttons:
            button.enabled = not (button.text == self.algorithm_name and self.auto_play)
            button.draw(surface)
            if button.text == self.algorithm_name:
                pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, button.rect, 2, border_radius=6)

    def _should_draw_cell_value(self, cell):
        if self.game_state.level == 0:
            return False
        if self.game_state.level == 2 and self.algorithm_name in HILL_CLIMBING_ALGORITHMS:
            return cell.kind != "wall"
        return cell.kind not in ("start", "trophy", "wall")

    def _should_dim_level_one_cell(self, pos):
        # Level 1 (blind) and Level 2 (informed) use the same light/dark
        # visualization: current node, frontier and reached stay lit.
        if self.game_state.level not in {0, 1} or self.algorithm_name not in TRACE_TABLE_ALGORITHMS:
            return False
        if not self.last_search_step:
            return False
        lit = set(self.last_search_step.get("expanded", self.last_search_step.get("reached_order", [])))
        lit.update(self.last_search_step.get("frontier", []))
        if self.current is not None:
            lit.add(self.current)
        lit.update(self.final_path)
        return pos not in lit

    def _cell_color(self, kind, value=None):
        special = {
            "wall": C.COL_WALL_STONE,
            "start": (244, 218, 126),
            "trophy": (210, 184, 96),
            "danger": C.COL_DANGER_RED,
            "fire": (120, 48, 36),
        }
        if kind in special:
            return special[kind]
        if value is not None:
            if value > 0:
                return (110, 180, 110)
            if value == 0:
                return C.COL_SILVER
            return C.COL_DANGER_RED
        return {
            "grass": C.COL_GRASS_LIGHT,
            "path": C.COL_PATH_GREY,
        }.get(kind, C.COL_GRASS_DARK)

    def _overlay(self, surface, rect, color):
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill(color)
        surface.blit(overlay, rect.topleft)
