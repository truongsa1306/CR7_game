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


LEVEL_LAYOUTS = {
    0: {
        "start": (0, 2),
        "goal": (8, 0),
        "path": [(1, 2), (2, 2), (2, 1), (3, 1), (4, 1), (5, 1), (5, 2), (5, 3), (6, 3), (7, 3)],
        "danger": [(6, 1), (7, 1), (8, 1), (6, 4), (7, 4)],
        "fire": [(7, 0), (7, 2), (8, 2)],
        "wall": [(3, 3), (4, 3)],
        "fog": True,
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
        self.belief_button = None
        self.and_or_button = None
        self.back_button = None
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

    def on_enter(self, **kwargs):
        if self.game_state.level == 4:
            self.manager.change(C.STATE_CARO)
            return

        self.finished = False
        self.auto_play = True
        self.step_timer = 0.0
        self.depth_limit = None
        self.restarting = False
        self.player.set_kit(self.game_state.kit_index)
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
        if self.belief_button is not None:
            self.belief_button.handle_event(event)
        if self.and_or_button is not None:
            self.and_or_button.handle_event(event)
        if self.back_button is not None:
            self.back_button.handle_event(event)
        if self.level4_toggle is not None:
            self.level4_toggle.handle_event(event)
        for button in self.algorithm_buttons:
            button.handle_event(event)

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

        if self.follow_path and not self.player.is_moving:
            next_pos = self.follow_path.pop(0)
            if next_pos != (self.player.col, self.player.row):
                self._move_player(next_pos)
            if not self.follow_path:
                self.dialogue.set_status("")
            return

        if self.finished or self.player.is_moving or not self.dialogue.fully_revealed:
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
            top = panel.bottom - total_h - 12
            columns = 1
            btn_width = panel.width - 24

        self.randomize_button = None
        self.belief_button = None
        self.and_or_button = None
        self.back_button = Button(
            pygame.Rect(panel.left + 12, panel.bottom - 3 * button_h - 2 * gap - 12, panel.width - 24, button_h),
            "BACK",
            font_size=11,
            on_click=self._back_to_level_select,
        )

        if self.game_state.level == 3 and self.level4_tab == 2:
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

        if name == self.algorithm_name:
            self.game_state.suggest_algorithm = None
            if not self.auto_play:
                self.auto_play = True
                self.step_timer = 0.0
            return

        if name not in ALGORITHM_FACTORIES:
            self.dialogue.set_status(f"Thuật toán {name} chưa hỗ trợ")
            return

        self.algorithm_name = name
        self.game_state.suggest_algorithm = None
        start_pos = self.current if self.current is not None else (self.player.col, self.player.row)
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

        self.visited = {self.current} if self.current is not None else set()
        self.frontier = set()
        self.final_path = []
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.algorithm_health = self.game_state.current_health
        self.finished = False
        self.auto_play = True
        self.step_timer = 0.0
        self.dialogue.set_status(f"Đang chạy {name}...")

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
            and self.dialogue.fully_revealed
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
        if self.game_state.level == 2:
            self._randomize_value_cells(self.grid)
        self.grid_rect, self.cell_size = self._grid_geometry(self.grid.cols, self.grid.rows)
        self.player.place_at_grid(*self.grid.start, self.grid_rect.topleft, self.cell_size)
        if self.game_state.level not in {2, 3}:
            self.grid.reveal_around(*self.grid.start, radius=1)
        self.visited = {self.grid.start}
        self.frontier = set()
        self.final_path = []
        self.follow_path = []
        self.current = self.grid.start
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
        self.and_or_dark = False
        self.and_or_branch = set()
        self.and_or_goal = None
        self.and_or_path = []
        self.and_or_choices = set()
        self.and_or_selected_choice = None
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

    def _advance_algorithm(self):
        if self.finished or self.player.is_moving or self.generator is None:
            return
        try:
            step = next(self.generator)
        except StopIteration:
            self._go_gameover("stuck")
            return
        except Exception as exc:
            self.generator = None
            self.auto_play = False
            self.searching = False
            self.dialogue.set_status(f"Thuật toán dừng do lỗi: {exc}")
            print(f"[Gameplay] algorithm step failed: {exc}")
            return

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
            elif self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
                self.frontier = set(self.neighbor_scores.keys())
                self.visited = set()
            else:
                self.frontier = set(step.get("frontier", []))
                self.visited = set(step.get("visited", self.visited))

            if self.algorithm_name == "IDS" and self.depth_limit is not None:
                label = f"IDS depth={self.depth_limit}"
                if self.restarting:
                    label += " (restart)"
                self.dialogue.set_status(label)

            if self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
                self._set_hill_climbing_dialogue(step)

            if step.get("stuck"):
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

            if self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
                if self.chosen and self.chosen != (self.player.col, self.player.row):
                    self.searching = False
                    self.follow_path = [self.chosen]
                    self.auto_play = False
                    self.step_timer = 0.0
                    self.dialogue.set_status("Đã chọn hành động. CR7 sẽ di chuyển.")
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
        self._randomize_value_cells(self.grid)
        self.grid.reveal_around(*self.grid.start, radius=1)
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
        chosen = step.get("chosen")
        current_score = self.grid.heuristic_value(*self.current) if self.grid and self.current else None
        chosen_score = self.grid.heuristic_value(*chosen) if self.grid and chosen else None
        if chosen is None:
            if current_score is None:
                message = "Đang kiểm tra ô..."
            else:
                message = f"Không có ô nào có chi phí thấp hơn {current_score:.0f}, đang tìm hướng khác."
        elif self.algorithm_name == "Hill Climbing":
            message = (
                f"Ô {chosen} tốt hơn vì h(n)={chosen_score:.0f} < {current_score:.0f}. "
                "Chọn ô này và di chuyển."
            )
        elif self.algorithm_name == "Steepest Ascent HC":
            message = (
                f"Ô {chosen} là ô tốt nhất trong các láng giềng với h(n)={chosen_score:.0f}. "
                "Chọn ô tối ưu nhất."
            )
        else:
            neighbors = sorted(step.get("neighbor_scores", {}).items(), key=lambda item: item[1])
            neighbor_text = ", ".join(f"{pos}:{score:.0f}" for pos, score in neighbors[:4])
            message = (
                f"Stochastic HC xem xét: {neighbor_text}. "
                f"Ngẫu nhiên chọn {chosen} với h(n)={chosen_score:.0f}."
            )
        self.dialogue.set_text(message, kit_index=self.game_state.kit_index)

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
        health_delta = self.grid.health_delta(*pos)
        if self.game_state.current_health + health_delta < 0:
            return False
        self.player.move_to_grid(pos[0], pos[1], self.grid_rect.topleft, self.cell_size)
        self.current = pos
        self.game_state.current_health += health_delta
        self.algorithm_health = self.game_state.current_health
        if self.game_state.level != 3:
            self.grid.reveal_around(*pos, radius=1)
        if cell.kind in ("danger", "fire"):
            AudioManager.instance().play_sfx("danger_trigger", volume=0.8)
        else:
            AudioManager.instance().play_sfx("cell_step", volume=0.7)
        if pos == self.grid.goal:
            self._finish_level()
        return True

    def _finish_level(self):
        self.finished = True
        if self.game_state.level >= max(C.LEVEL_NAMES.keys()):
            self.manager.change(C.STATE_VICTORY)
            return
        self.game_state.advance_level()
        self.manager.change(C.STATE_LEVELUP)

    def _go_gameover(self, reason):
        self.finished = True
        self.game_state.gameover_reason = reason
        if reason == "stuck":
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

        if pos in self.frontier and self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
            self._overlay(surface, rect, (*C.COL_FRONTIER, 100))
        elif pos in self.visited:
            self._overlay(surface, rect, (*C.COL_VISITED, 75))
        if pos in self.final_path:
            self._overlay(surface, rect, (*C.COL_PATH_FINAL, 120))

        if cell.kind not in ("start", "trophy", "wall"):
            label = str(cell.cost)
            text_color = C.COL_BLACK if cell.kind == "path" and cell.value is None else C.COL_CREAM_TEXT
            draw_text(surface, label, (rect.centerx, rect.centery - 11), size=18,
                      color=text_color, align="center")

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

        if not cell.revealed and self.game_state.level == 3:
            if pos not in (self.grid.start, self.grid.goal):
                draw_text(surface, "?", rect.center, size=24, color=C.COL_CREAM_TEXT, align="center")
        elif self.algorithm_name in {"BFS", "DFS", "IDS"}:
            if cell.kind not in ("start", "trophy", "wall"):
                draw_text(surface, "0", (rect.centerx, rect.centery - 11), size=16,
                          color=C.COL_CREAM_TEXT, align="center")
        elif cell.kind not in ("start", "trophy", "wall"):
            label = str(cell.cost)
            draw_text(surface, label, (rect.centerx, rect.centery - 11), size=16,
                      color=C.COL_CREAM_TEXT, align="center")

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

        if self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
            if pos not in self.frontier and pos != self.current and pos != self.chosen and pos not in self.final_path:
                self._overlay(surface, rect, (0, 0, 0, 150))

        if self.level4_tab == 2 and pos == self.current:
            self._overlay(surface, rect, (*C.COL_HIGHLIGHT_PURPLE, 180))

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

    def _draw_side_panel(self, surface):
        panel = C.SIDE_PANEL_RECT
        draw_wood_panel(surface, panel, border=5, corner=8, fill=(54, 32, 24))
        if self.neighbor_scores:
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
            if self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
                sorted_neighbors = sorted(self.neighbor_scores.items(), key=lambda item: item[1])
            else:
                sorted_neighbors = sorted(self.neighbor_scores.items(), key=lambda item: item[1], reverse=True)

            for pos, score in sorted_neighbors[:5]:
                color = C.COL_GOLD_BRIGHT if pos == self.chosen else C.COL_CREAM_TEXT
                draw_text(surface, f"{pos}: {score}", (panel.left + 22, y), size=13, color=color)
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
            elif self.algorithm_name in {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}:
                draw_text(surface, "Hill climbing dung heuristic local search.",
                          (panel.centerx, panel.top + 62), size=11,
                          color=C.COL_CREAM_TEXT, align="center", shadow=False)
            draw_text(surface, "Trang thai:", (panel.centerx, panel.top + 110),
                      size=14, color=C.COL_CREAM_TEXT, align="center")
            status = "Tu dong" if self.auto_play else "Tung buoc"
            draw_text(surface, status, (panel.centerx, panel.top + 134),
                      size=15, color=C.COL_GOLD_BRIGHT, align="center")

        health_ratio = max(0.0, min(1.0, self.game_state.current_health / max(1, self.game_state.max_health)))
        bar_rect = pygame.Rect(24, 20, 180, 16)
        pygame.draw.rect(surface, (70, 30, 20), bar_rect)
        fill_width = int(bar_rect.width * health_ratio)
        pygame.draw.rect(surface, (90, 180, 95) if health_ratio > 0.5 else (220, 120, 70), pygame.Rect(bar_rect.left, bar_rect.top, fill_width, bar_rect.height))
        pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, bar_rect, 2)
        draw_text(surface, f"Máu: {self.game_state.current_health}/{self.game_state.max_health}", (bar_rect.centerx, bar_rect.top - 10), size=11, color=C.COL_CREAM_TEXT, align="center")
        draw_text(surface, "Mui ten: dieu khien", (panel.centerx, panel.bottom - 32),
                  size=12, color=C.COL_CREAM_TEXT, align="center")

        if self.back_button is not None:
            self.back_button.draw(surface)
        if self.level4_toggle is not None:
            self.level4_toggle.draw(surface)
        if self.and_or_button is not None:
            self.and_or_button.draw(surface)
        if self.randomize_button is not None:
            self.randomize_button.draw(surface)
        if self.belief_button is not None:
            self.belief_button.draw(surface)

        for button in self.algorithm_buttons:
            button.enabled = not (button.text == self.algorithm_name and self.auto_play)
            button.draw(surface)
            if button.text == self.algorithm_name:
                pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, button.rect, 2, border_radius=6)

    def _cell_color(self, kind, value=None):
        if value is not None:
            if value > 0:
                return (110, 180, 110)
            if value == 0:
                return C.COL_PATH_GREY
            if value <= -4:
                return C.COL_DANGER_RED
            return C.COL_SILVER
        return {
            "grass": C.COL_GRASS_LIGHT,
            "path": C.COL_PATH_GREY,
            "danger": C.COL_DANGER_RED,
            "fire": (120, 48, 36),
            "wall": C.COL_WALL_STONE,
            "start": (244, 218, 126),
            "trophy": (210, 184, 96),
        }.get(kind, C.COL_GRASS_DARK)

    def _overlay(self, surface, rect, color):
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill(color)
        surface.blit(overlay, rect.topleft)
