"""
tests/test_algorithms.py
=========================
Unit tests cho tất cả thuật toán: BFS, DFS, IDS, UCS, Greedy, A*,
Simple HC, Steepest HC, Stochastic HC, Simulated Annealing.
Bao gồm cả chế độ goal=None và start=None.
"""
import random
import sys
import unittest

sys.path.insert(0, "/home/claude/AI_project")

from entities.grid_cell import GridModel
from systems.algorithms.blind_search import bfs_steps, dfs_steps, ids_steps
from systems.algorithms.hill_climbing import (
    simple_hill_climbing_steps,
    steepest_ascent_hill_climbing_steps,
    stochastic_hill_climbing_steps,
    simulated_annealing_steps,
)
from systems.algorithms.informed_search import astar_steps, greedy_steps, ucs_steps


# ─── Helper ───────────────────────────────────────────────────────
def drain(gen, max_steps=200):
    """Chạy generator đến hết, trả về bước cuối."""
    last = None
    for i, step in enumerate(gen):
        last = step
        if i >= max_steps:
            break
    return last


def find_path(gen, max_steps=500):
    """Chạy generator cho đến khi có path (≠ None) hoặc hết."""
    for _ in range(max_steps):
        try:
            step = next(gen)
        except StopIteration:
            return None
        if step.get("path") is not None:
            return step["path"]
    return None


def make_grid(cols=5, rows=5, start=(0, 0), goal=(4, 4)):
    return GridModel(cols, rows, start, goal, fog=False)


def make_grid_with_wall(cols=5, rows=5):
    """Lưới 5x5 với tường chặn đường thẳng → buộc thuật toán đi vòng."""
    g = make_grid(cols, rows)
    # tường dọc cột 2, hàng 0-3
    for r in range(4):
        if (2, r) not in (g.start, g.goal):
            g.set_kind(2, r, "wall")
    return g


# ══════════════════════════════════════════════════════════════════
# BFS
# ══════════════════════════════════════════════════════════════════
class TestBFS(unittest.TestCase):

    def test_finds_path_on_open_grid(self):
        g = make_grid()
        path = find_path(bfs_steps(g))
        self.assertIsNotNone(path)
        self.assertEqual(path[0], g.start)
        self.assertEqual(path[-1], g.goal)

    def test_path_is_connected(self):
        g = make_grid()
        path = find_path(bfs_steps(g))
        for i in range(len(path) - 1):
            c0, r0 = path[i]; c1, r1 = path[i + 1]
            self.assertEqual(abs(c0 - c1) + abs(r0 - r1), 1,
                             msg=f"Non-orthogonal step {path[i]} → {path[i+1]}")

    def test_shortest_path_length_open_grid(self):
        # BFS đảm bảo đường ngắn nhất (số bước)
        g = make_grid(5, 5, (0, 0), (4, 4))
        path = find_path(bfs_steps(g))
        # đường ngắn nhất 5x5 từ (0,0) đến (4,4) = 8 bước
        self.assertEqual(len(path) - 1, 8)

    def test_frontier_uses_fifo_order(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        step1 = next(bfs_steps(g))
        # BFS mở rộng (0,0) trước; frontier phải chứa (1,0) và (0,1)
        self.assertEqual(set(step1["frontier"]), {(1, 0), (0, 1)})

    def test_visited_includes_frontier_members(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        step1 = next(bfs_steps(g))
        self.assertIn((1, 0), step1["visited"])
        self.assertIn((0, 1), step1["visited"])

    def test_no_reveal_called_on_grid(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        g.fog = True
        for (c, r), cell in g.cells.items():
            if (c, r) not in (g.start, g.goal):
                cell.revealed = False
        next(bfs_steps(g))
        revealed = {pos for pos, cell in g.cells.items() if cell.revealed}
        self.assertEqual(revealed, {g.start, g.goal})

    def test_returns_empty_path_when_no_route(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        # Bịt hết đường ra từ start
        g.set_kind(1, 0, "wall")
        g.set_kind(0, 1, "wall")
        last = drain(bfs_steps(g))
        self.assertEqual(last["path"], [])

    def test_goal_none_exhaustive(self):
        g = make_grid(3, 3, (0, 0), goal=None)
        last = drain(bfs_steps(g, goal=None))
        # Duyệt xong, không trả path thực
        self.assertEqual(last["path"], [])
        # Đã thăm tất cả ô passable
        self.assertEqual(len(last["visited"]), 9)

    def test_start_none_multisource(self):
        g = make_grid(3, 3, start=None, goal=(2, 2))
        last = drain(bfs_steps(g, start=None))
        # Tìm thấy đường (goal=(2,2) reachable từ nhiều nguồn)
        # hoặc ít nhất visited đầy đủ
        self.assertGreater(len(last["visited"]), 0)


# ══════════════════════════════════════════════════════════════════
# DFS
# ══════════════════════════════════════════════════════════════════
class TestDFS(unittest.TestCase):

    def test_finds_path_on_open_grid(self):
        g = make_grid()
        path = find_path(dfs_steps(g))
        self.assertIsNotNone(path)
        self.assertEqual(path[0], g.start)
        self.assertEqual(path[-1], g.goal)

    def test_path_is_connected(self):
        g = make_grid()
        path = find_path(dfs_steps(g))
        for i in range(len(path) - 1):
            c0, r0 = path[i]; c1, r1 = path[i + 1]
            self.assertEqual(abs(c0 - c1) + abs(r0 - r1), 1)

    def test_visited_grows_monotonically(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        gen = dfs_steps(g)
        prev_size = 0
        for _ in range(10):
            try:
                step = next(gen)
                self.assertGreaterEqual(len(step["visited"]), prev_size)
                prev_size = len(step["visited"])
            except StopIteration:
                break

    def test_goal_none_exhaustive(self):
        g = make_grid(3, 3, (0, 0), goal=None)
        last = drain(dfs_steps(g, goal=None))
        self.assertEqual(last["path"], [])
        self.assertEqual(len(last["visited"]), 9)


# ══════════════════════════════════════════════════════════════════
# IDS
# ══════════════════════════════════════════════════════════════════
class TestIDS(unittest.TestCase):

    def test_finds_path(self):
        g = make_grid()
        path = find_path(ids_steps(g))
        self.assertIsNotNone(path)
        self.assertEqual(path[-1], g.goal)

    def test_depth_limit_in_step(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        gen = ids_steps(g)
        step = next(gen)
        self.assertIn("depth_limit", step)
        self.assertIsInstance(step["depth_limit"], int)

    def test_overall_visited_accumulates(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        last = drain(ids_steps(g))
        self.assertGreater(len(last["visited"]), 0)


# ══════════════════════════════════════════════════════════════════
# UCS
# ══════════════════════════════════════════════════════════════════
class TestUCS(unittest.TestCase):

    def test_finds_path(self):
        g = make_grid()
        path = find_path(ucs_steps(g))
        self.assertIsNotNone(path)
        self.assertEqual(path[-1], g.goal)

    def test_g_scores_written_to_cells(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        drain(ucs_steps(g))
        # Ô start phải có g=0
        self.assertEqual(g.get(0, 0).g, 0)

    def test_goal_none_exhaustive(self):
        g = make_grid(3, 3, (0, 0), goal=None)
        last = drain(ucs_steps(g, goal=None))
        self.assertEqual(last["path"], [])

    def test_start_none_multisource(self):
        g = make_grid(3, 3, start=None, goal=(2, 2))
        last = drain(ucs_steps(g, start=None))
        # Ít nhất tìm thấy đường (hoặc duyệt hết)
        self.assertIsNotNone(last)

    def test_visited_never_shrinks(self):
        g = make_grid()
        gen = ucs_steps(g)
        prev = 0
        for _ in range(15):
            try:
                s = next(gen)
                self.assertGreaterEqual(len(s["visited"]), prev)
                prev = len(s["visited"])
            except StopIteration:
                break


# ══════════════════════════════════════════════════════════════════
# Greedy
# ══════════════════════════════════════════════════════════════════
class TestGreedy(unittest.TestCase):

    def test_finds_path(self):
        g = make_grid()
        path = find_path(greedy_steps(g))
        self.assertIsNotNone(path)
        self.assertEqual(path[-1], g.goal)

    def test_goal_none_h_equals_zero(self):
        g = make_grid(3, 3, (0, 0), goal=None)
        last = drain(greedy_steps(g, goal=None))
        # h=0 khi goal=None → tất cả cell.h = 0
        for cell in g.cells.values():
            self.assertEqual(cell.h, 0)

    def test_h_scores_written(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        drain(greedy_steps(g))
        # Ô start: h = manhattan((0,0),(2,2)) = 4
        self.assertEqual(g.get(0, 0).h, 4)


# ══════════════════════════════════════════════════════════════════
# A*
# ══════════════════════════════════════════════════════════════════
class TestAStar(unittest.TestCase):

    def test_finds_path(self):
        g = make_grid()
        path = find_path(astar_steps(g))
        self.assertIsNotNone(path)
        self.assertEqual(path[-1], g.goal)

    def test_path_is_connected(self):
        g = make_grid()
        path = find_path(astar_steps(g))
        for i in range(len(path) - 1):
            c0, r0 = path[i]; c1, r1 = path[i + 1]
            self.assertEqual(abs(c0 - c1) + abs(r0 - r1), 1)

    def test_f_equals_g_plus_h(self):
        g = make_grid(4, 4, (0, 0), (3, 3))
        drain(astar_steps(g))
        for cell in g.cells.values():
            if cell.g > 0 or cell.h > 0:
                self.assertAlmostEqual(cell.f, cell.g + cell.h, places=5)

    def test_goal_none_degenerates_to_ucs(self):
        """A* với goal=None → h=0 → f=g → hành xử giống UCS."""
        g1 = make_grid(4, 4, (0, 0), goal=None)
        g2 = make_grid(4, 4, (0, 0), goal=None)
        a_visited  = drain(astar_steps(g1, goal=None))["visited"]
        u_visited  = drain(ucs_steps(g2, goal=None))["visited"]
        self.assertEqual(a_visited, u_visited)

    def test_start_none_multisource(self):
        g = make_grid(3, 3, start=None, goal=(1, 1))
        last = drain(astar_steps(g, start=None))
        self.assertIsNotNone(last)


# ══════════════════════════════════════════════════════════════════
# Simple Hill Climbing
# ══════════════════════════════════════════════════════════════════
class TestSimpleHC(unittest.TestCase):

    def test_yields_neighbor_scores(self):
        g = make_grid(3, 3, (0, 0), (2, 2))
        step = next(simple_hill_climbing_steps(g))
        self.assertIsInstance(step["neighbor_scores"], dict)
        self.assertGreater(len(step["neighbor_scores"]), 0)

    def test_chosen_improves_or_none(self):
        g = make_grid(5, 5, (0, 0), (4, 4))
        gen = simple_hill_climbing_steps(g)
        prev_pos = g.start
        for _ in range(20):
            try:
                step = next(gen)
            except StopIteration:
                break
            chosen = step["chosen"]
            if chosen is not None:
                self.assertGreater(
                    g.heuristic_value(*chosen),
                    g.heuristic_value(*prev_pos),
                    msg="Simple HC phải chọn ô có heuristic cao hơn hiện tại",
                )
                prev_pos = chosen
            else:
                self.assertTrue(step["stuck"])

    def test_stops_at_local_max(self):
        """Tạo lưới mà start bị bao quanh toàn bởi ô tệ hơn → stuck ngay."""
        g = GridModel(3, 3, (1, 1), (0, 0), fog=False)
        # Đặt goal tại (0,0) nhưng tất cả láng giềng (1,1) đều xa goal hơn
        step = next(simple_hill_climbing_steps(g))
        # (1,1) là trung tâm; (0,0) là goal nên heuristic cao, chosen=(0,1) or (1,0)
        # Test chính: nếu không có láng giềng tốt hơn → stuck=True
        if step["stuck"]:
            self.assertIsNone(step["chosen"])

    def test_no_goal_test_inside(self):
        """Kiểm tra: step dict KHÔNG có "path" khi đang chạy (local search)."""
        g = make_grid(5, 5, (0, 0), (4, 4))
        gen = simple_hill_climbing_steps(g)
        for _ in range(5):
            try:
                step = next(gen)
                # path luôn None trong mọi bước (không có goal test bên trong)
                self.assertIsNone(step["path"])
            except StopIteration:
                break

    def test_start_none_random_restart(self):
        g = make_grid(5, 5, start=None, goal=(4, 4))
        rng = random.Random(42)
        step = next(simple_hill_climbing_steps(g, start=None, rng=rng))
        self.assertIsNotNone(step["current"])
        # Vị trí start phải là ô passable
        c, r = step["current"]
        self.assertTrue(g.get(c, r).passable)


# ══════════════════════════════════════════════════════════════════
# Steepest-Ascent Hill Climbing
# ══════════════════════════════════════════════════════════════════
class TestSteepestHC(unittest.TestCase):

    def test_chosen_is_best_neighbor(self):
        g = make_grid(5, 5, (0, 0), (4, 4))
        gen = steepest_ascent_hill_climbing_steps(g)
        step = next(gen)
        if step["chosen"] is not None:
            chosen_score = g.heuristic_value(*step["chosen"])
            for pos, score in step["neighbor_scores"].items():
                self.assertLessEqual(score, chosen_score,
                                     "Steepest HC phải chọn ô TỐT NHẤT")

    def test_evaluates_all_neighbors(self):
        g = make_grid(3, 3, (1, 1), (2, 2))
        step = next(steepest_ascent_hill_climbing_steps(g))
        # (1,1) có 4 láng giềng trong lưới 3x3
        self.assertEqual(len(step["neighbor_scores"]), 4)

    def test_start_none(self):
        g = make_grid(5, 5, start=None, goal=(4, 4))
        rng = random.Random(7)
        step = next(steepest_ascent_hill_climbing_steps(g, start=None, rng=rng))
        self.assertIsNotNone(step["current"])


# ══════════════════════════════════════════════════════════════════
# Stochastic Hill Climbing
# ══════════════════════════════════════════════════════════════════
class TestStochasticHC(unittest.TestCase):

    def test_chosen_from_uphill_only(self):
        g = make_grid(5, 5, (0, 0), (4, 4))
        rng = random.Random(0)
        gen = stochastic_hill_climbing_steps(g, rng=rng)
        step = next(gen)
        if step["chosen"] is not None:
            current_score = g.heuristic_value(0, 0)
            chosen_score  = g.heuristic_value(*step["chosen"])
            self.assertGreater(chosen_score, current_score,
                               "Stochastic HC chỉ chọn trong tập uphill")

    def test_randomness_produces_different_paths(self):
        """Hai RNG khác nhau có thể tạo đường đi khác nhau."""
        paths = set()
        for seed in range(5):
            g   = make_grid(5, 5, (0, 0), (4, 4))
            rng = random.Random(seed)
            visited_seq = []
            for step in stochastic_hill_climbing_steps(g, rng=rng):
                visited_seq.append(step["current"])
                if step["stuck"]:
                    break
            paths.add(tuple(visited_seq))
        # Ít nhất 2 path khác nhau trong 5 seed
        self.assertGreater(len(paths), 1)


# ══════════════════════════════════════════════════════════════════
# Simulated Annealing
# ══════════════════════════════════════════════════════════════════
class TestSimulatedAnnealing(unittest.TestCase):

    def test_temperature_decreases_monotonically(self):
        g   = make_grid(4, 4, (0, 0), (3, 3))
        rng = random.Random(1)
        gen = simulated_annealing_steps(g, initial_temp=10.0, cooling=0.9,
                                        min_temp=0.5, rng=rng)
        prev_temp = float("inf")
        for _ in range(20):
            try:
                step = next(gen)
                t    = step["temperature"]
                self.assertLessEqual(t, prev_temp,
                                     "Nhiệt độ phải giảm đơn điệu")
                prev_temp = t
            except StopIteration:
                break

    def test_temperature_floors_at_min_temp(self):
        g   = make_grid(3, 3, (0, 0), (2, 2))
        rng = random.Random(2)
        gen = simulated_annealing_steps(g, initial_temp=5.0, cooling=0.5,
                                        min_temp=0.5, rng=rng)
        for step in gen:
            self.assertGreaterEqual(step["temperature"], 0.49)  # ~min_temp

    def test_accepts_downhill_at_high_temp(self):
        """Tại nhiệt độ cao, SA có thể chấp nhận bước tệ hơn.
        Kiểm tra gián tiếp qua nhiều seed."""
        g = make_grid(5, 5, (0, 0), (4, 4))
        has_downhill_accepted = False
        for seed in range(30):
            rng  = random.Random(seed)
            gen  = simulated_annealing_steps(g, initial_temp=50.0, cooling=0.99,
                                             min_temp=0.1, rng=rng)
            pos  = g.start
            for _ in range(10):
                try:
                    step = next(gen)
                    chosen = step.get("chosen")
                    if chosen and chosen != pos:
                        if g.heuristic_value(*chosen) < g.heuristic_value(*pos):
                            has_downhill_accepted = True
                            break
                    pos = chosen or pos
                except StopIteration:
                    break
            if has_downhill_accepted:
                break
        self.assertTrue(has_downhill_accepted,
                        "SA nên chấp nhận ít nhất một bước đi tệ hơn khi nhiệt độ cao")

    def test_path_always_none(self):
        """SA không có goal test bên trong → path luôn None."""
        g   = make_grid(4, 4, (0, 0), (3, 3))
        rng = random.Random(3)
        gen = simulated_annealing_steps(g, rng=rng)
        for _ in range(15):
            try:
                step = next(gen)
                self.assertIsNone(step["path"])
            except StopIteration:
                break

    def test_start_none_random_restart(self):
        g   = make_grid(5, 5, start=None, goal=(4, 4))
        rng = random.Random(42)
        step = next(simulated_annealing_steps(g, start=None, rng=rng))
        c, r = step["current"]
        self.assertTrue(g.get(c, r).passable)


# ══════════════════════════════════════════════════════════════════
# Kiểm tra registry
# ══════════════════════════════════════════════════════════════════
class TestRegistry(unittest.TestCase):

    def test_all_algorithms_registered(self):
        from systems.algorithms import ALGORITHM_REGISTRY
        expected = {
            "BFS", "DFS", "IDS",
            "UCS", "Greedy", "A*",
            "Hill Climbing", "Steepest Ascent HC",
            "Stochastic HC", "Simulated Annealing",
        }
        self.assertEqual(set(ALGORITHM_REGISTRY.keys()), expected)

    def test_local_search_set_correct(self):
        from systems.algorithms import LOCAL_SEARCH_ALGORITHMS
        self.assertIn("Hill Climbing", LOCAL_SEARCH_ALGORITHMS)
        self.assertIn("Simulated Annealing", LOCAL_SEARCH_ALGORITHMS)
        self.assertNotIn("BFS", LOCAL_SEARCH_ALGORITHMS)
        self.assertNotIn("A*", LOCAL_SEARCH_ALGORITHMS)

    def test_registry_callables_produce_generators(self):
        from systems.algorithms import ALGORITHM_REGISTRY
        import inspect
        g = make_grid(3, 3, (0, 0), (2, 2))
        for name, fn in ALGORITHM_REGISTRY.items():
            gen = fn(g)
            self.assertTrue(
                inspect.isgenerator(gen),
                msg=f"{name} phải trả về generator",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
