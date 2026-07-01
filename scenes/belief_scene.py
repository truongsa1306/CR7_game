"""Level 4: belief-state search on several possible maps at once."""
from __future__ import annotations

import copy
import math
import random

import pygame

import config as C
from entities.grid_cell import GridModel
from scenes.base_scene import BaseScene
from systems.algorithms.belief_search import (
    BLIND,
    HILL,
    INFORMED,
    belief_search_steps,
    heuristic_components,
    score_state,
)
from systems.asset_manager import AssetManager, placeholder_chibi, placeholder_trophy
from systems.audio_manager import AudioManager
from ui.button import Button, ToggleGroup
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_stadium_background, draw_wood_panel


ALGORITHM_GROUPS = (
    ("BFS", "DFS", "IDS"),
    ("UCS", "Greedy", "A*"),
    ("Hill Climbing", "Steepest Ascent HC", "Stochastic HC"),
)

OBSERVATION_LABELS = ("KHÔNG QS", "QS 1 PHẦN")
COUNT_OPTIONS = (2, 3, 4, 5, 6)

MAP_AREA = pygame.Rect(24, 76, 646, 336)
CONTROL_PANEL = pygame.Rect(688, 76, 312, 336)
TRACE_PANEL = pygame.Rect(24, 422, 976, 140)


class BeliefSearchScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.rng = random.Random()
        self.observation_mode = 0
        self.algorithm_group = 0
        self.algorithm_name = ALGORITHM_GROUPS[0][0]
        self.belief_count = 2

        self.worlds = []
        self.initial_state = ()
        self.current_state = ()
        self.current_score = None
        self.generator = None
        self.last_step = None
        self.trace_rows = []
        self.step_index = 0
        self.auto_play = False
        self.step_timer = 0.0
        self.finished = False
        self.history = []
        self.history_cursor = -1
        self.completed_worlds = set()
        self.status_message = "Chọn số lượng rồi nhấn RANDOM hoặc BELIEF +"

        self.mode_toggle = None
        self.group_toggle = None
        self.count_toggle = None
        self.algorithm_buttons = []
        self.belief_button = None
        self.random_button = None
        self.prev_button = None
        self.next_button = None
        self.auto_button = None
        self.back_button = None

    def on_enter(self, **kwargs):
        self.worlds = []
        self.initial_state = ()
        self.current_state = ()
        self.current_score = None
        self.generator = None
        self.last_step = None
        self.trace_rows = []
        self.step_index = 0
        self.auto_play = False
        self.step_timer = 0.0
        self.finished = False
        self.history = []
        self.history_cursor = -1
        self.completed_worlds = set()
        self.status_message = "Đang tạo tập belief ban đầu..."
        self._build_controls()
        self._randomize_preview()
        AudioManager.instance().play_bgm("gameplay_search", volume=0.42)

    # ------------------------------------------------------------------
    # Controls
    def _build_controls(self):
        panel = CONTROL_PANEL
        self.mode_toggle = ToggleGroup(
            pygame.Rect(panel.left + 12, panel.top + 12, panel.width - 24, 24),
            list(OBSERVATION_LABELS),
            on_select=self._select_observation_mode,
            font_size=10,
        )
        self.mode_toggle.selected = self.observation_mode

        self.group_toggle = ToggleGroup(
            pygame.Rect(panel.left + 12, panel.top + 44, panel.width - 24, 24),
            ["NHÓM 1", "NHÓM 2", "NHÓM 3"],
            on_select=self._select_algorithm_group,
            font_size=10,
        )
        self.group_toggle.selected = self.algorithm_group

        self.algorithm_buttons = []
        button_h = 24
        for index, name in enumerate(ALGORITHM_GROUPS[self.algorithm_group]):
            rect = pygame.Rect(
                panel.left + 12,
                panel.top + 76 + index * (button_h + 4),
                panel.width - 24,
                button_h,
            )
            self.algorithm_buttons.append(
                Button(rect, name, font_size=10, on_click=lambda value=name: self._select_algorithm(value))
            )

        self.count_toggle = ToggleGroup(
            pygame.Rect(panel.left + 12, panel.top + 164, panel.width - 24, 24),
            [str(value) for value in COUNT_OPTIONS],
            on_select=self._select_belief_count,
            font_size=11,
        )
        self.count_toggle.selected = COUNT_OPTIONS.index(self.belief_count)

        half = (panel.width - 28) // 2
        self.belief_button = Button(
            pygame.Rect(panel.left + 12, panel.top + 196, half, 24),
            f"BELIEF + ({self.belief_count})",
            font_size=10,
            on_click=self._create_belief_states,
        )
        self.random_button = Button(
            pygame.Rect(panel.left + 16 + half, panel.top + 196, half, 24),
            "RANDOM",
            font_size=10,
            on_click=self._randomize_preview,
        )
        nav_gap = 4
        nav_width = (panel.width - 24 - nav_gap * 2) // 3
        nav_y = panel.top + 228
        self.prev_button = Button(
            pygame.Rect(panel.left + 12, nav_y, nav_width, 24),
            "PREV",
            font_size=10,
            on_click=self._rewind_search,
        )
        self.next_button = Button(
            pygame.Rect(panel.left + 12 + nav_width + nav_gap, nav_y, nav_width, 24),
            "NEXT",
            font_size=10,
            on_click=self._advance_search,
        )
        self.auto_button = Button(
            pygame.Rect(
                panel.left + 12 + (nav_width + nav_gap) * 2,
                nav_y,
                panel.width - 24 - nav_width * 2 - nav_gap * 2,
                24,
            ),
            "AUTO",
            font_size=10,
            on_click=self._toggle_auto,
        )
        self.back_button = Button(
            pygame.Rect(panel.left + 12, panel.top + 260, panel.width - 24, 24),
            "BACK",
            font_size=10,
            on_click=self._back_to_level_select,
        )

    def handle_event(self, event):
        for control in (
            self.mode_toggle,
            self.group_toggle,
            self.count_toggle,
            self.belief_button,
            self.random_button,
            self.prev_button,
            self.next_button,
            self.auto_button,
            self.back_button,
        ):
            if control is not None:
                control.handle_event(event)
        for button in self.algorithm_buttons:
            button.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self._rewind_search()
            elif event.key == pygame.K_RIGHT:
                self._advance_search()
            elif event.key == pygame.K_a:
                self._toggle_auto()
            elif event.key == pygame.K_r:
                self._create_belief_states()
            elif event.key == pygame.K_ESCAPE:
                self._back_to_level_select()

    def update(self, dt):
        has_recorded_future = self.history_cursor < len(self.history) - 1
        if not self.auto_play or ((self.generator is None or self.finished) and not has_recorded_future):
            return
        self.step_timer += dt
        if self.step_timer >= 0.10:
            self.step_timer = 0.0
            # AUTO advances in small batches so BFS/UCS/IDS remain practical
            # with several simultaneous worlds; NEXT still shows every step.
            batch = 8 if self.algorithm_name in {"BFS", "IDS", "UCS", "A*"} else 2
            for _ in range(batch):
                has_recorded_future = self.history_cursor < len(self.history) - 1
                if (((self.generator is None or self.finished) and not has_recorded_future)
                        or not self.auto_play):
                    break
                self._advance_search()

    def _select_observation_mode(self, index):
        self.observation_mode = index
        self._clear_belief("Đang tạo lại tập belief theo chế độ quan sát mới...")
        self._build_controls()
        self._randomize_preview()

    def _select_algorithm_group(self, index):
        self.algorithm_group = index
        self.algorithm_name = ALGORITHM_GROUPS[index][0]
        self._build_controls()
        if self.worlds and self._belief_revealed():
            self._start_search()
        else:
            self.status_message = f"Đã chọn nhóm {index + 1}: {self.algorithm_name}"

    def _select_algorithm(self, name):
        self.algorithm_name = name
        if self.worlds and self._belief_revealed():
            self._start_search()
        else:
            self.status_message = f"Đã chọn {name}. Hãy RANDOM hoặc BELIEF +."

    def _select_belief_count(self, index):
        self.belief_count = COUNT_OPTIONS[index]
        if self.belief_button is not None:
            self.belief_button.text = f"BELIEF + ({self.belief_count})"
        self._randomize_preview()

    def _toggle_auto(self):
        has_recorded_future = self.history_cursor < len(self.history) - 1
        if (self.generator is None or self.finished) and not has_recorded_future:
            self.status_message = "Hãy nhấn BELIEF + trước khi chạy."
            return
        self.auto_play = not self.auto_play
        self.step_timer = 0.0
        self.status_message = "Đang chạy tự động" if self.auto_play else "Đã tạm dừng"

    def _back_to_level_select(self):
        self.game_state.suggest_algorithm = None
        self.manager.change(C.STATE_LEVEL_SELECT)

    # ------------------------------------------------------------------
    # Belief maps and search
    def _clear_belief(self, message):
        self.worlds = []
        self.initial_state = ()
        self.current_state = ()
        self.current_score = None
        self.generator = None
        self.last_step = None
        self.trace_rows = []
        self.auto_play = False
        self.finished = False
        self.history = []
        self.history_cursor = -1
        self.completed_worlds = set()
        self.status_message = message

    def _belief_revealed(self):
        return bool(self.worlds) and all(world.get("belief_revealed", False) for world in self.worlds)

    def _randomize_preview(self):
        self.worlds = [self._random_world(index) for index in range(self.belief_count)]
        self.initial_state = tuple(world["start"] for world in self.worlds)
        self.current_state = self.initial_state
        self.current_score = None
        self.generator = None
        self.last_step = None
        self.trace_rows = []
        self.step_index = 0
        self.auto_play = False
        self.step_timer = 0.0
        self.finished = False
        self.history = []
        self.history_cursor = -1
        if self.observation_mode == 0:
            self.status_message = (
                f"Đã tạo S={{{', '.join(f'M{i + 1}' for i in range(self.belief_count))}}} ở chế độ không quan sát. "
                "Toàn bộ ô đang ẩn bằng ?. Nhấn BELIEF + để khui hết và bắt đầu giải."
            )
        else:
            self.status_message = (
                f"Đã tạo S={{{', '.join(f'M{i + 1}' for i in range(self.belief_count))}}} ở chế độ quan sát một phần. "
                "RANDOM sẽ đảo vị trí ô số/? và có thể ẩn hoặc hiện nhân vật. Nhấn BELIEF + để khui hết."
            )

    def _create_belief_states(self):
        if not self.worlds:
            self._randomize_preview()
        for world in self.worlds:
            for cell in world["grid"].cells.values():
                cell.revealed = True
            world["actor_visible"] = True
            world["belief_revealed"] = True
        self.initial_state = tuple(world["start"] for world in self.worlds)
        self.current_state = self.initial_state
        self._start_search()
        self.status_message = (
            f"Đã khui S={{{', '.join(f'M{i + 1}' for i in range(self.belief_count))}}}. "
            "Nhấn NEXT hoặc AUTO để giải."
        )
        if self.history:
            self.history[-1]["status_message"] = self.status_message

    def _random_world(self, index):
        cols, rows = 4, 3
        goal = (cols - 1, 0)
        start = (self.rng.randrange(0, cols), self.rng.randrange(1, rows))
        if start == goal:
            start = (0, rows - 1)

        grid = GridModel(cols, rows, start, goal, fog=False)
        # Keep the topology open so every random belief set has a common
        # conformant plan. Randomness comes from starts, values and visibility.
        values = (-4, -2, 0, 2, 4)
        weights = (10, 16, 22, 24, 16)
        for pos, cell in grid.cells.items():
            value = self.rng.choices(values, weights=weights, k=1)[0]
            cell.value = value
            if value > 0:
                cell.kind = "path"
            elif value == 0:
                cell.kind = "grass"
            elif value >= -2:
                cell.kind = "danger"
            else:
                cell.kind = "fire"

        grid.set_kind(*start, "start")
        grid.get(*start).value = self.rng.choice((0, 2, 4))
        grid.set_kind(*goal, "trophy")
        grid.get(*goal).value = self.rng.choice((0, 2, 4))

        if self.observation_mode == 0:
            for cell in grid.cells.values():
                cell.revealed = False
            actor_visible = False
        else:
            for pos, cell in grid.cells.items():
                cell.revealed = pos == goal or self.rng.random() < 0.52
            actor_visible = self.rng.random() < 0.5

        return {
            "name": f"M{index + 1}",
            "grid": grid,
            "start": start,
            "actor_visible": actor_visible,
            "belief_revealed": False,
        }

    def _start_search(self):
        if not self.worlds:
            return
        grids = [world["grid"] for world in self.worlds]
        self.current_state = self.initial_state
        self.current_score = score_state(grids, self.current_state)
        self.generator = belief_search_steps(
            grids,
            self.initial_state,
            self.algorithm_name,
            rng=self.rng,
            max_depth=36,
        )
        self.last_step = None
        self.step_index = 0
        if self.algorithm_name in HILL:
            self.trace_rows = [
                {
                    "current": "S",
                    "next": "Chưa xét node kế tiếp",
                }
            ]
        else:
            belief_label = "S={" + ", ".join(
                f"M{i + 1}" for i in range(len(self.worlds))
            ) + "}"
            self.trace_rows = [
                {
                    "stt": "0",
                    "node": "-",
                    "frontier": "{S}",
                    "reached": "∅",
                }
            ]
        self.auto_play = False
        self.finished = False
        self.step_timer = 0.0
        self.status_message = f"{self.algorithm_name} đã sẵn sàng."
        self.completed_worlds = {i for i, (world, pos) in enumerate(zip(self.worlds, self.current_state)) if pos == world["grid"].goal}
        self.history = []
        self.history_cursor = -1
        self._record_history()

    def _advance_search(self):
        # When PREV was used, NEXT first replays already-computed snapshots.
        # The search generator stays at the newest computed step, so no node
        # is expanded twice and accumulated g(n) values remain correct.
        if self.history_cursor < len(self.history) - 1:
            self._restore_history(self.history_cursor + 1)
            return
        if self.finished:
            return
        if self.generator is None:
            self.status_message = "Hãy nhấn BELIEF + để tạo tập trạng thái."
            return
        try:
            step = next(self.generator)
        except StopIteration:
            self.generator = None
            self.auto_play = False
            self.status_message = "Thuật toán đã dừng."
            return
        except Exception as exc:
            self.generator = None
            self.auto_play = False
            self.status_message = f"Không thể tiếp tục: {exc}"
            print(f"[BeliefSearch] step failed: {exc}")
            return

        self.last_step = step
        raw_state = tuple(step.get("display_state", step.get("current_state", self.current_state)))
        frozen_state = []
        for idx, (world, pos) in enumerate(zip(self.worlds, raw_state)):
            goal = world["grid"].goal
            if idx in self.completed_worlds or pos == goal:
                frozen_state.append(goal)
                self.completed_worlds.add(idx)
            else:
                frozen_state.append(pos)
        self.current_state = tuple(frozen_state)
        if step.get("selected_score") is not None and self.current_state == tuple(step.get("next_state", ())):
            self.current_score = step["selected_score"]
        elif step.get("score") is not None:
            self.current_score = step["score"]
        else:
            grids = [world["grid"] for world in self.worlds]
            self.current_score = score_state(grids, self.current_state)

        self.step_index += 1
        self.trace_rows.append(self._trace_row(step))
        if len(self.trace_rows) > 12:
            self.trace_rows = [self.trace_rows[0]] + self.trace_rows[-11:]

        if step.get("goal"):
            self.finished = True
            self.auto_play = False
            self.generator = None
            self.status_message = "Hoàn tất: tất cả ma trận trong belief state đã đạt GOAL."
        elif step.get("loop"):
            self.auto_play = False
            self.generator = None
            self.status_message = "Đã dính loop trong tập belief state. Hãy RANDOM và chạy lại."
        elif step.get("stuck"):
            self.auto_play = False
            self.generator = None
            self.status_message = "Không còn trạng thái tốt hơn hoặc không tìm được đường chung."
        elif step.get("restarting"):
            self.status_message = f"IDS bắt đầu lại với depth = {step.get('depth_limit', 0)}"
        else:
            self.status_message = f"Đang mở rộng node {step.get('current_label', '-')}."

        self._record_history()

    def _rewind_search(self):
        """Move one visual step backward without restarting the algorithm."""
        if self.history_cursor <= 0:
            self.status_message = "Đang ở trạng thái belief ban đầu."
            return
        self.auto_play = False
        self._restore_history(self.history_cursor - 1)
        self.status_message = (
            f"Đang xem lại bước {self.history_cursor}/{max(0, len(self.history) - 1)}. "
            "Nhấn NEXT để xem tiếp."
        )

    def _record_history(self):
        """Save the visible search state used by PREV/NEXT playback."""
        if self.history_cursor < len(self.history) - 1:
            self.history = self.history[: self.history_cursor + 1]
        snapshot = {
            "current_state": tuple(self.current_state),
            "current_score": copy.deepcopy(self.current_score),
            "last_step": copy.deepcopy(self.last_step),
            "trace_rows": copy.deepcopy(self.trace_rows),
            "step_index": self.step_index,
            "finished": self.finished,
            "status_message": self.status_message,
            "completed_worlds": set(self.completed_worlds),
        }
        self.history.append(snapshot)
        self.history_cursor = len(self.history) - 1

    def _restore_history(self, index):
        index = max(0, min(index, len(self.history) - 1))
        snapshot = self.history[index]
        self.history_cursor = index
        self.current_state = tuple(snapshot["current_state"])
        self.current_score = copy.deepcopy(snapshot["current_score"])
        self.last_step = copy.deepcopy(snapshot["last_step"])
        self.trace_rows = copy.deepcopy(snapshot["trace_rows"])
        self.step_index = snapshot["step_index"]
        self.finished = snapshot["finished"]
        self.status_message = snapshot["status_message"]
        self.completed_worlds = set(snapshot.get("completed_worlds", set()))
        self.auto_play = False

    def _trace_row(self, step):
        current = step.get("current_label", "-")
        if step.get("depth_limit") is not None:
            current += f" (d={step['depth_limit']})"

        if self.algorithm_name in HILL:
            score = step.get("score")
            current_text = current
            if score is not None:
                current_text += f"  h={score['h']:.1f}"

            next_nodes = []
            for child in step.get("children", []):
                child_text = child.get("label", "-")
                child_score = child.get("score")
                if child_score is not None:
                    child_text += f" (h={child_score['h']:.1f})"
                if child.get("selected"):
                    child_text += " [CHỌN]"
                elif not child.get("accepted"):
                    child_text += " [LOẠI]"
                next_nodes.append(child_text)

            if not next_nodes:
                if step.get("goal"):
                    next_text = "GOAL – tất cả ma trận đã hoàn thành"
                elif step.get("loop"):
                    next_text = "LOOP – trạng thái đã xuất hiện"
                elif step.get("stuck"):
                    next_text = "Không có node tốt hơn"
                else:
                    next_text = "Không sinh node kế tiếp"
            else:
                next_text = " | ".join(next_nodes)

            return {
                "current": current_text,
                "next": next_text,
            }

        # Node is only the state currently being expanded.
        node_text = current
        score = step.get("score")
        if self.algorithm_name in INFORMED and score is not None:
            node_text += (
                f" (g={score['g']:.1f}, h={score['h']:.1f}, f={score['f']:.1f})"
            )

        # Frontier is the open set: generated child nodes still waiting to be
        # examined.  For group 2, show each node's averaged g/h/f beside it.
        if self.algorithm_name in INFORMED:
            frontier_items = []
            for item in step.get("frontier_entries", []):
                item_score = item.get("score") or {}
                frontier_items.append(
                    f"{item.get('label', '-')}"
                    f"(g={item_score.get('g', 0.0):.1f},"
                    f"h={item_score.get('h', 0.0):.1f},"
                    f"f={item_score.get('f', 0.0):.1f})"
                )
        else:
            frontier_items = list(step.get("frontier", []))

        # Reached is the closed set only: nodes already expanded and never
        # successor descriptions or calculation details.
        reached_items = list(step.get("reached", []))
        frontier_text = "{" + ", ".join(frontier_items) + "}" if frontier_items else "∅"
        reached_text = "{" + ", ".join(reached_items) + "}" if reached_items else "∅"

        return {
            "stt": str(self.step_index),
            "node": node_text,
            "frontier": frontier_text,
            "reached": reached_text,
        }

    @staticmethod
    def _number(value):
        return str(int(value)) if float(value).is_integer() else f"{value:.1f}"

    # ------------------------------------------------------------------
    # Drawing
    def draw(self, surface):
        draw_stadium_background(surface)
        self._draw_header(surface)
        self._draw_belief_maps(surface)
        self._draw_controls(surface)
        self._draw_trace_table(surface)
        draw_outer_frame(surface)

    def _draw_header(self, surface):
        draw_text(
            surface,
            "LEVEL 4: BELIEF STATE SEARCH",
            (C.SCREEN_W // 2, 18),
            size=22,
            color=C.COL_CREAM_TEXT,
            align="center",
        )
        mode = "KHÔNG QUAN SÁT" if self.observation_mode == 0 else "QUAN SÁT MỘT PHẦN"
        draw_text(
            surface,
            f"{mode}  •  {self.algorithm_name}",
            (C.SCREEN_W // 2, 48),
            size=12,
            color=C.COL_GOLD_BRIGHT,
            align="center",
            shadow=False,
        )

    def _draw_belief_maps(self, surface):
        draw_wood_panel(surface, MAP_AREA, border=5, corner=8, fill=(44, 34, 24))
        if not self.worlds:
            draw_text(surface, "TRẠNG THÁI NHÂN VẬT = ?", (MAP_AREA.centerx, MAP_AREA.top + 95),
                      size=24, color=C.COL_GOLD_BRIGHT, align="center")
            draw_text(surface, "Chọn 2 đến 6 rồi nhấn RANDOM hoặc BELIEF +", (MAP_AREA.centerx, MAP_AREA.top + 145),
                      size=16, color=C.COL_CREAM_TEXT, align="center")
            draw_text(surface, "RANDOM tạo ma trận ẩn/quan sát một phần. BELIEF + sẽ khui hết rồi bắt đầu giải.",
                      (MAP_AREA.centerx, MAP_AREA.top + 185), size=13,
                      color=C.COL_CREAM_TEXT, align="center", shadow=False)
            return

        set_text = "S={" + ", ".join(f"ma trận {i + 1}" for i in range(len(self.worlds))) + "}"
        draw_text(surface, set_text, (MAP_AREA.centerx, MAP_AREA.top + 7), size=14,
                  color=C.COL_GOLD_BRIGHT, align="center", shadow=False)

        for index, (world, panel_rect) in enumerate(zip(self.worlds, self._belief_map_rects())):
            self._draw_world(surface, world, index, panel_rect)

    def _belief_map_rects(self):
        count = len(self.worlds) or self.belief_count
        columns = 2 if count > 1 else 1
        rows = math.ceil(count / columns)
        gap = 10
        inner = pygame.Rect(MAP_AREA.left + 10, MAP_AREA.top + 30, MAP_AREA.width - 20, MAP_AREA.height - 40)
        slot_w = (inner.width - gap * (columns - 1)) // columns
        slot_h = (inner.height - gap * (rows - 1)) // rows
        rects = []
        for index in range(count):
            col = index % columns
            row = index // columns
            rects.append(pygame.Rect(
                inner.left + col * (slot_w + gap),
                inner.top + row * (slot_h + gap),
                slot_w,
                slot_h,
            ))
        return rects

    def _draw_world(self, surface, world, index, panel_rect):
        grid = world["grid"]
        position = self.current_state[index]
        solved = position == grid.goal
        border = C.COL_GOLD_BRIGHT if solved else C.COL_WOOD_DARK
        pygame.draw.rect(surface, (62, 48, 34), panel_rect, border_radius=6)
        pygame.draw.rect(surface, border, panel_rect, 2, border_radius=6)

        if world.get("belief_revealed", False):
            title_state = "ĐÃ GOAL" if solved else "trạng thái = CR7"
        elif world.get("actor_visible", False):
            title_state = "trạng thái = CR7"
        else:
            title_state = "trạng thái = ?"
        title = f"{world['name']}  {title_state}"
        draw_text(surface, title, (panel_rect.centerx, panel_rect.top + 4), size=11,
                  color=C.COL_GOLD_BRIGHT if solved else C.COL_CREAM_TEXT,
                  align="center", shadow=False)

        cell_size = min(
            max(12, (panel_rect.width - 12) // grid.cols),
            max(12, (panel_rect.height - 36) // grid.rows),
        )
        grid_w, grid_h = grid.cols * cell_size, grid.rows * cell_size
        origin_x = panel_rect.centerx - grid_w // 2
        origin_y = panel_rect.top + 25 + max(0, (panel_rect.height - 30 - grid_h) // 2)

        for row in range(grid.rows):
            for col in range(grid.cols):
                cell = grid.get(col, row)
                rect = pygame.Rect(origin_x + col * cell_size, origin_y + row * cell_size, cell_size, cell_size)
                self._draw_world_cell(surface, world, index, rect, cell, position)

        if self.current_score is not None and self.algorithm_name not in BLIND:
            h = self.current_score["h_components"][index]
            g = self.current_score["g_components"][index]
            f = self.current_score["f_components"][index]
            draw_text(surface, f"g={g:.1f}  h={h:.1f}  f={f:.1f}",
                      (panel_rect.centerx, panel_rect.bottom - 14), size=9,
                      color=C.COL_CREAM_TEXT, align="center", shadow=False)

    def _draw_world_cell(self, surface, world, index, rect, cell, position):
        grid = world["grid"]
        pos = (cell.col, cell.row)
        hidden = not cell.revealed and pos != grid.goal

        if hidden:
            pygame.draw.rect(surface, (232, 224, 198), rect)
            pygame.draw.rect(surface, (65, 55, 45), rect, 1)
            draw_text(surface, "?", rect.center, size=max(11, rect.height // 2),
                      color=C.COL_BLACK, align="center", shadow=False)
        else:
            pygame.draw.rect(surface, self._cell_color(cell.kind, cell.value), rect)
            pygame.draw.rect(surface, (48, 72, 42), rect, 1)
            if cell.kind == "wall":
                draw_text(surface, "×", rect.center, size=max(10, rect.height // 2),
                          color=C.COL_CREAM_TEXT, align="center", shadow=False)
            elif cell.kind == "trophy":
                trophy = AssetManager.instance().get_image(
                    "sprites/ui/trophy_worldcup.png",
                    size=(max(10, int(rect.width * 0.55)), max(10, int(rect.height * 0.62))),
                    placeholder=placeholder_trophy,
                )
                surface.blit(trophy, trophy.get_rect(center=(rect.centerx, rect.centery - 2)))
            elif cell.value is not None:
                self._draw_level_two_value(surface, rect, cell)

        if pos != position:
            return
        if not world.get("belief_revealed", False):
            if world.get("actor_visible", False):
                self._draw_character(surface, rect, at_goal=pos == grid.goal)
            return
        if pos == grid.goal:
            pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, rect.inflate(-3, -3), 3, border_radius=4)
            draw_text(surface, "✓", (rect.centerx, rect.top + 1), size=max(9, rect.height // 4),
                      color=C.COL_GOLD_BRIGHT, align="center", shadow=False)

        self._draw_character(surface, rect, at_goal=pos == grid.goal)

    def _draw_character(self, surface, rect, at_goal=False):
        kit_index = max(0, min(self.game_state.kit_index, len(C.KITS) - 1))
        kit = C.KITS[kit_index]
        sprite_h = max(18, int(rect.height * (0.54 if at_goal else 0.72)))
        sprite_w = max(10, int(sprite_h * 50 / 96))
        sprite = AssetManager.instance().get_image(
            f"sprites/characters/cr7_chibi_{kit['name']}.png",
            size=(sprite_w, sprite_h),
            placeholder=lambda size: placeholder_chibi(size, kit["color"]),
        )
        anchor_x = rect.right - max(3, rect.width // 8) if at_goal else rect.centerx
        anchor_y = rect.bottom - max(2, rect.height // 18)
        actor_rect = sprite.get_rect(midbottom=(anchor_x, anchor_y))
        surface.blit(sprite, actor_rect)

    @staticmethod
    def _draw_level_two_value(surface, rect, cell):
        """Render signed cell values with the same sizing as Level 2."""
        value = cell.value if cell.value is not None else 0
        text_color = (
            C.COL_BLACK
            if cell.kind in {"path", "start", "trophy", "grass"} or value >= 0
            else C.COL_CREAM_TEXT
        )
        # Level 2 uses a 17 px bold pixel font and a slightly raised centre.
        # Keep that exact look on normal-sized cells and scale down only when
        # 3–4 belief maps make the cells too small.
        font_size = 17 if rect.height >= 42 else max(10, rect.height // 3)
        y_offset = 9 if rect.height >= 42 else max(4, rect.height // 7)
        draw_text(
            surface,
            f"{value:+d}",
            (rect.centerx, rect.centery - y_offset),
            size=font_size,
            color=text_color,
            align="center",
        )

    def _draw_controls(self, surface):
        panel = CONTROL_PANEL
        draw_wood_panel(surface, panel, border=5, corner=8, fill=(54, 32, 24))

        self.mode_toggle.draw(surface)
        self.group_toggle.draw(surface)
        self.count_toggle.draw(surface)
        self.belief_button.text = f"BELIEF + ({self.belief_count})"
        self.belief_button.draw(surface)
        self.random_button.draw(surface)

        can_rewind = self.history_cursor > 0
        can_advance = (
            self.history_cursor < len(self.history) - 1
            or (self.generator is not None and not self.finished)
        )
        self.prev_button.enabled = can_rewind
        self.next_button.enabled = can_advance
        self.auto_button.enabled = can_advance
        self.auto_button.text = "STOP" if self.auto_play else "AUTO"
        self.prev_button.draw(surface)
        self.next_button.draw(surface)
        self.auto_button.draw(surface)
        self.back_button.draw(surface)

        for button in self.algorithm_buttons:
            button.draw(surface)
            if button.text == self.algorithm_name:
                pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, button.rect, 2, border_radius=6)

        if self.current_score is not None and self.algorithm_name in INFORMED:
            n = len(self.worlds)
            h_values = "+".join(self._number(v) for v in self.current_score["h_components"])
            g_values = "+".join(self._number(v) for v in self.current_score["g_components"])
            draw_text(surface, f"h=({h_values})/{n}={self.current_score['h']:.1f}",
                      (panel.left + 14, panel.top + 291), size=9,
                      color=C.COL_CREAM_TEXT, shadow=False, max_width=panel.width - 28)
            draw_text(surface, f"g=({g_values})/{n}={self.current_score['g']:.1f}; f=g+h={self.current_score['f']:.1f}",
                      (panel.left + 14, panel.top + 305), size=9,
                      color=C.COL_GOLD_BRIGHT, shadow=False, max_width=panel.width - 28)
        else:
            draw_text(surface, self.status_message, (panel.left + 14, panel.top + 291),
                      size=9, color=C.COL_CREAM_TEXT, shadow=False,
                      max_width=panel.width - 28)

    def _draw_trace_table(self, surface):
        draw_wood_panel(surface, TRACE_PANEL, border=5, corner=8, fill=(34, 28, 20))
        inner = TRACE_PANEL.inflate(-14, -12)
        header_h = 22

        pygame.draw.rect(surface, (232, 224, 198), inner, border_radius=3)
        pygame.draw.rect(surface, C.COL_WOOD_DARK, inner, 2, border_radius=3)
        pygame.draw.line(
            surface,
            C.COL_WOOD_DARK,
            (inner.left, inner.top + header_h),
            (inner.right, inner.top + header_h),
            2,
        )

        rows = self.trace_rows[-2:] if len(self.trace_rows) > 1 else self.trace_rows
        row_h = max(42, (inner.height - header_h) // max(1, len(rows)))

        if self.algorithm_name in HILL:
            current_w = 250
            divider = inner.left + current_w
            pygame.draw.line(surface, C.COL_WOOD_DARK, (divider, inner.top), (divider, inner.bottom), 2)

            draw_text(surface, "Current Node", (inner.left + 8, inner.top + 3), size=12,
                      color=C.COL_BLACK, shadow=False)
            draw_text(surface, "Next Node", (divider + 8, inner.top + 3), size=12,
                      color=C.COL_BLACK, shadow=False)

            if not rows:
                rows = [{"current": "-", "next": "Chưa bắt đầu giải."}]

            y = inner.top + header_h
            for row in rows:
                pygame.draw.line(surface, (120, 106, 84), (inner.left, y), (inner.right, y), 1)
                draw_text(
                    surface,
                    row.get("current", "-"),
                    (inner.left + 8, y + 5),
                    size=10,
                    color=C.COL_BLACK,
                    shadow=False,
                    max_width=current_w - 16,
                )
                draw_text(
                    surface,
                    row.get("next", "-"),
                    (divider + 8, y + 4),
                    size=9,
                    color=C.COL_BLACK,
                    shadow=False,
                    max_width=inner.right - divider - 16,
                )
                y += row_h
            return

        stt_w = 52
        node_w = 205
        frontier_w = 430
        x1 = inner.left + stt_w
        x2 = x1 + node_w
        x3 = x2 + frontier_w

        for divider in (x1, x2, x3):
            pygame.draw.line(surface, C.COL_WOOD_DARK, (divider, inner.top), (divider, inner.bottom), 2)

        draw_text(surface, "STT", (inner.left + 8, inner.top + 3), size=12,
                  color=C.COL_BLACK, shadow=False)
        draw_text(surface, "Node", (x1 + 8, inner.top + 3), size=12,
                  color=C.COL_BLACK, shadow=False)
        draw_text(surface, "Frontier", (x2 + 8, inner.top + 3), size=12,
                  color=C.COL_BLACK, shadow=False)
        draw_text(surface, "Reached", (x3 + 8, inner.top + 3), size=12,
                  color=C.COL_BLACK, shadow=False)

        if not rows:
            rows = [{"stt": "-", "node": "-", "frontier": "∅", "reached": "Chưa bắt đầu giải."}]

        y = inner.top + header_h
        for row in rows:
            pygame.draw.line(surface, (120, 106, 84), (inner.left, y), (inner.right, y), 1)
            draw_text(surface, row.get("stt", "-"), (inner.left + 8, y + 5), size=10,
                      color=C.COL_BLACK, shadow=False, max_width=stt_w - 16)
            draw_text(surface, row.get("node", "-"), (x1 + 8, y + 5), size=9,
                      color=C.COL_BLACK, shadow=False, max_width=node_w - 16)
            draw_text(surface, row.get("frontier", "∅"), (x2 + 8, y + 4), size=9,
                      color=C.COL_BLACK, shadow=False, max_width=frontier_w - 16)
            draw_text(surface, row.get("reached", "∅"), (x3 + 8, y + 4), size=9,
                      color=C.COL_BLACK, shadow=False, max_width=inner.right - x3 - 16)
            y += row_h

    @staticmethod
    def _cell_color(kind, value):
        if kind == "wall":
            return C.COL_WALL_STONE
        if kind == "trophy":
            return (210, 184, 96)
        if kind == "start":
            return (244, 218, 126)
        if value is not None:
            if value > 0:
                return (110, 180, 110)
            if value == 0:
                return C.COL_SILVER
            if value >= -2:
                return C.COL_DANGER_RED
            return (120, 48, 36)
        return C.COL_GRASS_LIGHT
