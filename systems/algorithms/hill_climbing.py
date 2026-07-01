"""
systems/algorithms/hill_climbing.py
=====================================
Step generators for the local-search algorithms used by Level 3.

All three Hill Climbing variants reuse GridModel.heuristic_value(), i.e.
the same h(n) definition used by informed search.  A smaller h(n) is better.

Extra fields emitted for the visual solver:
    candidate            the neighbor currently being inspected
    phase                inspect | evaluate_all | select_best | random_select
    decision             reject | accept | candidate | best | random | stuck | loop
    improving_neighbors  neighbors whose h(n) is lower than current h(n)
    loop                  True when a selected node was already visited
"""
import math
import random

from entities.grid_cell import ORTHOGONAL_DIRECTIONS

_UNSET = object()


def _resolve_start(grid, start, rng=None):
    """Resolve a concrete starting position.

    start=None means random restart on a passable cell.
    """
    if start is None:
        passable = [(c, r) for (c, r), cell in grid.cells.items() if cell.passable]
        if not passable:
            raise ValueError("Ma trận không có ô nào có thể di chuyển")
        rng = rng or random.Random()
        return rng.choice(passable)
    return start


def _candidate_scores(grid, current, current_health, use_health):
    """Return passable, affordable orthogonal neighbors in L-R-U-D order."""
    result = []
    for dc, dr in ORTHOGONAL_DIRECTIONS:
        nc, nr = current[0] + dc, current[1] + dr
        if not grid.in_bounds(nc, nr):
            continue
        cell = grid.get(nc, nr)
        if cell is None or not cell.passable:
            continue
        pos = (nc, nr)
        if use_health and not grid.can_afford(current_health, *pos):
            continue
        result.append((pos, grid.heuristic_value(*pos)))
    return result


def _base_step(current, scores, chosen=None, *, candidate=None, phase="inspect",
               decision=None, stuck=False, loop=False, improving=None,
               temperature=None):
    return {
        "current": current,
        "neighbor_scores": dict(scores),
        "chosen": chosen,
        "candidate": candidate,
        "phase": phase,
        "decision": decision,
        "improving_neighbors": list(improving or []),
        "stuck": stuck,
        "loop": loop,
        "path": None,
        "temperature": temperature,
    }


# ══════════════════════════════════════════════════════════════════
# SIMPLE HILL CLIMBING
# Inspect neighbors one by one and accept the first better neighbor.
# ══════════════════════════════════════════════════════════════════
def simple_hill_climbing_steps(grid, start=_UNSET, rng=None, health=None):
    start = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)
    current_health = health if health is not None else 100
    visited = {current}

    while True:
        current_score = grid.heuristic_value(*current)
        candidates = _candidate_scores(grid, current, current_health, health is not None)
        chosen = None

        for pos, score in candidates:
            better = score < current_score
            is_loop = better and pos in visited
            decision = "loop" if is_loop else ("accept" if better else "reject")
            yield _base_step(
                current,
                {pos: score},
                chosen=pos if better and not is_loop else None,
                candidate=pos,
                phase="inspect",
                decision=decision,
                loop=is_loop,
                improving=[pos] if better else [],
            )

            if is_loop:
                return
            if better:
                chosen = pos
                break

        if chosen is None:
            yield _base_step(
                current,
                {},
                phase="inspect",
                decision="stuck",
                stuck=True,
            )
            return

        if health is not None:
            current_health += grid.health_delta(*chosen)
        current = chosen
        visited.add(current)


# ══════════════════════════════════════════════════════════════════
# STEEPEST-ASCENT HILL CLIMBING
# Light all neighbors, then select the one with the smallest h(n).
# ══════════════════════════════════════════════════════════════════
def steepest_ascent_hill_climbing_steps(grid, start=_UNSET, rng=None, health=None):
    start = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)
    current_health = health if health is not None else 100
    visited = {current}

    while True:
        current_score = grid.heuristic_value(*current)
        candidates = _candidate_scores(grid, current, current_health, health is not None)
        scores = dict(candidates)
        improving = [pos for pos, score in candidates if score < current_score]

        # First visual step: every neighbor is visible and listed.
        yield _base_step(
            current,
            scores,
            phase="evaluate_all",
            decision="candidate",
            improving=improving,
        )

        if not improving:
            yield _base_step(
                current,
                scores,
                phase="select_best",
                decision="stuck",
                stuck=True,
            )
            return

        best_pos = min(improving, key=lambda pos: (scores[pos], pos[1], pos[0]))
        is_loop = best_pos in visited
        yield _base_step(
            current,
            scores,
            chosen=None if is_loop else best_pos,
            candidate=best_pos,
            phase="select_best",
            decision="loop" if is_loop else "best",
            loop=is_loop,
            improving=improving,
        )

        if is_loop:
            return
        if health is not None:
            current_health += grid.health_delta(*best_pos)
        current = best_pos
        visited.add(current)


# ══════════════════════════════════════════════════════════════════
# STOCHASTIC HILL CLIMBING
# Randomly select one node from the set of better neighbors.
# ══════════════════════════════════════════════════════════════════
def stochastic_hill_climbing_steps(grid, start=_UNSET, rng=None, health=None):
    rng = rng or random.Random()
    start = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)
    current_health = health if health is not None else 100
    visited = {current}

    while True:
        current_score = grid.heuristic_value(*current)
        candidates = _candidate_scores(grid, current, current_health, health is not None)
        scores = dict(candidates)
        improving = [pos for pos, score in candidates if score < current_score]

        if not improving:
            yield _base_step(
                current,
                scores,
                phase="random_select",
                decision="stuck",
                stuck=True,
            )
            return

        # Uniform random choice in the improving-neighbor set, as requested.
        chosen = rng.choice(improving)
        is_loop = chosen in visited
        yield _base_step(
            current,
            scores,
            chosen=None if is_loop else chosen,
            candidate=chosen,
            phase="random_select",
            decision="loop" if is_loop else "random",
            loop=is_loop,
            improving=improving,
        )

        if is_loop:
            return
        if health is not None:
            current_health += grid.health_delta(*chosen)
        current = chosen
        visited.add(current)


# ══════════════════════════════════════════════════════════════════
# SIMULATED ANNEALING (kept for other scenes/experiments)
# ══════════════════════════════════════════════════════════════════
def simulated_annealing_steps(
    grid,
    start=_UNSET,
    initial_temp=30.0,
    cooling=0.95,
    min_temp=0.5,
    rng=None,
    health=None,
):
    rng = rng or random.Random()
    start = grid.start if start is _UNSET else start
    current = _resolve_start(grid, start, rng)
    current_health = health if health is not None else 100
    temperature = float(initial_temp)

    while True:
        current_score = grid.heuristic_value(*current)
        candidates = _candidate_scores(grid, current, current_health, health is not None)
        scores = dict(candidates)
        chosen = None

        if candidates:
            pos, score = rng.choice(candidates)
            delta = score - current_score  # lower is better
            if delta < 0:
                chosen = pos
            elif temperature > min_temp:
                accept_prob = math.exp(-delta / max(temperature, 1e-9))
                if rng.random() < accept_prob:
                    chosen = pos

        temperature = max(temperature * cooling, min_temp)
        stuck = chosen is None and temperature <= min_temp
        yield _base_step(
            current,
            scores,
            chosen=chosen,
            candidate=chosen,
            phase="annealing",
            decision="accept" if chosen is not None else ("stuck" if stuck else "reject"),
            stuck=stuck,
            temperature=temperature,
        )

        if stuck:
            return
        if chosen is not None:
            if health is not None:
                current_health += grid.health_delta(*chosen)
            current = chosen


ALGORITHMS_HILLCLIMB = {
    "Hill Climbing": simple_hill_climbing_steps,
    "Steepest Ascent HC": steepest_ascent_hill_climbing_steps,
    "Stochastic HC": stochastic_hill_climbing_steps,
    "Simulated Annealing": simulated_annealing_steps,
}
