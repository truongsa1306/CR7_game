"""
systems/algorithms/blind_search.py
=====================================
Uninformed ("blind") search: BFS, DFS, Iterative Deepening Search (IDS).

Mỗi hàm là một generator, cho phép gameplay_scene tiến từng bước một hoặc
chạy liên tục (Auto). Không có lời gọi reveal_around ở đây – scene tự quản
lý sương mù sau mỗi lần di chuyển người chơi.

Mỗi bước yield một dict:
    {
        "current"  : (col, row),           # nút đang được mở rộng
        "frontier" : [(col,row), ...],     # hàng đợi / ngăn xếp hiện tại
        "visited"  : {(col,row), ...},     # tập đã phát hiện (bao gồm frontier)
        "path"     : None hoặc [(col,row), ...]   # chỉ đặt ở bước cuối
    }

Tham số start / goal
---------------------
Mặc định lấy từ grid.start / grid.goal (sử dụng sentinel _UNSET nên
việc truyền None có nghĩa thật sự là "không có trạng thái bắt đầu /
không có trạng thái đích").

  * goal=None  → không có trạng thái đích: thuật toán duyệt toàn bộ đồ
                 thị (exhaustive traversal) thay vì dừng sớm. Trả về
                 path=[] (rỗng) khi hết frontier, thay vì path đến đích.

  * start=None → không có trạng thái bắt đầu: multi-source search, tất
                 cả ô có thể đi (passable) đều được khởi tạo đồng thời
                 vào frontier với cost 0.
"""
from collections import deque

# --- Sentinel để phân biệt "không truyền" vs "truyền None" ---
_UNSET = object()


def _reconstruct(parent, goal):
    """Truy vết đường đi từ dict cha."""
    path = [goal]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def _resolve_sources(grid, start):
    """Trả về tập nguồn ban đầu.

    - start là tuple cụ thể → {start}   (trường hợp thông thường)
    - start là None          → mọi ô passable (multi-source / no initial state)
    """
    if start is None:
        return {(c, r) for (c, r), cell in grid.cells.items() if cell.passable}
    return {start}


# ══════════════════════════════════════════════════════════════════
# BFS – Breadth-First Search
# Mã giả AIMA:
#   function BFS(problem):
#       node ← Node(problem.INITIAL)
#       if problem.IS-GOAL(node.STATE): return node
#       frontier ← FIFO queue với node
#       reached  ← {problem.INITIAL}
#       loop:
#           if EMPTY(frontier): return failure
#           node ← POP(frontier)
#           for child in EXPAND(problem, node):
#               s ← child.STATE
#               if problem.IS-GOAL(s): return child
#               if s ∉ reached:
#                   reached.add(s)
#                   frontier.add(child)
# ══════════════════════════════════════════════════════════════════
def bfs_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """BFS – đảm bảo tìm đường đi ngắn nhất (số bước) trong lưới không
    trọng số. Dùng FIFO queue (deque).
    
    Quy trình:
    1. Thêm start vào frontier (queue) và reached
    2. Pop từ đầu queue (FIFO)
    3. Sinh neighbors (L,R,U,D) 
    4. Thêm neighbors chưa thăm vào reached và queue
    5. Yield trạng thái sau mỗi bước expand
    """
    start = grid.start if start is _UNSET else start
    goal  = grid.goal  if goal  is _UNSET else goal

    sources = _resolve_sources(grid, start)
    frontier = deque(sources)          # FIFO queue
    reached  = set(sources)            # tập đã phát hiện
    parent   = {}                      # truy vết đường đi

    # Kiểm tra goal ngay từ nguồn
    if goal is not None:
        for s in sources:
            if s == goal:
                yield {"current": s, "frontier": list(frontier),
                       "visited": set(reached), "path": [s]}
                return

    while frontier:
        current = frontier.popleft()   # POP từ đầu (FIFO)

        # Expand: sinh neighbors theo thứ tự L, R, U, D
        for cell in grid.neighbors(*current):
            pos = (cell.col, cell.row)
            if pos in reached:
                continue
            # Thêm vào reached khi PHÁT HIỆN (không chờ dequeue)
            reached.add(pos)
            parent[pos] = current
            frontier.append(pos)       # thêm vào cuối queue

            # Kiểm tra goal khi phát hiện (early-exit)
            if goal is not None and pos == goal:
                yield {"current": current, "frontier": list(frontier),
                       "visited": set(reached),
                       "path": _reconstruct(parent, goal)}
                return

        # Yield sau khi expand node hiện tại
        yield {"current": current, "frontier": list(frontier),
               "visited": set(reached), "path": None}

    # Hết frontier mà không tìm thấy goal
    yield {"current": None, "frontier": [], "visited": set(reached), "path": []}


# ══════════════════════════════════════════════════════════════════
# DFS – Depth-First Search
# Mã giả AIMA (graph-search version):
#   function DFS(problem):
#       frontier ← LIFO stack với Node(problem.INITIAL)
#       reached  ← {}
#       loop:
#           if EMPTY(frontier): return failure
#           node ← POP(frontier)
#           if problem.IS-GOAL(node.STATE): return node
#           if node.STATE ∉ reached:
#               reached.add(node.STATE)
#               for child in EXPAND(problem, node):
#                   frontier.push(child)
# ══════════════════════════════════════════════════════════════════
def dfs_steps(grid, start=_UNSET, goal=_UNSET, health=None):
    """DFS – dùng LIFO stack, đi sâu một hướng trước. 
    Tương tự BFS nhưng pop từ cuối stack (LIFO) thay vì đầu queue (FIFO).
    
    Quy trình:
    1. Thêm start vào stack và discovered
    2. Pop từ cuối stack (LIFO)
    3. Sinh neighbors (L,R,U,D)
    4. Thêm neighbors chưa thăm vào discovered và push vào stack
    5. Yield trạng thái sau mỗi bước expand
    """
    start = grid.start if start is _UNSET else start
    goal  = grid.goal  if goal  is _UNSET else goal

    sources = _resolve_sources(grid, start)
    stack   = list(sources)            # LIFO stack (append/pop)
    discovered = set(sources)          # mark nodes on discovery
    parent  = {}

    while stack:
        current = stack.pop()          # POP từ cuối (LIFO)

        # Kiểm tra goal (sau khi pop – khớp mã giả graph DFS)
        if goal is not None and current == goal:
            yield {"current": current, "frontier": list(stack),
                   "visited": set(discovered),
                   "path": _reconstruct(parent, goal)}
            return

        for cell in grid.neighbors(*current):
            pos = (cell.col, cell.row)
            if pos not in discovered:
                discovered.add(pos)
                parent[pos] = current
                stack.append(pos)      # push lên stack

        yield {"current": current, "frontier": list(stack),
               "visited": set(discovered), "path": None}

    yield {"current": None, "frontier": [], "visited": set(discovered), "path": []}


# ══════════════════════════════════════════════════════════════════
# IDS – Iterative Deepening Depth-First Search
# Mã giả AIMA:
#   function ITERATIVE-DEEPENING-SEARCH(problem):
#       for depth = 0 to ∞:
#           result ← DEPTH-LIMITED-SEARCH(problem, depth)
#           if result ≠ cutoff: return result
#
#   function DEPTH-LIMITED-SEARCH(problem, l):
#       frontier ← LIFO stack với Node(problem.INITIAL)
#       result   ← failure
#       loop:
#           if EMPTY(frontier): return result
#           node ← POP(frontier)
#           if problem.IS-GOAL(node.STATE): return node
#           if DEPTH(node) > l: result ← cutoff
#           elif not IS-CYCLE(node):
#               for child in EXPAND(problem, node):
#                   frontier.push(child)
# ══════════════════════════════════════════════════════════════════
def ids_steps(grid, start=_UNSET, goal=_UNSET, max_depth=40, health=None):
    """IDS – kết hợp ưu điểm BFS (optimal) và DFS (ít bộ nhớ).
    Depth limit tăng dần 0, 1, 2, … cho đến khi tìm thấy goal.
    Mỗi vòng lặp depth_limit sẽ RESTART từ đầu để demo từng độ sâu.
    overall_visited tích lũy để visualize các bước đã mở rộng."""
    start = grid.start if start is _UNSET else start
    goal  = grid.goal  if goal  is _UNSET else goal

    sources         = _resolve_sources(grid, start)
    overall_visited = set(sources)  # Tích lũy qua các vòng

    for depth_limit in range(max_depth + 1):
        # RESTART từ đầu cho mỗi depth limit (demo từng độ sâu)
        # Stack chứa (pos, depth, parent_pos)
        stack           = [(s, 0, None) for s in sources]
        discovered_this = set(sources)   # chống lặp vô hạn trong 1 vòng
        parent          = {}

        # Đầu vòng: yield state khởi tạo để biểu thị restart
        if depth_limit > 0:
            for source in sources:
                overall_visited.add(source)
            yield {"current": None,
                   "frontier": [s[0] for s in stack],
                   "visited":  set(overall_visited),
                   "path":     None,
                   "depth_limit": depth_limit,
                   "restarting": True}

        while stack:
            current, depth, par = stack.pop()

            # Ghi nhận parent lần đầu gặp
            if par is not None and current not in parent:
                parent[current] = par

            overall_visited.add(current)

            # Kiểm tra goal
            if goal is not None and current == goal:
                yield {"current": current,
                       "frontier": [s[0] for s in stack],
                       "visited":  set(overall_visited),
                       "path":     _reconstruct(parent, goal),
                       "depth_limit": depth_limit}
                return

            # Không mở rộng nếu đã đạt giới hạn độ sâu (cutoff)
            if depth < depth_limit:
                for cell in grid.neighbors(*current):
                    pos = (cell.col, cell.row)
                    if pos not in discovered_this:
                        discovered_this.add(pos)
                        stack.append((pos, depth + 1, current))

            yield {"current": current,
                   "frontier":    [s[0] for s in stack],
                   "visited":     set(overall_visited),
                   "path":        None,
                   "depth_limit": depth_limit}

        # Mỗi depth limit kết thúc thì quay lại từ start,
        # vẫn giữ overall_visited để visualize các bước đã mở rộng.

    # Vượt max_depth mà không tìm thấy
    yield {"current": None, "frontier": [], "visited": overall_visited,
           "path": [], "depth_limit": max_depth}
