"""AND-OR graph search used by the uncertainty demo scene.

The agent chooses one OR action.  The environment can return any state in
``outcomes(state, action)``; therefore every outcome under that action is an
AND branch and all of them must have a plan to the goal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Mapping, Sequence

State = Hashable
Action = Hashable


@dataclass(frozen=True)
class ConditionalPlan:
    """A policy node: perform ``action`` and follow the matching child plan."""

    action: Action | None
    branches: Mapping[State, "ConditionalPlan"]

    @property
    def is_goal(self) -> bool:
        return self.action is None


@dataclass
class AndOrResult:
    success: bool
    plan: ConditionalPlan | None
    events: list[dict]
    expanded: int


def and_or_graph_search(
    start: State,
    is_goal: Callable[[State], bool],
    actions: Callable[[State], Iterable[Action]],
    outcomes: Callable[[State, Action], Sequence[State]],
    action_name: Callable[[Action], str] | None = None,
    max_depth: int = 18,
    max_events: int = 800,
    trace_depth: int = 1,
) -> AndOrResult:
    """Find a finite conditional plan and return animation-friendly events.

    Cycles on the current recursion path are treated as a failed branch.  This
    matches the teaching demo: an action is accepted only when every possible
    immediate result can be proven to reach the goal without looping.
    """

    name_of = action_name or (lambda action: str(action))
    events: list[dict] = []
    expanded = 0
    success_cache: dict[State, ConditionalPlan] = {}
    failure_cache: set[tuple[State, int]] = set()

    def emit(event_type: str, **payload) -> None:
        depth = int(payload.get("depth", 0))
        if depth > trace_depth or len(events) >= max_events:
            return
        events.append({"type": event_type, **payload})

    def solve_or(state: State, path: frozenset[State], depth: int) -> ConditionalPlan | None:
        nonlocal expanded
        emit("OR_ENTER", state=state, depth=depth)

        if is_goal(state):
            emit("GOAL", state=state, depth=depth, result="GOAL")
            return ConditionalPlan(None, {})

        if depth >= max_depth:
            emit("OR_FAIL", state=state, depth=depth, reason="DEPTH LIMIT")
            return None

        if state in path:
            emit("OR_FAIL", state=state, depth=depth, reason="LOOP")
            return None

        cached = success_cache.get(state)
        if cached is not None:
            emit("CACHE_SUCCESS", state=state, depth=depth)
            return cached

        cache_key = (state, max_depth - depth)
        if cache_key in failure_cache:
            emit("CACHE_FAIL", state=state, depth=depth)
            return None

        expanded += 1
        next_path = path | {state}

        for action_index, action in enumerate(actions(state)):
            branch_states = tuple(dict.fromkeys(outcomes(state, action)))
            if not branch_states:
                continue

            emit(
                "OR_TRY",
                state=state,
                action=action,
                action_name=name_of(action),
                action_index=action_index,
                depth=depth,
            )
            emit(
                "AND_EXPAND",
                state=state,
                action=action,
                action_name=name_of(action),
                outcomes=branch_states,
                depth=depth,
            )

            child_plans: dict[State, ConditionalPlan] = {}
            all_success = True
            for branch_index, child_state in enumerate(branch_states):
                emit(
                    "BRANCH_START",
                    state=state,
                    action=action,
                    action_name=name_of(action),
                    outcome=child_state,
                    branch_index=branch_index,
                    outcomes=branch_states,
                    depth=depth,
                )
                child_plan = solve_or(child_state, next_path, depth + 1)
                if child_plan is None:
                    emit(
                        "BRANCH_FAIL",
                        state=state,
                        action=action,
                        action_name=name_of(action),
                        outcome=child_state,
                        branch_index=branch_index,
                        outcomes=branch_states,
                        depth=depth,
                    )
                    all_success = False
                    break

                child_plans[child_state] = child_plan
                emit(
                    "BRANCH_SUCCESS",
                    state=state,
                    action=action,
                    action_name=name_of(action),
                    outcome=child_state,
                    branch_index=branch_index,
                    outcomes=branch_states,
                    depth=depth,
                )

            if all_success and len(child_plans) == len(branch_states):
                plan = ConditionalPlan(action, child_plans)
                success_cache[state] = plan
                emit(
                    "ACTION_ACCEPT",
                    state=state,
                    action=action,
                    action_name=name_of(action),
                    outcomes=branch_states,
                    depth=depth,
                    result="NHẬN",
                )
                return plan

            emit(
                "ACTION_REJECT",
                state=state,
                action=action,
                action_name=name_of(action),
                outcomes=branch_states,
                depth=depth,
                result="LOẠI",
            )

        failure_cache.add(cache_key)
        emit("OR_FAIL", state=state, depth=depth, reason="KHÔNG CÓ HÀNH ĐỘNG AN TOÀN")
        return None

    plan = solve_or(start, frozenset(), 0)
    return AndOrResult(plan is not None, plan, events, expanded)
