"""
scenes/gameplay_scene.py
========================
Interactive grid/tutorial scene from the spec. It renders the stadium UI
layout at 1024x576, visualizes the selected search algorithm step by step,
spends energy when CR7 moves across cells, and transitions to LevelUp,
GameOver, or Victory scenes.
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
from ui.button import Button
from ui.dialogue_box import DialogueBox
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_stadium_background, draw_wood_panel


ALGORITHM_FACTORIES = {
    "BFS": bfs_steps,
    "DFS": dfs_steps,
    "IDS": ids_steps,
    "UCS": ucs_steps,
    "Greedy": greedy_steps,
    "A*": astar_steps,
    "Hill Climbing": simple_hill_climbing_steps,
    "Steepest Ascent HC": steepest_ascent_hill_climbing_steps,
    "Stochastic HC": lambda grid: stochastic_hill_climbing_steps(grid, random.Random(17)),
    "Simulated Annealing": lambda grid: simulated_annealing_steps(grid, rng=random.Random(23)),
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
        self.visited = set()
        self.frontier = set()
        self.final_path = []
        self.current = None
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.auto_play = True
        self.step_timer = 0.0
        self.finished = False

    def on_enter(self, **kwargs):
        self.finished = False
        self.auto_play = True
        self.step_timer = 0.0
        self.player.set_kit(self.game_state.kit_index)
        self.dialogue.set_text(C.LEVEL_INTRO_LINES[self.game_state.level], kit_index=self.game_state.kit_index)

        algorithms = C.LEVEL_ALGORITHMS[self.game_state.level]
        suggested = self.game_state.suggest_algorithm
        self.algorithm_name = suggested if suggested in algorithms else algorithms[0]
        self.game_state.suggest_algorithm = None
        self._create_algorithm_buttons()
        self._reset_algorithm_run(reset_energy=False)
        AudioManager.instance().play_bgm("gameplay_search", volume=0.42)

    def handle_event(self, event):
        self.dialogue.handle_event(event)
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
        algorithms = C.LEVEL_ALGORITHMS[self.game_state.level]
        panel = C.SIDE_PANEL_RECT
        button_h = 28
        gap = 5
        total_h = len(algorithms) * button_h + (len(algorithms) - 1) * gap
        top = panel.bottom - total_h - 12
        self.algorithm_buttons = []
        for i, name in enumerate(algorithms):
            rect = pygame.Rect(panel.left + 12, top + i * (button_h + gap), panel.width - 24, button_h)
            self.algorithm_buttons.append(Button(rect, name, font_size=11, on_click=lambda n=name: self._select_algorithm(n)))

    def _select_algorithm(self, name):
        if name == self.algorithm_name:
            return
        self.algorithm_name = name
        self.game_state.restart_level()
        self._reset_algorithm_run(reset_energy=False)

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
        self.grid = self._build_grid(self.game_state.level)
        self.grid_rect, self.cell_size = self._grid_geometry(self.grid.cols, self.grid.rows)
        self.player.place_at_grid(*self.grid.start, self.grid_rect.topleft, self.cell_size)
        self.grid.reveal_around(*self.grid.start, radius=1)
        self.visited = {self.grid.start}
        self.frontier = set()
        self.final_path = []
        self.current = self.grid.start
        self.neighbor_scores = {}
        self.chosen = None
        self.temperature = None
        self.finished = False
        self.auto_play = True
        self.step_timer = 0.0
        self.generator = ALGORITHM_FACTORIES[self.algorithm_name](self.grid)

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
        grid.reveal_around(*grid.start, radius=1)
        return grid

    def _grid_geometry(self, cols, rows):
        cell = min(C.GRID_CELL_SIZE, C.GRID_RECT.width // cols, C.GRID_RECT.height // rows)
        rect = pygame.Rect(C.GRID_ORIGIN[0], C.GRID_ORIGIN[1], cols * cell, rows * cell)
        return rect, cell

    def _on_dialogue_advance(self):
        if not self.dialogue.fully_revealed:
            return
        self.auto_play = False
        self._advance_algorithm()

    def _advance_algorithm(self):
        if self.finished or self.player.is_moving:
            return
        try:
            step = next(self.generator)
        except StopIteration:
            self._go_gameover("stuck")
            return

        self.current = step.get("current") or self.current
        self.frontier = set(step.get("frontier", []))
        self.visited = set(step.get("visited", self.visited))
        self.neighbor_scores = step.get("neighbor_scores", {})
        self.chosen = step.get("chosen")
        self.temperature = step.get("temperature")

        if step.get("stuck"):
            self._go_gameover("stuck")
            return

        path = step.get("path")
        if path is not None:
            self.final_path = path
            if path:
                self._finish_level()
            else:
                self._go_gameover("stuck")
            return

        move_target = self.chosen or self.current
        if move_target and move_target != (self.player.col, self.player.row):
            self._move_player(move_target)

    def _move_player(self, pos):
        if self.grid is None:
            return

        if not self._is_orthogonal_step(pos):
            next_step = self._next_step_towards(pos)
            if next_step is None:
                return
            pos = next_step

        cell = self.grid.get(*pos)
        if cell is None or not cell.passable:
            return
        self.player.move_to_grid(pos[0], pos[1], self.grid_rect.topleft, self.cell_size)
        self.current = pos
        self.grid.reveal_around(*pos, radius=1)
        cost = cell.cost or 0
        if cost < 0:
            self.game_state.spend_energy(abs(cost))
        if cell.kind in ("danger", "fire"):
            AudioManager.instance().play_sfx("danger_trigger", volume=0.8)
        else:
            AudioManager.instance().play_sfx("cell_step", volume=0.7)
        if pos == self.grid.goal:
            self._finish_level()
        elif self.game_state.energy <= 0:
            self._go_gameover("energy")

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
        draw_wood_panel(surface, C.HEADER_ENERGY_RECT, border=4, corner=8, fill=(58, 36, 26))
        coin_center = (C.HEADER_ENERGY_RECT.left + 25, C.HEADER_ENERGY_RECT.centery)
        pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, coin_center, 12)
        pygame.draw.circle(surface, C.COL_GOLD, coin_center, 12, 2)
        draw_text(surface, f"Ngan luong: {self.game_state.energy}", (C.HEADER_ENERGY_RECT.left + 48, C.HEADER_ENERGY_RECT.top + 9),
                  size=18, color=C.COL_CREAM_TEXT)

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
            pygame.draw.rect(surface, self._cell_color(cell.kind), mini)
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

        if self.chosen:
            self._draw_choice_arrow(surface, self.chosen)

        self.player.draw(surface)

    def _draw_cell(self, surface, rect, cell):
        pygame.draw.rect(surface, self._cell_color(cell.kind), rect)
        pygame.draw.rect(surface, (48, 72, 42), rect, 1)

        pos = (cell.col, cell.row)
        if pos in self.visited:
            self._overlay(surface, rect, (*C.COL_VISITED, 75))
        if pos in self.frontier:
            self._overlay(surface, rect, (*C.COL_FRONTIER, 90))
        if pos in self.final_path:
            self._overlay(surface, rect, (*C.COL_PATH_FINAL, 120))

        highlighted_pos = (self.player.col, self.player.row)
        if pos == highlighted_pos:
            pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, rect.center, max(8, min(rect.width, rect.height) // 2 - 4), 3)
        elif pos == self.current:
            pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, rect.inflate(-4, -4), 2)

        if cell.kind == "fire":
            self.fire.draw(surface, rect.inflate(-10, -8))
        elif cell.kind == "trophy":
            trophy = AssetManager.instance().get_image(
                "sprites/ui/trophy_worldcup.png",
                size=(int(self.cell_size * 0.75), int(self.cell_size * 0.85)),
                placeholder=placeholder_trophy,
            )
            surface.blit(trophy, trophy.get_rect(center=rect.center))

        if self.algorithm_name in {"BFS", "DFS", "IDS"}:
            if cell.kind not in ("start", "trophy", "wall"):
                draw_text(surface, "0", (rect.centerx, rect.centery - 11), size=16,
                          color=C.COL_CREAM_TEXT, align="center")
        elif cell.kind not in ("start", "trophy", "wall"):
            label = str(cell.cost)
            draw_text(surface, label, (rect.centerx, rect.centery - 11), size=16,
                      color=C.COL_CREAM_TEXT, align="center")

        if not cell.revealed:
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

    def _draw_side_panel(self, surface):
        panel = C.SIDE_PANEL_RECT
        draw_wood_panel(surface, panel, border=5, corner=8, fill=(54, 32, 24))
        if self.neighbor_scores:
            if self.algorithm_name in {"BFS", "DFS", "IDS"}:
                draw_text(surface, "DANH GIA", (panel.centerx, panel.top + 12),
                          size=15, color=C.COL_CREAM_TEXT, align="center")
                draw_text(surface, "KHONG CO HEURISTIC", (panel.centerx, panel.top + 34),
                          size=11, color=C.COL_CREAM_TEXT, align="center", shadow=False)
            else:
                draw_text(surface, "DANH GIA", (panel.centerx, panel.top + 12),
                          size=15, color=C.COL_CREAM_TEXT, align="center")
                draw_text(surface, "HEURISTIC LAN CAN", (panel.centerx, panel.top + 34),
                          size=11, color=C.COL_CREAM_TEXT, align="center", shadow=False)
            y = panel.top + 64
            for pos, score in sorted(self.neighbor_scores.items(), key=lambda item: item[1], reverse=True)[:5]:
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
            draw_text(surface, "Trang thai:", (panel.centerx, panel.top + 92),
                      size=14, color=C.COL_CREAM_TEXT, align="center")
            status = "Tu dong" if self.auto_play else "Tung buoc"
            draw_text(surface, status, (panel.centerx, panel.top + 116),
                      size=15, color=C.COL_GOLD_BRIGHT, align="center")

        draw_text(surface, "Mui ten: dieu khien", (panel.centerx, panel.bottom - 32),
                  size=12, color=C.COL_CREAM_TEXT, align="center")

        for button in self.algorithm_buttons:
            button.enabled = button.text != self.algorithm_name
            button.draw(surface)
            if button.text == self.algorithm_name:
                pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, button.rect, 2, border_radius=6)

    def _cell_color(self, kind):
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
