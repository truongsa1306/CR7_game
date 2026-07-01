"""
systems/algorithms/blind_search.py
==================================
Blind-search generators used by the gameplay scene.

Neighbor generation order is always Left, Right, Up, Down because
GridModel.neighbors follows ORTHOGONAL_DIRECTIONS in that order.
"""
from collections import deque

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


def _neighbors_lr_ud(grid, pos):
    return [(cell.col, cell.row) for cell in grid.neighbors(*pos)]


def _step(current, frontier, reached, reached_order, path=None,
          children=None, added_children=None, **extra):
    data = {
        "current": current,
        "frontier": list(frontier),
        "visited": set(reached),
        "reached_order": list(reached_order),
        "children": list(children or []),
        "added_children": list(added_children or []),
        "path": path,
    }
    data.update(extra)
    return data


def bfs_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """Breadth-first search using a FIFO queue."""
    start = grid.start if start is _UNSET else start
    goal = grid.goal if goal is _UNSET else goal

    sources = _resolve_sources(grid, start)
    frontier = deque(sources)
    reached = set(sources)
    reached_order = list(sources)
    parent = {}

    if goal is not None:
        for source in sources:
            if source == goal:
                yield _step(source, frontier, reached, reached_order, path=[source])
                return

    while frontier:
        current = frontier.popleft()
        children = _neighbors_lr_ud(grid, current)
        added_children = []

        for pos in children:
            if pos in reached:
                continue
            reached.add(pos)
            reached_order.append(pos)
            parent[pos] = current
            frontier.append(pos)
            added_children.append(pos)

            if goal is not None and pos == goal:
                yield _step(
                    current,
                    frontier,
                    reached,
                    reached_order,
                    path=_reconstruct(parent, goal),
                    children=children,
                    added_children=added_children,
                )
                return

        yield _step(
            current,
            frontier,
            reached,
            reached_order,
            path=None,
            children=children,
            added_children=added_children,
        )

    yield _step(None, [], reached, reached_order, path=[])


def dfs_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """Depth-first graph search using a LIFO stack."""
    start = grid.start if start is _UNSET else start
    goal = grid.goal if goal is _UNSET else goal

    sources = _resolve_sources(grid, start)
    stack = list(sources)
    discovered = set(sources)
    reached_order = list(sources)
    parent = {}

    while stack:
        current = stack.pop()

        if goal is not None and current == goal:
            yield _step(
                current,
                stack,
                discovered,
                reached_order,
                path=_reconstruct(parent, goal),
            )
            return

        children = _neighbors_lr_ud(grid, current)
        added_children = []
        for pos in children:
            if pos not in discovered:
                discovered.add(pos)
                reached_order.append(pos)
                parent[pos] = current
                added_children.append(pos)

        for pos in reversed(added_children):
            stack.append(pos)

        yield _step(
            current,
            stack,
            discovered,
            reached_order,
            path=None,
            children=children,
            added_children=added_children,
        )

    yield _step(None, [], discovered, reached_order, path=[])


def ids_steps(grid, start=_UNSET, goal=_UNSET, max_depth=40, health=None):
    """Iterative deepening search using depth-limited LIFO stacks."""
    start = grid.start if start is _UNSET else start
    goal = grid.goal if goal is _UNSET else goal

    sources = _resolve_sources(grid, start)
    overall_visited = set(sources)
    overall_order = list(sources)

    for depth_limit in range(max_depth + 1):
        stack = [(source, 0, None) for source in sources]
        discovered_this = set(sources)
        parent = {}

        if depth_limit > 0:
            for source in sources:
                overall_visited.add(source)
                if source not in overall_order:
                    overall_order.append(source)
            yield _step(
                None,
                [item[0] for item in stack],
                overall_visited,
                overall_order,
                path=None,
                depth_limit=depth_limit,
                restarting=True,
            )

        while stack:
            current, depth, par = stack.pop()

            if par is not None and current not in parent:
                parent[current] = par

            overall_visited.add(current)
            if current not in overall_order:
                overall_order.append(current)

            if goal is not None and current == goal:
                yield _step(
                    current,
                    [item[0] for item in stack],
                    overall_visited,
                    overall_order,
                    path=_reconstruct(parent, goal),
                    depth_limit=depth_limit,
                )
                return

            children = _neighbors_lr_ud(grid, current)
            added_children = []
            if depth < depth_limit:
                for pos in children:
                    if pos not in discovered_this:
                        discovered_this.add(pos)
                        added_children.append(pos)
                        overall_visited.add(pos)
                        if pos not in overall_order:
                            overall_order.append(pos)

                for pos in reversed(added_children):
                    stack.append((pos, depth + 1, current))

            yield _step(
                current,
                [item[0] for item in stack],
                overall_visited,
                overall_order,
                path=None,
                children=children,
                added_children=added_children,
                depth_limit=depth_limit,
            )

    yield _step(
        None,
        [],
        overall_visited,
        overall_order,
        path=[],
        depth_limit=max_depth,
    )
