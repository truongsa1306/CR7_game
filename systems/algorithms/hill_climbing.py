"""
systems/algorithms/hill_climbing.py
=====================================
Thuật toán tìm kiếm cục bộ (Local Search) cho Level 2–3.

Theo mã giả AIMA, các thuật toán leo đồi / tìm kiếm cục bộ KHÔNG có
goal test bên trong thuật toán. Chúng chỉ tối ưu hóa một hàm mục tiêu
(objective function) và dừng khi bị kẹt hoặc theo lịch làm nguội.
Việc kiểm tra "đã đến đích chưa" thuộc về gameplay_scene (qua _move_player).

Shape của step dict (khác với graph search):
    {
        "current"         : (col, row),
        "neighbor_scores" : {(col,row): score, ...},   # heuristic_value của các láng giềng
        "chosen"          : (col,row) or None,          # ô được chọn bước tiếp theo
        "stuck"           : bool,                       # True = đỉnh cục bộ (game over)
        "path"            : None,                       # luôn None (local search không trả path)
        "temperature"     : float or None,              # chỉ cho Simulated Annealing
    }

Tham số start
--------------
_UNSET sentinel:
  * start=cụ thể → bắt đầu từ vị trí đó.
  * start=None   → random restart: chọn ngẫu nhiên một ô passable làm điểm xuất phát.
                   Phù hợp với "không có trạng thái bắt đầu" trong local search.

Mã giả AIMA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HILL-CLIMBING(problem):
    current ← Node(problem.INITIAL)
    loop:
        neighbors ← expand(current)
        best      ← highest-valued node in neighbors
        if VALUE(best) ≤ VALUE(current):
            return current          ← đỉnh cục bộ, trả về hiện tại
        current ← best

SIMULATED-ANNEALING(problem, schedule):
    current ← Node(problem.INITIAL)
    t ← 1
    loop:
        T ← schedule(t)
        if T = 0: return current
        next ← random node in expand(current)
        ΔE   ← VALUE(next) - VALUE(current)
        if ΔE > 0: current ← next
        else:      current ← next with prob e^(ΔE/T)
        t ← t + 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import math
import random

from entities.grid_cell import ORTHOGONAL_DIRECTIONS

_UNSET = object()


def _resolve_start(grid, start, rng=None):
    """Trả về vị trí bắt đầu.
    start=None → random restart (chọn ngẫu nhiên ô passable).
    """
    if start is None:
        passable = [(c, r) for (c, r), cell in grid.cells.items() if cell.passable]
        rng = rng or random.Random()
        return rng.choice(passable)
    return start


# ══════════════════════════════════════════════════════════════════
# SIMPLE HILL CLIMBING
# Xét lần lượt láng giềng, chọn ngay ô ĐẦU TIÊN có chi phí nhỏ hơn hiện tại.
# ══════════════════════════════════════════════════════════════════
def simple_hill_climbing_steps(grid, start=_UNSET, rng=None):
    """Simple Hill Climbing – "first-choice".
    Dừng (stuck=True) khi không có ô láng giềng nào có chi phí thấp hơn hiện tại.
    Không có goal test bên trong (đúng với mã giả local search).
    """
    start = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)

    while True:
        current_score = grid.heuristic_value(*current)
        scores        = {}
        chosen        = None

        for dc, dr in ORTHOGONAL_DIRECTIONS:
            nc, nr = current[0] + dc, current[1] + dr
            if not grid.in_bounds(nc, nr):
                continue
            cell = grid.get(nc, nr)
            if cell is None or not cell.passable:
                continue
            pos   = (nc, nr)
            score = grid.heuristic_value(*pos)
            scores[pos] = score
            yield {
                "current":          current,
                "neighbor_scores":  {pos: score},
                "chosen":           None,
                "stuck":            False,
                "path":             None,
                "temperature":      None,
            }
            if chosen is None and score < current_score:
                chosen = pos
                break

        stuck = chosen is None
        yield {
            "current":          current,
            "neighbor_scores":  scores,
            "chosen":           chosen,
            "stuck":            stuck,
            "path":             None,
            "temperature":      None,
        }

        if stuck:
            return          # đỉnh cục bộ – scene xử lý game over

        current = chosen


# ══════════════════════════════════════════════════════════════════
# STEEPEST-ASCENT HILL CLIMBING
# Xét TẤT CẢ láng giềng, chọn ô có chi phí nhỏ nhất.
# ══════════════════════════════════════════════════════════════════
def steepest_ascent_hill_climbing_steps(grid, start=_UNSET, rng=None):
    """Steepest-Ascent Hill Climbing – "best-improvement".
    So sánh tất cả láng giềng, chọn ô có chi phí thấp nhất.
    Nếu không có láng giềng nào thấp hơn hiện tại → stuck.
    """
    start = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)

    while True:
        current_score          = grid.heuristic_value(*current)
        scores                 = {}
        best_pos, best_score   = None, current_score  # ngưỡng tối đa = current

        for dc, dr in ORTHOGONAL_DIRECTIONS:
            nc, nr = current[0] + dc, current[1] + dr
            if not grid.in_bounds(nc, nr):
                continue
            cell = grid.get(nc, nr)
            if cell is None or not cell.passable:
                continue
            pos   = (nc, nr)
            score = grid.heuristic_value(*pos)
            scores[pos] = score
            if score < best_score:
                best_score, best_pos = score, pos
            yield {
                "current":          current,
                "neighbor_scores":  {pos: score},
                "chosen":           None,
                "stuck":            False,
                "path":             None,
                "temperature":      None,
            }

        stuck = best_pos is None
        yield {
            "current":          current,
            "neighbor_scores":  scores,
            "chosen":           best_pos,
            "stuck":            stuck,
            "path":             None,
            "temperature":      None,
        }

        if stuck:
            return

        current = best_pos


# ══════════════════════════════════════════════════════════════════
# STOCHASTIC HILL CLIMBING
# Lọc các láng giềng tốt hơn, chọn NGẪU NHIÊN có trọng số.
# ══════════════════════════════════════════════════════════════════
def stochastic_hill_climbing_steps(grid, start=_UNSET, rng=None):
    """Stochastic Hill Climbing.
    Trong tập các láng giềng có chi phí thấp hơn hiện tại, chọn ngẫu nhiên có
    trọng số tỷ lệ với mức độ cải thiện. Có thể thoát local minima tốt hơn
    Simple/Steepest HC.
    """
    rng     = rng or random.Random()
    start   = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)

    while True:
        current_score = grid.heuristic_value(*current)
        scores        = {}
        downhill      = []   # (pos, improvement)

        for dc, dr in ORTHOGONAL_DIRECTIONS:
            nc, nr = current[0] + dc, current[1] + dr
            if not grid.in_bounds(nc, nr):
                continue
            cell = grid.get(nc, nr)
            if cell is None or not cell.passable:
                continue
            pos   = (nc, nr)
            score = grid.heuristic_value(*pos)
            scores[pos] = score
            if score < current_score:
                downhill.append((pos, current_score - score))
            yield {
                "current":          current,
                "neighbor_scores":  {pos: score},
                "chosen":           None,
                "stuck":            False,
                "path":             None,
                "temperature":      None,
            }

        chosen = None
        if downhill:
            weights = [w for _, w in downhill]
            chosen = rng.choices([p for p, _ in downhill], weights=weights, k=1)[0]

        stuck = chosen is None
        yield {
            "current":          current,
            "neighbor_scores":  scores,
            "chosen":           chosen,
            "stuck":            stuck,
            "path":             None,
            "temperature":      None,
        }

        if stuck:
            return

        current = chosen


# ══════════════════════════════════════════════════════════════════
# SIMULATED ANNEALING
# Mã giả AIMA: chấp nhận bước đi tệ hơn với xác suất e^(ΔE/T).
# T giảm dần theo lịch làm nguội (cooling schedule).
# ══════════════════════════════════════════════════════════════════
def simulated_annealing_steps(
    grid,
    start=_UNSET,
    initial_temp=30.0,
    cooling=0.95,
    min_temp=0.5,
    rng=None,
):
    """Simulated Annealing – "Precision Sprints" (Level 3).

    Mỗi bước:
    1. Chọn ngẫu nhiên MỘT láng giềng.
    2. Nếu tốt hơn → luôn chấp nhận.
    3. Nếu tệ hơn   → chấp nhận với xác suất e^(ΔE / T).
    4. Giảm nhiệt độ T theo hệ số cooling.
    5. Khi T ≤ min_temp và không chấp nhận được bước nào → stuck.

    Không có goal test bên trong (local search thuần túy).
    start=None → random restart theo ô passable bất kỳ.
    """
    rng         = rng or random.Random()
    start       = grid.start if start is _UNSET else start
    current     = _resolve_start(grid, start, rng)
    temperature = float(initial_temp)

    while True:
        current_score = grid.heuristic_value(*current)
        candidates    = list(grid.neighbors(*current))
        scores        = {(c.col, c.row): grid.heuristic_value(c.col, c.row)
                         for c in candidates}

        chosen = None
        if candidates:
            pick  = rng.choice(candidates)
            pos   = (pick.col, pick.row)
            delta = scores[pos] - current_score

            if delta > 0:
                # Luôn chấp nhận bước cải thiện
                chosen = pos
            elif temperature > min_temp:
                # Chấp nhận bước tệ hơn với xác suất e^(ΔE/T)
                accept_prob = math.exp(delta / temperature)
                if rng.random() < accept_prob:
                    chosen = pos

        # Giảm nhiệt độ mỗi bước (đúng với mã giả AIMA: T ← schedule(t))
        temperature = max(temperature * cooling, min_temp)

        # Thực sự stuck chỉ khi nhiệt độ chạm đáy VÀ không chấp nhận được
        stuck = (chosen is None) and (temperature <= min_temp)

        yield {
            "current":          current,
            "neighbor_scores":  scores,
            "chosen":           chosen,
            "stuck":            stuck,
            "path":             None,
            "temperature":      temperature,
        }

        if stuck:
            return          # scene xử lý game over

        if chosen is not None:
            current = chosen
        # Nếu chosen=None nhưng chưa stuck (T chưa đến đáy) → thử lại vòng tiếp


# ─── Registry ────────────────────────────────────────────────────
ALGORITHMS_HILLCLIMB = {
    "Hill Climbing":       simple_hill_climbing_steps,
    "Steepest Ascent HC":  steepest_ascent_hill_climbing_steps,
    "Stochastic HC":       stochastic_hill_climbing_steps,
    "Simulated Annealing": simulated_annealing_steps,
}
