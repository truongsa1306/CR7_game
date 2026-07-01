"""Belief-state search generators used by Level 4.

A belief state is a tuple of player positions, one position for each possible
world/map.  Every action is applied to all worlds at the same time:

* if a move is legal, that world's position changes;
* if it is blocked or outside the map, that world stays in place;
* if a world has already reached its goal, it is frozen at the goal.

Blind algorithms ignore cell values.  Informed algorithms calculate g, h and
f for every world and use the arithmetic mean of the whole belief set.
"""
from __future__ import annotations

from collections import deque
import heapq
import random
from typing import Iterable, Sequence


ACTIONS = (
    ("L", "trái", (-1, 0)),
    ("R", "phải", (1, 0)),
    ("U", "trên", (0, -1)),
    ("D", "dưới", (0, 1)),
)

BLIND = {"BFS", "DFS", "IDS"}
INFORMED = {"UCS", "Greedy", "A*"}
HILL = {"Hill Climbing", "Steepest Ascent HC", "Stochastic HC"}


def _average(values: Sequence[float]) -> float:
    return sum(values) / max(1, len(values))


def _alpha_label(index: int) -> str:
    """Return A..Z, AA..AZ, BA.. for generated belief nodes."""
    chars = []
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        chars.append(chr(ord("A") + remainder))
    return "".join(reversed(chars))


class _Labeler:
    def __init__(self, start_state):
        self.labels = {start_state: "S"}
        self.next_index = 0

    def label(self, state):
        if state not in self.labels:
            self.labels[state] = _alpha_label(self.next_index)
            self.next_index += 1
        return self.labels[state]


def is_goal_state(grids, state) -> bool:
    return all(pos == grid.goal for grid, pos in zip(grids, state))


def apply_belief_action(grids, state, delta):
    """Apply one action to all worlds and return (next_state, per-world detail)."""
    next_positions = []
    details = []
    dc, dr = delta

    for index, (grid, pos) in enumerate(zip(grids, state)):
        if pos == grid.goal:
            next_pos = pos
            moved = False
            blocked = False
            frozen = True
        else:
            target = (pos[0] + dc, pos[1] + dr)
            cell = grid.get(*target) if grid.in_bounds(*target) else None
            if cell is not None and cell.passable:
                next_pos = target
                moved = next_pos != pos
                blocked = False
            else:
                next_pos = pos
                moved = False
                blocked = True
            frozen = False

        next_positions.append(next_pos)
        details.append(
            {
                "world": index,
                "from": pos,
                "to": next_pos,
                "moved": moved,
                "blocked": blocked,
                "frozen": frozen,
                "goal": next_pos == grid.goal,
            }
        )

    return tuple(next_positions), details


def heuristic_components(grids, state):
    return tuple(
        0.0 if pos == grid.goal else float(grid.manhattan(pos, grid.goal))
        for grid, pos in zip(grids, state)
    )


def transition_cost_components(grids, details):
    """Positive per-world movement cost derived from the signed cell value.

    Better positive cells are cheaper, while negative cells are more costly.
    A blocked/frozen world contributes zero because it did not move.
    """
    costs = []
    for grid, detail in zip(grids, details):
        if not detail["moved"]:
            costs.append(0.0)
            continue
        cell = grid.get(*detail["to"])
        value = float(cell.value or 0) if cell is not None else 0.0
        costs.append(max(1.0, 5.0 - value))
    return tuple(costs)


def score_state(grids, state, g_components=None):
    h_components = heuristic_components(grids, state)
    if g_components is None:
        g_components = tuple(0.0 for _ in grids)
    f_components = tuple(g + h for g, h in zip(g_components, h_components))
    return {
        "g_components": tuple(float(v) for v in g_components),
        "h_components": h_components,
        "f_components": f_components,
        "g": _average(g_components),
        "h": _average(h_components),
        "f": _average(f_components),
    }


def _child_entries(grids, current, labeler, score_builder=None):
    entries = []
    for code, action_name, delta in ACTIONS:
        state, details = apply_belief_action(grids, current, delta)
        entry = {
            "action": code,
            "action_name": action_name,
            "state": state,
            "label": labeler.label(state),
            "details": details,
            "changed": state != current,
            "accepted": False,
            "selected": False,
        }
        if score_builder is not None:
            entry["score"] = score_builder(state, details)
        entries.append(entry)
    return entries


def _base_step(index, algorithm, current, labeler, children, **extra):
    data = {
        "belief": True,
        "index": index,
        "algorithm": algorithm,
        "current_state": current,
        "display_state": current,
        "current_label": labeler.label(current),
        "children": children,
        "goal": is_goal_state(extra.get("grids", ()), current) if extra.get("grids") else False,
        "stuck": False,
        "loop": False,
    }
    data.update(extra)
    data.pop("grids", None)
    return data


def _blind_steps(grids, start, algorithm, max_depth=40):
    """Generate blind-search steps with textbook table semantics.

    ``frontier`` contains nodes that have been generated but are still waiting
    to be examined. ``reached`` contains only nodes whose expansion has
    finished (the closed set). Successor details remain in ``children`` and are
    never mixed into the reached column.
    """
    labeler = _Labeler(start)
    step_index = 0

    if algorithm == "BFS":
        frontier = deque([start])
        discovered = {start}
        expanded_order = []
        parent = {}
        parent_action = {}

        while frontier:
            current = frontier.popleft()
            if current not in expanded_order:
                expanded_order.append(current)

            if is_goal_state(grids, current):
                yield _base_step(
                    step_index, algorithm, current, labeler, [], grids=grids,
                    frontier=[labeler.label(s) for s in frontier],
                    reached=[labeler.label(s) for s in expanded_order],
                    goal=True,
                    path=_reconstruct_belief_path(parent, parent_action, current),
                )
                return

            children = _child_entries(grids, current, labeler)
            for child in children:
                state = child["state"]
                if state == current or state in discovered:
                    continue
                discovered.add(state)
                parent[state] = current
                parent_action[state] = child["action"]
                frontier.append(state)
                child["accepted"] = True

            yield _base_step(
                step_index, algorithm, current, labeler, children, grids=grids,
                frontier=[labeler.label(s) for s in frontier],
                reached=[labeler.label(s) for s in expanded_order],
            )
            step_index += 1

    elif algorithm == "DFS":
        stack = [start]
        discovered = {start}
        expanded_order = []
        parent = {}
        parent_action = {}

        while stack:
            current = stack.pop()
            if current not in expanded_order:
                expanded_order.append(current)

            if is_goal_state(grids, current):
                yield _base_step(
                    step_index, algorithm, current, labeler, [], grids=grids,
                    frontier=[labeler.label(s) for s in stack],
                    reached=[labeler.label(s) for s in expanded_order],
                    goal=True,
                    path=_reconstruct_belief_path(parent, parent_action, current),
                )
                return

            children = _child_entries(grids, current, labeler)
            accepted = []
            for child in children:
                state = child["state"]
                if state == current or state in discovered:
                    continue
                discovered.add(state)
                parent[state] = current
                parent_action[state] = child["action"]
                child["accepted"] = True
                accepted.append(state)
            for state in reversed(accepted):
                stack.append(state)

            yield _base_step(
                step_index, algorithm, current, labeler, children, grids=grids,
                frontier=[labeler.label(s) for s in stack],
                reached=[labeler.label(s) for s in expanded_order],
            )
            step_index += 1

    else:  # IDS
        for depth_limit in range(max_depth + 1):
            stack = [(start, 0, frozenset({start}))]
            expanded_order = []
            expanded_set = set()
            restarting = depth_limit > 0

            while stack:
                current, depth, path_states = stack.pop()
                if current in expanded_set:
                    continue
                expanded_set.add(current)
                expanded_order.append(current)

                if is_goal_state(grids, current):
                    yield _base_step(
                        step_index, algorithm, current, labeler, [], grids=grids,
                        frontier=[labeler.label(item[0]) for item in stack],
                        reached=[labeler.label(s) for s in expanded_order],
                        goal=True,
                        depth_limit=depth_limit,
                        restarting=restarting,
                    )
                    return

                children = _child_entries(grids, current, labeler)
                accepted = []
                if depth < depth_limit:
                    for child in children:
                        state = child["state"]
                        if state == current or state in path_states or state in expanded_set:
                            continue
                        child["accepted"] = True
                        accepted.append((state, depth + 1, path_states | {state}))
                    for item in reversed(accepted):
                        stack.append(item)

                yield _base_step(
                    step_index, algorithm, current, labeler, children, grids=grids,
                    frontier=[labeler.label(item[0]) for item in stack],
                    reached=[labeler.label(s) for s in expanded_order],
                    depth_limit=depth_limit,
                    restarting=restarting,
                )
                restarting = False
                step_index += 1

    yield {
        "belief": True,
        "index": step_index,
        "algorithm": algorithm,
        "current_state": start,
        "display_state": start,
        "current_label": "S",
        "children": [],
        "frontier": [],
        "reached": [],
        "goal": False,
        "stuck": True,
        "loop": False,
    }

def _priority_for(algorithm, score):
    return {"UCS": score["g"], "Greedy": score["h"], "A*": score["f"]}[algorithm]


def _informed_steps(grids, start, algorithm):
    """Generate UCS/Greedy/A* steps with separate open and closed sets."""
    labeler = _Labeler(start)
    counter = 0
    step_index = 0
    start_score = score_state(grids, start)

    best_scores = {start: start_score}
    expanded = set()
    expanded_order = []
    parent = {}
    parent_action = {}
    frontier = [(_priority_for(algorithm, start_score), counter, start)]
    counter += 1

    def frontier_snapshot():
        """Return active open nodes once, ordered by the heap priority."""
        active = []
        seen = set()
        for priority, order, state in sorted(frontier):
            if state in expanded or state in seen:
                continue
            score = best_scores.get(state)
            if score is None or priority != _priority_for(algorithm, score):
                continue
            seen.add(state)
            active.append({"label": labeler.label(state), "score": score})
        return active

    while frontier:
        priority, _, current = heapq.heappop(frontier)
        if current in expanded:
            continue
        current_score = best_scores.get(current)
        if current_score is None or priority != _priority_for(algorithm, current_score):
            continue

        expanded.add(current)
        expanded_order.append(current)

        if is_goal_state(grids, current):
            open_nodes = frontier_snapshot()
            yield _base_step(
                step_index, algorithm, current, labeler, [], grids=grids,
                score=current_score,
                frontier=[item["label"] for item in open_nodes],
                frontier_entries=open_nodes,
                reached=[labeler.label(s) for s in expanded_order],
                goal=True,
                path=_reconstruct_belief_path(parent, parent_action, current),
            )
            return

        def build_score(state, details):
            step_costs = transition_cost_components(grids, details)
            new_g = tuple(
                g + cost for g, cost in zip(current_score["g_components"], step_costs)
            )
            return score_state(grids, state, new_g)

        children = _child_entries(grids, current, labeler, build_score)
        for child in children:
            state = child["state"]
            if state == current or state in expanded:
                continue
            candidate = child["score"]
            old = best_scores.get(state)
            if old is not None and candidate["g"] >= old["g"]:
                continue
            best_scores[state] = candidate
            parent[state] = current
            parent_action[state] = child["action"]
            heapq.heappush(frontier, (_priority_for(algorithm, candidate), counter, state))
            counter += 1
            child["accepted"] = True

        open_nodes = frontier_snapshot()
        yield _base_step(
            step_index, algorithm, current, labeler, children, grids=grids,
            score=current_score,
            frontier=[item["label"] for item in open_nodes],
            frontier_entries=open_nodes,
            reached=[labeler.label(s) for s in expanded_order],
        )
        step_index += 1

    yield {
        "belief": True,
        "index": step_index,
        "algorithm": algorithm,
        "current_state": start,
        "display_state": start,
        "current_label": "S",
        "children": [],
        "frontier": [],
        "frontier_entries": [],
        "reached": [labeler.label(s) for s in expanded_order],
        "goal": False,
        "stuck": True,
        "loop": False,
    }

def _hill_steps(grids, start, algorithm, rng):
    labeler = _Labeler(start)
    current = start
    current_g = tuple(0.0 for _ in grids)
    visited = {start}
    step_index = 0

    while True:
        current_score = score_state(grids, current, current_g)
        if is_goal_state(grids, current):
            yield _base_step(
                step_index, algorithm, current, labeler, [], grids=grids,
                score=current_score,
                reached=[labeler.label(s) for s in visited],
                goal=True,
            )
            return

        def build_score(state, details):
            costs = transition_cost_components(grids, details)
            next_g = tuple(g + cost for g, cost in zip(current_g, costs))
            return score_state(grids, state, next_g)

        children = _child_entries(grids, current, labeler, build_score)
        improving = [
            child for child in children
            if child["state"] != current and child["score"]["h"] < current_score["h"]
        ]

        selected = None
        if algorithm == "Hill Climbing":
            selected = improving[0] if improving else None
        elif algorithm == "Steepest Ascent HC":
            selected = min(improving, key=lambda item: item["score"]["h"]) if improving else None
        else:
            selected = rng.choice(improving) if improving else None

        if selected is None:
            yield _base_step(
                step_index, algorithm, current, labeler, children, grids=grids,
                score=current_score,
                reached=[labeler.label(s) for s in visited],
                stuck=True,
            )
            return

        selected["selected"] = True
        selected["accepted"] = True
        next_state = selected["state"]
        loop = next_state in visited
        yield _base_step(
            step_index, algorithm, current, labeler, children, grids=grids,
            display_state=next_state,
            next_state=next_state,
            next_label=selected["label"],
            score=current_score,
            selected_score=selected["score"],
            reached=[labeler.label(s) for s in visited] + [selected["label"]],
            loop=loop,
        )
        if loop:
            return

        current = next_state
        current_g = selected["score"]["g_components"]
        visited.add(current)
        step_index += 1


def _reconstruct_belief_path(parent, parent_action, goal):
    actions = []
    states = [goal]
    cursor = goal
    while cursor in parent:
        actions.append(parent_action[cursor])
        cursor = parent[cursor]
        states.append(cursor)
    states.reverse()
    actions.reverse()
    return {"states": states, "actions": actions}


def belief_search_steps(grids, starts, algorithm, rng=None, max_depth=40):
    """Create a step generator for a belief-state search algorithm."""
    grids = tuple(grids)
    starts = tuple(starts)
    if not grids or len(grids) != len(starts):
        raise ValueError("Belief state must contain the same number of grids and starts")
    if algorithm not in BLIND | INFORMED | HILL:
        raise ValueError(f"Unsupported belief algorithm: {algorithm}")

    if algorithm in BLIND:
        return _blind_steps(grids, starts, algorithm, max_depth=max_depth)
    if algorithm in INFORMED:
        return _informed_steps(grids, starts, algorithm)
    return _hill_steps(grids, starts, algorithm, rng or random.Random())
