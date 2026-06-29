"""
systems/algorithms/__init__.py
================================
Registry duy nhất để scene có thể gọi ALGORITHM_REGISTRY["A*"](grid)
mà không cần biết submodule nào chứa implementation.

Lưu ý: các hàm trong registry đều nhận grid là tham số bắt buộc,
và start/goal là tham số tùy chọn với giá trị mặc định từ grid.
"""
from systems.algorithms.blind_search import bfs_steps, dfs_steps, ids_steps
from systems.algorithms.informed_search import ucs_steps, greedy_steps, astar_steps
from systems.algorithms.hill_climbing import (
    simple_hill_climbing_steps,
    steepest_ascent_hill_climbing_steps,
    stochastic_hill_climbing_steps,
    simulated_annealing_steps,
    ALGORITHMS_HILLCLIMB,
)

ALGORITHM_REGISTRY = {
    "BFS":                 bfs_steps,
    "DFS":                 dfs_steps,
    "IDS":                 ids_steps,
    "UCS":                 ucs_steps,
    "Greedy":              greedy_steps,
    "A*":                  astar_steps,
    "Hill Climbing":       simple_hill_climbing_steps,
    "Steepest Ascent HC":  steepest_ascent_hill_climbing_steps,
    "Stochastic HC":       stochastic_hill_climbing_steps,
    "Simulated Annealing": simulated_annealing_steps,
}

# Thuật toán dùng local-search step shape (current/neighbor_scores/chosen/stuck)
# thay vì graph-search shape (current/frontier/visited)
LOCAL_SEARCH_ALGORITHMS = frozenset({
    "Hill Climbing",
    "Steepest Ascent HC",
    "Stochastic HC",
    "Simulated Annealing",
})

# Thuật toán hỗ trợ chế độ "không có trạng thái đích" (goal=None)
NO_GOAL_SUPPORTED = frozenset({
    "BFS", "DFS", "IDS",
    "UCS", "Greedy", "A*",
})

# Thuật toán hỗ trợ chế độ "không có trạng thái bắt đầu" (start=None)
NO_START_SUPPORTED = frozenset(ALGORITHM_REGISTRY.keys())
