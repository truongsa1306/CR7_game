"""Level 7: visual AND-OR search in a partially observable grid."""
from __future__ import annotations

import copy
import math
import random

import pygame

import config as C
from entities.grid_cell import GridModel
from scenes.base_scene import BaseScene
from systems.algorithms.and_or_search import and_or_graph_search
from systems.asset_manager import AssetManager, placeholder_chibi, placeholder_trophy
from systems.audio_manager import AudioManager
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_stadium_background, draw_wood_panel


MAIN_PANEL = pygame.Rect(18, 68, 570, 340)
BRANCH_PANEL = pygame.Rect(596, 68, 410, 340)
TRACE_PANEL = pygame.Rect(18, 416, 988, 144)

ACTION_DATA = {
    "R": (1, 0, "PHẢI"),
    "U": (0, -1, "LÊN"),
    "D": (0, 1, "XUỐNG"),
    "L": (-1, 0, "TRÁI"),
}
ACTION_ORDER = ("R", "U", "D", "L")

COL_OR = (70, 145, 235)
COL_AND = (166, 76, 202)
COL_ACCEPT = (64, 190, 105)
COL_REJECT = (215, 72, 72)
COL_DIM = (10, 8, 12, 155)


class AndOrSearchScene(BaseScene):
    """Demo one OR choice and all environment outcomes as AND branches."""

    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.rng = random.Random()
        self.grid = None
        self.start = (1, 3)
        self.goal = (6, 0)
        self.player_pos = self.start
        self.unknown_cells = set()
        self.initial_unknown_cells = set()
        self.uncertainty = {}
        self.revealed_unknowns = set()
        self.initial_revealed_unknowns = set()

        self.event_queue = []
        self.event_index = 0
        self.current_event = None
        self.search_state = self.start
        self.current_action = None
        self.current_outcomes = []
        self.branch_statuses = []
        self.accepted_target = None
        self.rejected_targets = set()
        self.trace_rows = []
        self.step_no = 0
        self.expanded = 0
        self.finished = False
        self.auto_play = False
        self.auto_timer = 0.0
        self.status_message = ""

        self.history = []
        self.history_cursor = -1

        self.prev_button = None
        self.next_button = None
        self.auto_button = None
        self.random_button = None
        self.return_button = None
        self.back_button = None

    def on_enter(self, **kwargs):
        self._build_controls()
        self._randomize_map()
        AudioManager.instance().play_bgm("gameplay_search", volume=0.42)

    # ------------------------------------------------------------------
    # Controls
    def _build_controls(self):
        left = BRANCH_PANEL.left + 12
        top = BRANCH_PANEL.top + 12
        gap = 6
        width = (BRANCH_PANEL.width - 24 - gap * 2) // 3
        height = 25
        self.prev_button = Button(
            pygame.Rect(left, top, width, height), "PREV", font_size=10,
            on_click=self._step_back,
        )
        self.next_button = Button(
            pygame.Rect(left + width + gap, top, width, height), "NEXT", font_size=10,
            on_click=self._step_forward,
        )
        self.auto_button = Button(
            pygame.Rect(left + (width + gap) * 2, top, width, height), "AUTO", font_size=10,
            on_click=self._toggle_auto,
        )
        second_y = top + height + 6
        self.random_button = Button(
            pygame.Rect(left, second_y, width, height), "RANDOM", font_size=10,
            on_click=self._randomize_map,
        )
        self.return_button = Button(
            pygame.Rect(left + width + gap, second_y, width, height), "RETURN", font_size=10,
            on_click=self._return_to_start,
        )
        self.back_button = Button(
            pygame.Rect(left + (width + gap) * 2, second_y, width, height), "BACK", font_size=10,
            on_click=lambda: self.manager.change(C.STATE_LEVEL_SELECT),
        )

    def handle_event(self, event):
        for control in (
            self.prev_button,
            self.next_button,
            self.auto_button,
            self.random_button,
            self.return_button,
            self.back_button,
        ):
            control.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                self._step_forward()
            elif event.key == pygame.K_LEFT:
                self._step_back()
            elif event.key == pygame.K_a:
                self._toggle_auto()
            elif event.key == pygame.K_r:
                self._randomize_map()
            elif event.key == pygame.K_HOME:
                self._return_to_start()
            elif event.key == pygame.K_ESCAPE:
                self.manager.change(C.STATE_LEVEL_SELECT)

    def update(self, dt):
        if not self.auto_play or self.finished:
            return
        self.auto_timer += dt
        if self.auto_timer >= 0.16:
            self.auto_timer = 0.0
            self._step_forward()

    # ------------------------------------------------------------------
    # Map generation and transition model
    def _randomize_map(self):
        self.grid = GridModel(7, 5, self.start, self.goal, fog=False)
        self.player_pos = self.start

        guaranteed_corridor = {
            (1, 3), (1, 2), (1, 1), (1, 0),
            (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
        }
        wall_candidates = [(0, 3), (3, 2), (4, 3), (0, 1), (5, 4)]
        walls = {(0, 3)}
        for pos in wall_candidates[1:]:
            if self.rng.random() < 0.45 and pos not in guaranteed_corridor:
                walls.add(pos)

        values = (-4, -2, 0, 2, 4)
        weights = (8, 18, 20, 30, 24)
        for pos, cell in self.grid.cells.items():
            if pos in walls:
                cell.kind = "wall"
                cell.value = None
                continue
            value = self.rng.choices(values, weights=weights, k=1)[0]
            cell.value = value
            if value > 0:
                cell.kind = "path"
            elif value == 0:
                cell.kind = "grass"
            elif value == -2:
                cell.kind = "danger"
            else:
                cell.kind = "fire"

        self.grid.set_kind(*self.start, "start")
        self.grid.get(*self.start).value = 2
        self.grid.set_kind(*self.goal, "trophy")
        self.grid.get(*self.goal).value = 0

        passable = [
            pos for pos, cell in self.grid.cells.items()
            if cell.passable and pos not in (self.start, self.goal)
        ]
        required_unknowns = {(2, 3), (1, 2)}
        extra_candidates = [pos for pos in passable if pos not in required_unknowns]
        self.rng.shuffle(extra_candidates)
        self.unknown_cells = set(required_unknowns)
        self.unknown_cells.update(extra_candidates[:7])
        self.initial_unknown_cells = set(self.unknown_cells)

        self.uncertainty = {}
        for pos in self.unknown_cells:
            self.uncertainty[pos] = {
                "risky": self.rng.random() < 0.38,
                "branches": self.rng.choice((2, 2, 3)),
            }
        # The first right action demonstrates rejection; the first upward
        # action demonstrates a valid AND choice with two possible outcomes.
        if (2, 3) in self.uncertainty:
            self.uncertainty[(2, 3)] = {"risky": True, "branches": 2}
        if (1, 2) in self.uncertainty:
            self.uncertainty[(1, 2)] = {"risky": False, "branches": 2}

        self.revealed_unknowns = set()
        self.initial_revealed_unknowns = set()
        self._reset_search_state("Bản đồ mới: ô ? chỉ được chọn khi mọi nhánh AND đều tới Goal.")

    def _return_to_start(self):
        self.player_pos = self.start
        self.revealed_unknowns = set(self.initial_revealed_unknowns)
        self._reset_search_state("Đã RETURN về Start. Nhấn NEXT hoặc AUTO để giải lại.")

    def _reset_search_state(self, message):
        self.event_queue = []
        self.event_index = 0
        self.current_event = None
        self.search_state = self.player_pos
        self.current_action = None
        self.current_outcomes = []
        self.branch_statuses = []
        self.accepted_target = None
        self.rejected_targets = set()
        self.trace_rows = []
        self.step_no = 0
        self.expanded = 0
        self.finished = self.player_pos == self.goal
        self.auto_play = False
        self.auto_timer = 0.0
        self.status_message = message
        self.history = []
        self.history_cursor = -1
        self._prepare_decision()
        self._record_history()

    def _is_passable(self, pos):
        return self.grid.in_bounds(*pos) and self.grid.get(*pos).passable

    def _target(self, state, action):
        dc, dr, _ = ACTION_DATA[action]
        target = (state[0] + dc, state[1] + dr)
        return target if self._is_passable(target) else state

    def _actions_from(self, state):
        candidates = []
        for order, action in enumerate(ACTION_ORDER):
            target = self._target(state, action)
            if target == state:
                continue
            h = self.grid.manhattan(target, self.goal)
            candidates.append((h, order, action))
        candidates.sort()
        return [action for _, _, action in candidates]

    def _outcomes(self, state, action):
        target = self._target(state, action)
        if target == state:
            return (state,)
        if target not in self.unknown_cells or target in self.revealed_unknowns:
            return (target,)

        profile = self.uncertainty[target]
        if profile["risky"]:
            return tuple(dict.fromkeys((target, state)))

        dc, dr, _ = ACTION_DATA[action]
        if dc:
            slips = [(state[0], state[1] - 1), (state[0], state[1] + 1)]
        else:
            slips = [(state[0] + 1, state[1]), (state[0] - 1, state[1])]
        slips = [pos for pos in slips if self._is_passable(pos) and pos != target]
        slips.sort(key=lambda pos: self.grid.manhattan(pos, self.goal))
        count = max(1, profile["branches"] - 1)
        result = [target] + slips[:count]
        if len(result) == 1:
            result.append(state)
        return tuple(dict.fromkeys(result))

    def _prepare_decision(self):
        if self.finished:
            return
        result = and_or_graph_search(
            self.player_pos,
            is_goal=lambda state: state == self.goal,
            actions=self._actions_from,
            outcomes=self._outcomes,
            action_name=lambda action: ACTION_DATA[action][2],
            max_depth=15,
            max_events=500,
            trace_depth=1,
        )
        self.expanded = result.expanded
        self.event_queue = list(result.events)
        self.event_index = 0

        if result.success and result.plan is not None and result.plan.action is not None:
            action = result.plan.action
            outcomes = tuple(result.plan.branches.keys())
            intended = self._target(self.player_pos, action)
            choices = list(outcomes)
            actual = intended if intended in choices and self.rng.random() < 0.65 else self.rng.choice(choices)
            self.event_queue.append({
                "type": "EXECUTE",
                "state": self.player_pos,
                "action": action,
                "action_name": ACTION_DATA[action][2],
                "outcomes": outcomes,
                "actual": actual,
                "depth": 0,
            })
            self.status_message = (
                f"Đã lập cây AND–OR ({result.expanded} OR nodes). Nhấn NEXT để xem từng bước."
            )
        else:
            self.event_queue.append({
                "type": "NO_PLAN",
                "state": self.player_pos,
                "depth": 0,
            })
            self.status_message = "Không tìm được hành động an toàn từ trạng thái hiện tại."

    # ------------------------------------------------------------------
    # Timeline
    def _step_forward(self):
        if self.history_cursor < len(self.history) - 1:
            self._restore_history(self.history_cursor + 1)
            return
        if self.finished:
            self.auto_play = False
            return
        if self.event_index >= len(self.event_queue):
            self._prepare_decision()
        if not self.event_queue or self.event_index >= len(self.event_queue):
            return

        event = self.event_queue[self.event_index]
        self.event_index += 1
        self._apply_event(event)
        self._record_history()

    def _step_back(self):
        if self.history_cursor <= 0:
            self.status_message = "Đang ở trạng thái đầu tiên."
            return
        self.auto_play = False
        self._restore_history(self.history_cursor - 1)

    def _toggle_auto(self):
        if self.finished:
            return
        self.auto_play = not self.auto_play
        self.auto_timer = 0.0
        self.status_message = "Đang chạy AUTO" if self.auto_play else "Đã tạm dừng"

    def _apply_event(self, event):
        self.current_event = copy.deepcopy(event)
        event_type = event["type"]
        self.search_state = event.get("outcome", event.get("state", self.player_pos))
        depth = event.get("depth", 0)

        if event_type == "OR_ENTER":
            self.current_action = None
            self.accepted_target = None
            self.status_message = f"OR node {self._state_name(event['state'])}: chọn một hành động."

        elif event_type == "OR_TRY":
            self.current_action = event["action"]
            self.current_outcomes = []
            self.branch_statuses = []
            self.status_message = f"Thử OR action {event['action_name']}."
            self._append_trace(event, "ĐANG XÉT")

        elif event_type == "AND_EXPAND":
            self.current_action = event["action"]
            self.current_outcomes = list(event["outcomes"])
            self.branch_statuses = ["CHỜ" for _ in self.current_outcomes]
            self.status_message = (
                f"Sinh {len(self.current_outcomes)} nhánh AND. Phải giải thành công tất cả."
            )
            self._append_trace(event, "SINH AND")

        elif event_type == "BRANCH_START":
            self._sync_outcomes(event)
            index = event["branch_index"]
            if index < len(self.branch_statuses):
                self.branch_statuses[index] = "ĐANG GIẢI"
            self.status_message = f"Đang giải nhánh AND {index + 1}."

        elif event_type in ("BRANCH_SUCCESS", "BRANCH_FAIL"):
            self._sync_outcomes(event)
            index = event["branch_index"]
            status = "THÀNH CÔNG" if event_type == "BRANCH_SUCCESS" else "THẤT BẠI"
            if index < len(self.branch_statuses):
                self.branch_statuses[index] = status
            self.status_message = f"Nhánh AND {index + 1}: {status}."
            self._append_trace(event, status)

        elif event_type in ("ACTION_ACCEPT", "ACTION_REJECT"):
            self.current_action = event["action"]
            self._sync_outcomes(event)
            target = self._target(event["state"], event["action"])
            accepted = event_type == "ACTION_ACCEPT"
            if depth == 0:
                if accepted:
                    self.accepted_target = target
                else:
                    self.rejected_targets.add(target)
            result = "NHẬN" if accepted else "LOẠI"
            self.status_message = (
                f"{event['action_name']}: {result} — "
                + ("mọi nhánh đều có lời giải." if accepted else "có ít nhất một nhánh thất bại.")
            )
            self._append_trace(event, result)

        elif event_type == "GOAL":
            self.status_message = f"Nhánh {self._state_name(event['state'])} đã tới GOAL."

        elif event_type == "OR_FAIL":
            self.status_message = f"Node {self._state_name(event['state'])}: {event.get('reason', 'THẤT BẠI')}."

        elif event_type == "EXECUTE":
            previous = self.player_pos
            self.player_pos = tuple(event["actual"])
            self.search_state = self.player_pos
            self.revealed_unknowns.add(self.player_pos)
            self.rejected_targets.clear()
            self.accepted_target = None
            self.current_outcomes = list(event.get("outcomes", ()))
            self.branch_statuses = [
                "KẾT QUẢ THẬT" if pos == self.player_pos else "ĐÃ CHỨNG MINH"
                for pos in self.current_outcomes
            ]
            self._append_trace(event, f"THỰC THI → {self._state_name(self.player_pos)}")
            if self.player_pos == self.goal:
                self.finished = True
                self.auto_play = False
                self.status_message = "HOÀN TẤT: CR7 đã tới cúp bằng chính sách AND–OR."
            else:
                self.status_message = (
                    f"Đã chọn {event['action_name']}; môi trường đưa CR7 từ "
                    f"{self._state_name(previous)} tới {self._state_name(self.player_pos)}."
                )

        elif event_type == "NO_PLAN":
            self.auto_play = False
            self.status_message = "Không có hành động nào bảo đảm tất cả nhánh tới Goal. Hãy RANDOM."
            self._append_trace(event, "KHÔNG CÓ PLAN")

        elif event_type == "CACHE_SUCCESS":
            self.status_message = f"Tái sử dụng lời giải của {self._state_name(event['state'])}."

        elif event_type == "CACHE_FAIL":
            self.status_message = f"Bỏ qua node thất bại đã biết {self._state_name(event['state'])}."

    def _sync_outcomes(self, event):
        outcomes = list(event.get("outcomes", ()))
        if outcomes != self.current_outcomes:
            self.current_outcomes = outcomes
            self.branch_statuses = ["CHỜ" for _ in outcomes]

    def _append_trace(self, event, result):
        action_name = event.get("action_name", "—")
        outcomes = event.get("outcomes")
        if outcomes:
            outcome_text = "{" + ", ".join(self._state_name(pos) for pos in outcomes) + "}"
        elif event.get("outcome") is not None:
            outcome_text = self._state_name(event["outcome"])
        else:
            outcome_text = "—"
        self.trace_rows.append({
            "step": str(self.step_no),
            "node": self._state_name(event.get("state", self.search_state)),
            "action": action_name,
            "and": outcome_text,
            "result": result,
        })
        self.step_no += 1
        if len(self.trace_rows) > 30:
            self.trace_rows = self.trace_rows[-30:]

    def _snapshot(self):
        return {
            "player_pos": self.player_pos,
            "revealed_unknowns": set(self.revealed_unknowns),
            "event_queue": copy.deepcopy(self.event_queue),
            "event_index": self.event_index,
            "current_event": copy.deepcopy(self.current_event),
            "search_state": self.search_state,
            "current_action": self.current_action,
            "current_outcomes": list(self.current_outcomes),
            "branch_statuses": list(self.branch_statuses),
            "accepted_target": self.accepted_target,
            "rejected_targets": set(self.rejected_targets),
            "trace_rows": copy.deepcopy(self.trace_rows),
            "step_no": self.step_no,
            "expanded": self.expanded,
            "finished": self.finished,
            "status_message": self.status_message,
        }

    def _record_history(self):
        if self.history_cursor < len(self.history) - 1:
            self.history = self.history[: self.history_cursor + 1]
        self.history.append(self._snapshot())
        self.history_cursor = len(self.history) - 1

    def _restore_history(self, index):
        index = max(0, min(index, len(self.history) - 1))
        snapshot = self.history[index]
        self.history_cursor = index
        self.player_pos = tuple(snapshot["player_pos"])
        self.revealed_unknowns = set(snapshot["revealed_unknowns"])
        self.event_queue = copy.deepcopy(snapshot["event_queue"])
        self.event_index = snapshot["event_index"]
        self.current_event = copy.deepcopy(snapshot["current_event"])
        self.search_state = tuple(snapshot["search_state"])
        self.current_action = snapshot["current_action"]
        self.current_outcomes = list(snapshot["current_outcomes"])
        self.branch_statuses = list(snapshot["branch_statuses"])
        self.accepted_target = snapshot["accepted_target"]
        self.rejected_targets = set(snapshot["rejected_targets"])
        self.trace_rows = copy.deepcopy(snapshot["trace_rows"])
        self.step_no = snapshot["step_no"]
        self.expanded = snapshot["expanded"]
        self.finished = snapshot["finished"]
        self.status_message = snapshot["status_message"]
        self.auto_play = False

    @staticmethod
    def _state_name(state):
        return f"({state[0]},{state[1]})"

    # ------------------------------------------------------------------
    # Drawing
    def draw(self, surface):
        draw_stadium_background(surface)
        self._draw_header(surface)
        self._draw_main_map(surface)
        self._draw_branch_panel(surface)
        self._draw_trace(surface)
        draw_outer_frame(surface)

    def _draw_header(self, surface):
        draw_text(
            surface, "LEVEL 7: AND–OR SEARCH", (C.SCREEN_W // 2, 16),
            size=23, color=C.COL_CREAM_TEXT, align="center",
        )
        draw_text(
            surface, "OR CHỌN 1 HÀNH ĐỘNG  •  AND PHẢI GIẢI TẤT CẢ KẾT QUẢ",
            (C.SCREEN_W // 2, 47), size=11, color=C.COL_GOLD_BRIGHT,
            align="center", shadow=False,
        )

    def _draw_main_map(self, surface):
        draw_wood_panel(surface, MAIN_PANEL, border=5, corner=8, fill=(48, 37, 27))
        draw_text(surface, "BẢN ĐỒ CHÍNH – QUAN SÁT MỘT PHẦN",
                  (MAIN_PANEL.centerx, MAIN_PANEL.top + 8), size=13,
                  color=C.COL_GOLD_BRIGHT, align="center", shadow=False)

        grid_area = pygame.Rect(MAIN_PANEL.left + 22, MAIN_PANEL.top + 38,
                                MAIN_PANEL.width - 44, MAIN_PANEL.height - 58)
        cell_size = min(grid_area.width // self.grid.cols, grid_area.height // self.grid.rows)
        grid_w = cell_size * self.grid.cols
        grid_h = cell_size * self.grid.rows
        origin = (grid_area.centerx - grid_w // 2, grid_area.centery - grid_h // 2)

        active = {self.player_pos, self.search_state, self.goal}
        active.update(self.current_outcomes)
        if self.current_action:
            active.add(self._target(self.search_state, self.current_action))

        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                pos = (col, row)
                rect = pygame.Rect(origin[0] + col * cell_size, origin[1] + row * cell_size,
                                   cell_size, cell_size)
                self._draw_cell(surface, rect, pos, active)

        draw_text(surface, "Vàng: node  Xanh dương: OR  Tím: AND  Xanh: nhận  Đỏ: loại",
                  (MAIN_PANEL.centerx, MAIN_PANEL.bottom - 19), size=9,
                  color=C.COL_CREAM_TEXT, align="center", shadow=False)

    def _draw_cell(self, surface, rect, pos, active):
        cell = self.grid.get(*pos)
        if cell.kind == "wall":
            base = C.COL_WALL_STONE
        elif cell.kind == "trophy":
            base = (210, 184, 96)
        elif cell.kind == "start":
            base = (244, 218, 126)
        elif cell.value is not None and cell.value > 0:
            base = (108, 178, 108)
        elif cell.value == 0:
            base = C.COL_SILVER
        elif cell.value == -2:
            base = C.COL_DANGER_RED
        else:
            base = (122, 52, 39)

        pygame.draw.rect(surface, base, rect)
        pygame.draw.rect(surface, (48, 58, 42), rect, 2)

        hidden = pos in self.unknown_cells and pos not in self.revealed_unknowns
        if cell.kind == "wall":
            draw_text(surface, "×", rect.center, size=max(13, rect.height // 2),
                      color=C.COL_CREAM_TEXT, align="center", shadow=False)
        elif cell.kind == "trophy":
            trophy = AssetManager.instance().get_image(
                "sprites/ui/trophy_worldcup.png",
                size=(int(rect.width * 0.56), int(rect.height * 0.62)),
                placeholder=placeholder_trophy,
            )
            surface.blit(trophy, trophy.get_rect(center=rect.center))
        elif hidden:
            draw_text(surface, "?", rect.center, size=max(17, rect.height // 2),
                      color=C.COL_BLACK, align="center", shadow=False)
        elif cell.value is not None:
            color = C.COL_BLACK if cell.value >= 0 else C.COL_CREAM_TEXT
            draw_text(surface, f"{cell.value:+d}",
                      (rect.centerx, rect.centery - max(5, rect.height // 8)),
                      size=max(12, min(18, rect.height // 3)), color=color,
                      align="center")

        if self.current_event is not None and pos not in active:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill(COL_DIM)
            surface.blit(overlay, rect.topleft)

        if pos in self.current_outcomes:
            pygame.draw.rect(surface, COL_AND, rect.inflate(-5, -5), 4, border_radius=5)
        if self.current_action and pos == self._target(self.search_state, self.current_action):
            pygame.draw.rect(surface, COL_OR, rect.inflate(-3, -3), 3, border_radius=5)
        if pos in self.rejected_targets:
            pygame.draw.line(surface, COL_REJECT, rect.topleft, rect.bottomright, 5)
            pygame.draw.line(surface, COL_REJECT, rect.topright, rect.bottomleft, 5)
        if pos == self.accepted_target:
            pygame.draw.rect(surface, COL_ACCEPT, rect.inflate(-4, -4), 5, border_radius=5)
        if pos == self.search_state:
            pygame.draw.rect(surface, C.COL_GOLD_BRIGHT, rect.inflate(-7, -7), 3, border_radius=4)

        if pos == self.player_pos:
            self._draw_character(surface, rect)

    def _draw_character(self, surface, rect):
        sprite_h = max(22, int(rect.height * 0.72))
        sprite_w = max(12, int(sprite_h * 50 / 96))
        sprite = AssetManager.instance().get_image(
            "sprites/characters/cr7_chibi_real.png",
            size=(sprite_w, sprite_h),
            placeholder=lambda size: placeholder_chibi(size, (245, 245, 245)),
        )
        surface.blit(sprite, sprite.get_rect(midbottom=(rect.centerx, rect.bottom - 3)))

    def _draw_branch_panel(self, surface):
        draw_wood_panel(surface, BRANCH_PANEL, border=5, corner=8, fill=(54, 32, 24))
        self.auto_button.text = "STOP" if self.auto_play else "AUTO"
        self.prev_button.enabled = self.history_cursor > 0
        self.next_button.enabled = not self.finished
        for control in (
            self.prev_button, self.next_button, self.auto_button,
            self.random_button, self.return_button, self.back_button,
        ):
            control.draw(surface)

        draw_text(surface, self.status_message,
                  (BRANCH_PANEL.left + 14, BRANCH_PANEL.top + 78), size=9,
                  color=C.COL_CREAM_TEXT, shadow=False,
                  max_width=BRANCH_PANEL.width - 28)
        draw_text(surface, f"OR nodes đã mở: {self.expanded}",
                  (BRANCH_PANEL.right - 14, BRANCH_PANEL.top + 103), size=9,
                  color=C.COL_GOLD_BRIGHT, align="right", shadow=False)

        branch_area = pygame.Rect(BRANCH_PANEL.left + 10, BRANCH_PANEL.top + 124,
                                  BRANCH_PANEL.width - 20, BRANCH_PANEL.height - 136)
        if not self.current_outcomes:
            draw_text(surface, "CHƯA CÓ NHÁNH AND",
                      (branch_area.centerx, branch_area.top + 30), size=15,
                      color=C.COL_GOLD_BRIGHT, align="center")
            draw_text(surface, "Khi xét bước vào ô ?, các kết quả có thể sẽ xuất hiện ở đây.",
                      (branch_area.centerx, branch_area.top + 75), size=10,
                      color=C.COL_CREAM_TEXT, align="center", shadow=False,
                      max_width=branch_area.width - 20)
            return

        rects = self._branch_rects(branch_area, len(self.current_outcomes))
        for index, (outcome, rect) in enumerate(zip(self.current_outcomes, rects)):
            status = self.branch_statuses[index] if index < len(self.branch_statuses) else "CHỜ"
            self._draw_mini_world(surface, rect, outcome, index, status)

    @staticmethod
    def _branch_rects(area, count):
        if count == 1:
            return [pygame.Rect(area.centerx - 105, area.top + 5, 210, area.height - 10)]
        gap = 8
        width = (area.width - gap) // 2
        height = (area.height - gap) // 2 if count > 2 else area.height
        rects = []
        for index in range(count):
            if count == 3 and index == 2:
                rects.append(pygame.Rect(area.centerx - width // 2, area.top + height + gap, width, height))
            else:
                col = index % 2
                row = index // 2
                rects.append(pygame.Rect(area.left + col * (width + gap),
                                         area.top + row * (height + gap), width, height))
        return rects

    def _draw_mini_world(self, surface, panel, outcome, index, status):
        if status == "THÀNH CÔNG":
            border = COL_ACCEPT
        elif status == "THẤT BẠI":
            border = COL_REJECT
        elif status in ("ĐANG GIẢI", "KẾT QUẢ THẬT"):
            border = C.COL_GOLD_BRIGHT
        else:
            border = COL_AND
        pygame.draw.rect(surface, (43, 35, 29), panel, border_radius=5)
        pygame.draw.rect(surface, border, panel, 2, border_radius=5)
        draw_text(surface, f"AND {index + 1}: {status}",
                  (panel.centerx, panel.top + 3), size=8, color=border,
                  align="center", shadow=False)

        top = panel.top + 20
        cell_size = min((panel.width - 8) // self.grid.cols,
                        max(5, (panel.height - 25) // self.grid.rows))
        grid_w = self.grid.cols * cell_size
        grid_h = self.grid.rows * cell_size
        ox = panel.centerx - grid_w // 2
        oy = top + max(0, (panel.bottom - top - grid_h) // 2)
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                pos = (col, row)
                cell = self.grid.get(col, row)
                rect = pygame.Rect(ox + col * cell_size, oy + row * cell_size, cell_size, cell_size)
                if cell.kind == "wall":
                    color = C.COL_WALL_STONE
                elif cell.kind == "trophy":
                    color = (210, 184, 96)
                elif pos in self.unknown_cells and pos not in self.revealed_unknowns:
                    color = (222, 214, 190)
                elif cell.value is not None and cell.value > 0:
                    color = (91, 151, 91)
                elif cell.value == 0:
                    color = (175, 175, 183)
                else:
                    color = (157, 73, 67)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, (50, 48, 42), rect, 1)
                if pos == outcome:
                    pygame.draw.rect(surface, COL_AND, rect.inflate(-1, -1), 2)
                if pos == self.goal:
                    pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, rect.center,
                                       max(2, cell_size // 4))

    def _draw_trace(self, surface):
        draw_wood_panel(surface, TRACE_PANEL, border=5, corner=8, fill=(34, 28, 20))
        inner = TRACE_PANEL.inflate(-14, -12)
        header_h = 22
        widths = [52, 105, 105, 330]
        xs = [inner.left]
        for width in widths:
            xs.append(xs[-1] + width)

        pygame.draw.rect(surface, (232, 224, 198), inner, border_radius=3)
        pygame.draw.rect(surface, C.COL_WOOD_DARK, inner, 2, border_radius=3)
        for x in xs[1:]:
            pygame.draw.line(surface, C.COL_WOOD_DARK, (x, inner.top), (x, inner.bottom), 2)
        pygame.draw.line(surface, C.COL_WOOD_DARK,
                         (inner.left, inner.top + header_h),
                         (inner.right, inner.top + header_h), 2)

        headers = ("Bước", "OR Node", "Action", "AND Outcomes", "Kết quả")
        for index, text in enumerate(headers):
            draw_text(surface, text, (xs[index] + 6, inner.top + 3), size=10,
                      color=C.COL_BLACK, shadow=False)

        rows = self.trace_rows[-3:]
        if not rows:
            rows = [{"step": "0", "node": self._state_name(self.player_pos),
                     "action": "—", "and": "—", "result": "Sẵn sàng"}]
        row_h = max(30, (inner.height - header_h) // len(rows))
        y = inner.top + header_h
        for row in rows:
            pygame.draw.line(surface, (125, 112, 92), (inner.left, y), (inner.right, y), 1)
            values = (row["step"], row["node"], row["action"], row["and"], row["result"])
            for index, value in enumerate(values):
                max_width = xs[index + 1] - xs[index] - 10 if index + 1 < len(xs) else inner.right - xs[index] - 10
                draw_text(surface, value, (xs[index] + 6, y + 4), size=9,
                          color=C.COL_BLACK, shadow=False, max_width=max_width)
            y += row_h
