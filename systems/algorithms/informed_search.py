"""
systems/algorithms/informed_search.py
=====================================
Step generators for UCS, Greedy Best-First Search, and A*.

Conventions used by level 2:
- h(n) is Manhattan distance to the goal.
- g(n) is the negative cumulative cell value collected so far.
  Positive cells reduce g; negative fire cells increase g.
- f(n) = g(n) + h(n).
- Children are generated in GridModel.neighbors order: Left, Right, Up, Down.
"""
import heapq

_UNSET = object()


def _reconstruct(parent, goal):
    path = [goal]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def _resolve_sources(grid, start):
    if start is None:
        return sorted((c, r) for (c, r), cell in grid.cells.items() if cell.passable)
    return [start]


def _heuristic(grid, pos, goal):
    if goal is None:
        return 0
    return grid.manhattan(pos, goal)


def _step_cost(grid, cell):
    if cell is None:
        return 0
    return -grid.health_delta(cell.col, cell.row)


def _in_parent_chain(parent, current, pos):
    cursor = current
    while cursor in parent:
        cursor = parent[cursor]
        if cursor == pos:
            return True
    return False


def _score_snapshot(reached):
    return {
        pos: {
            "g": data["g"],
            "h": data["h"],
            "f": data["f"],
            "health": data.get("health"),
            "priority": data.get("priority"),
        }
        for pos, data in reached.items()
    }


def _frontier_positions(frontier, reached, expanded):
    result = []
    seen = set()
    for priority, counter, pos in sorted(frontier):
        if pos in expanded or pos in seen or pos not in reached:
            continue
        if reached[pos].get("priority") != priority:
            continue
        seen.add(pos)
        result.append(pos)
    return result


def _step(current, frontier, reached, reached_order, expanded, path=None,
          children=None, added_children=None, **extra):
    data = {
        "current": current,
        "frontier": list(frontier),
        "visited": set(reached.keys()),
        "expanded": set(expanded),
        "reached_order": list(reached_order),
        "scores": _score_snapshot(reached),
        "children": list(children or []),
        "added_children": list(added_children or []),
        "path": path,
    }
    data.update(extra)
    return data


def _best_first_search(grid, priority_fn, start, goal, health=None,
                       respect_health=True):
    sources = _resolve_sources(grid, start)
    counter = 0
    reached_order = []
    reached = {}
    parent = {}
    expanded = set()
    frontier = []

    for source in sources:
        h = _heuristic(grid, source, goal)
        g_cost = 0
        f_cost = g_cost + h
        priority = priority_fn(g_cost, h, f_cost)
        reached[source] = {
            "g": g_cost,
            "h": h,
            "f": f_cost,
            "health": health,
            "priority": priority,
        }
        reached_order.append(source)
        heapq.heappush(frontier, (priority, counter, source))
        counter += 1
        cell = grid.get(*source)
        if cell is not None:
            cell.g, cell.h, cell.f = g_cost, h, f_cost

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current in expanded:
            continue

        current_entry = reached.get(current)
        if current_entry is None:
            continue
        expanded.add(current)

        if goal is not None and current == goal:
            yield _step(
                current,
                _frontier_positions(frontier, reached, expanded),
                reached,
                reached_order,
                expanded,
                path=_reconstruct(parent, goal),
            )
            return

        children = [(cell.col, cell.row) for cell in grid.neighbors(*current)]
        added_children = []

        for cell in grid.neighbors(*current):
            pos = (cell.col, cell.row)
            if pos in expanded or _in_parent_chain(parent, current, pos):
                continue

            new_g = current_entry["g"] + _step_cost(grid, cell)
            old_entry = reached.get(pos)
            if old_entry is not None and new_g >= old_entry["g"]:
                continue

            if current_entry.get("health") is None:
                new_health = None
            else:
                new_health = current_entry["health"] + grid.health_delta(*pos)
                if respect_health and new_health < 0:
                    continue

            h = _heuristic(grid, pos, goal)
            f_cost = new_g + h
            priority = priority_fn(new_g, h, f_cost)
            reached[pos] = {
                "g": new_g,
                "h": h,
                "f": f_cost,
                "health": new_health,
                "priority": priority,
            }
            if old_entry is None:
                reached_order.append(pos)
            parent[pos] = current
            cell.g, cell.h, cell.f = new_g, h, f_cost
            heapq.heappush(frontier, (priority, counter, pos))
            counter += 1
            added_children.append(pos)

        yield _step(
            current,
            _frontier_positions(frontier, reached, expanded),
            reached,
            reached_order,
            expanded,
            path=None,
            children=children,
            added_children=added_children,
        )

    yield _step(None, [], reached, reached_order, expanded, path=[])


def ucs_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    start = grid.start if start is _UNSET else start
    goal = grid.goal if goal is _UNSET else goal
    return _best_first_search(
        grid,
        priority_fn=lambda g, h, f: g,
        start=start,
        goal=goal,
        health=health,
        respect_health=True,
    )


def greedy_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    start = grid.start if start is _UNSET else start
    goal = grid.goal if goal is _UNSET else goal
    return _best_first_search(
        grid,
        priority_fn=lambda g, h, f: h,
        start=start,
        goal=goal,
        health=health,
        respect_health=False,
    )


def astar_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    start = grid.start if start is _UNSET else start
    goal = grid.goal if goal is _UNSET else goal
    return _best_first_search(
        grid,
        priority_fn=lambda g, h, f: f,
        start=start,
        goal=goal,
        health=health,
        respect_health=True,
    )
