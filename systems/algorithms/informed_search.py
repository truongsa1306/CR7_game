"""
systems/algorithms/informed_search.py
=======================================
Tìm kiếm có thông tin (cost-aware): UCS, Greedy Best-First, A*.

Cell.g / .h / .f được ghi trực tiếp vào GridModel để gameplay_scene
có thể đọc và hiển thị trên side panel mà không cần truyền thêm state.

Quy ước chi phí: đi vào một ô tốn abs(cell.cost) đơn vị năng lượng.
(cell.cost âm, ví dụ fire = -20, nên ta lấy abs để ra số dương.)

Mã giả AIMA cho BEST-FIRST-SEARCH:
────────────────────────────────────
function BEST-FIRST-SEARCH(problem, f):
    node ← Node(problem.INITIAL)
    frontier ← priority queue ordered by f, with node
    reached  ← table với {problem.INITIAL: node}
    loop:
        if EMPTY(frontier): return failure
        node ← POP(frontier)           # node có f nhỏ nhất
        if problem.IS-GOAL(node.STATE): return node
        for child in EXPAND(problem, node):
            s ← child.STATE
            if s ∉ reached or child.PATH-COST < reached[s].PATH-COST:
                reached[s] ← child
                add child to frontier

Sự khác biệt giữa UCS / Greedy / A*:
  UCS    : f(n) = g(n)          → mở rộng node có chi phí thực nhỏ nhất
  Greedy : f(n) = h(n)          → mở rộng node gần goal nhất (theo ước tính)
  A*     : f(n) = g(n) + h(n)   → cân bằng chi phí thực & ước tính

Tham số start / goal
---------------------
_UNSET sentinel cho phép truyền None với nghĩa rõ ràng:

  * goal=None  → không có trạng thái đích.
                 h(n) = 0 với mọi n (vì không có gì để ước tính khoảng
                 cách đến đích). Hệ quả:
                   - Greedy với h=0 duyệt frontier thuần túy theo thứ tự push
                   - A*    với h=0 degenerates thành UCS (đúng lý thuyết AI)
                 Khi hết frontier, trả về path=[] (không có đường đến đích).

  * start=None → không có trạng thái bắt đầu: mọi ô passable được khởi
                 tạo vào frontier với g=0 (multi-source search).
"""
import heapq

_UNSET = object()


# ─── Hàm hỗ trợ ──────────────────────────────────────────────────

def _reconstruct(parent, goal):
    """Truy vết đường đi từ dict cha."""
    path = [goal]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def _resolve_sources(grid, start):
    """Trả về tập nguồn ban đầu.
    start=None → mọi ô passable (no-initial-state / multi-source).
    """
    if start is None:
        return {(c, r) for (c, r), cell in grid.cells.items() if cell.passable}
    return {start}


def _heuristic(grid, pos, goal):
    """Heuristic used by Greedy and A*.

    h(n) = Manhattan distance to the goal.
    Bằng 0 nếu goal=None.
    """
    if goal is None:
        return 0
    return grid.manhattan(pos, goal)


def _step_cost(grid, cell):
    """Chi phí bước đi vào ô cho g(n).

    g(n) là âm của tổng điểm tích lũy khi đi qua các ô.
    Nếu ô gây tổn hại (giá trị âm), chi phí tăng lên.
    Nếu ô cộng điểm (giá trị dương), chi phí giảm.
    """
    if cell is None:
        return 0
    return -grid.health_delta(cell.col, cell.row)


# ─── Driver chung ─────────────────────────────────────────────────

def _best_first_search(grid, priority_fn, start, goal, health=None):
    """
    Driver dùng chung cho UCS / Greedy / A*.
    priority_fn(grid, pos, g_cost, goal) → số thực (ưu tiên nhỏ hơn = tốt hơn).

    Điểm khác biệt chính so với phiên bản cũ:
    - Thêm tham số start/goal với sentinel _UNSET
    - Xử lý multi-source (start=None)
    - Xử lý goal=None (exhaustive traversal, h=0)
    - Sửa bug: visited set dùng để skip các node đã pop, không phải
      skip các node đã push → đúng với mã giả AIMA (reached table)
    """
    sources = _resolve_sources(grid, start)
    counter = 0                         # tie-breaker cho heapq
    reached = {
        s: {"g": 0, "health": health} for s in sources
    } if health is not None else {s: {"g": 0, "health": None} for s in sources}
    parent  = {}
    visited = set()                     # đã pop và mở rộng

    # Khởi tạo frontier với tất cả nguồn
    frontier = []
    for s in sources:
        h = _heuristic(grid, s, goal)
        priority = priority_fn(grid, s, 0, goal)
        heapq.heappush(frontier, (priority, counter, s))
        counter += 1
        cell = grid.get(*s)
        if cell:
            cell.g, cell.h, cell.f = 0, h, h

    while frontier:
        _, _, current = heapq.heappop(frontier)

        # Bỏ qua nếu đã được mở rộng (lazy deletion)
        if current in visited:
            continue
        visited.add(current)

        # Kiểm tra goal (sau khi pop – đúng với AIMA BEST-FIRST)
        if goal is not None and current == goal:
            yield {"current": current,
                   "frontier": [f[2] for f in frontier],
                   "visited":  visited,
                   "path":     _reconstruct(parent, goal)}
            return

        # Mở rộng node
        for cell in grid.neighbors(*current):
            pos        = (cell.col, cell.row)
            current_entry = reached[current]
            new_g      = current_entry["g"] + _step_cost(grid, cell)
            old_entry  = reached.get(pos)
            if old_entry is not None and new_g >= old_entry["g"]:
                continue
            if health is not None:
                new_health = current_entry["health"] + grid.health_delta(*pos)
                if new_health < 0:
                    continue
            else:
                new_health = None
            reached[pos] = {"g": new_g, "health": new_health}
            parent[pos]   = current
            h             = _heuristic(grid, pos, goal)
            cell.g, cell.h, cell.f = new_g, h, new_g + h
            priority      = priority_fn(grid, pos, new_g, goal)
            counter      += 1
            heapq.heappush(frontier, (priority, counter, pos))

        yield {"current": current,
               "frontier": [f[2] for f in frontier],
               "visited":  visited,
               "path":     None}

    # Hết frontier – không có đường đến đích (hoặc goal=None, duyệt xong)
    yield {"current": None, "frontier": [], "visited": visited, "path": []}


# ─── Public API ───────────────────────────────────────────────────

def ucs_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """Uniform Cost Search – f(n) = g(n).
    Đảm bảo tìm đường đi có tổng chi phí nhỏ nhất.
    """
    start = grid.start if start is _UNSET else start
    goal  = grid.goal  if goal  is _UNSET else goal
    return _best_first_search(
        grid,
        priority_fn=lambda g, pos, cost, gl: cost,
        start=start,
        goal=goal,
        health=health,
    )


def greedy_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """Greedy Best-First Search – f(n) = h(n).
    Luôn ưu tiên node trông có vẻ gần goal nhất; nhanh nhưng không
    đảm bảo optimal. Khi goal=None, h=0 nên hoạt động như duyệt FIFO heap.
    """
    start = grid.start if start is _UNSET else start
    goal  = grid.goal  if goal  is _UNSET else goal
    return _best_first_search(
        grid,
        priority_fn=lambda g, pos, cost, gl: _heuristic(g, pos, gl),
        start=start,
        goal=goal,
        health=health,
    )


def astar_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """A* Search – f(n) = g(n) + h(n).
    Kết hợp chi phí thực và ước tính; optimal nếu h admissible.
    Khi goal=None → h=0 → A* degenerates thành UCS (đúng lý thuyết).
    """
    start = grid.start if start is _UNSET else start
    goal  = grid.goal  if goal  is _UNSET else goal
    return _best_first_search(
        grid,
        priority_fn=lambda g, pos, cost, gl: cost + _heuristic(g, pos, gl),
        start=start,
        goal=goal,
        health=health,
    )
