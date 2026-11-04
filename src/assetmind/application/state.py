"""Explicit run state machine.

CREATED → VALIDATING → PLANNING → FETCHING → ANALYZING → VERIFYING → COMPLETED

FAILED, CANCELLED, and PARTIAL are terminal.
"""

from enum import StrEnum


class RunState(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    PLANNING = "planning"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.CREATED: {RunState.VALIDATING, RunState.FAILED, RunState.CANCELLED},
    RunState.VALIDATING: {RunState.PLANNING, RunState.FAILED, RunState.CANCELLED},
    RunState.PLANNING: {RunState.FETCHING, RunState.FAILED, RunState.CANCELLED},
    RunState.FETCHING: {RunState.ANALYZING, RunState.FAILED, RunState.CANCELLED},
    RunState.ANALYZING: {RunState.VERIFYING, RunState.FAILED, RunState.CANCELLED},
    RunState.VERIFYING: {
        RunState.COMPLETED,
        RunState.PARTIAL,
        RunState.FAILED,
        RunState.CANCELLED,
    },
    RunState.COMPLETED: set(),
    RunState.FAILED: set(),
    RunState.CANCELLED: set(),
    RunState.PARTIAL: set(),
}


class InvalidTransition(Exception):
    def __init__(self, current: RunState, target: RunState) -> None:
        super().__init__(f"Cannot move from {current} to {target}.")
        self.current = current
        self.target = target


class StateMachine:
    def __init__(self, state: RunState = RunState.CREATED) -> None:
        self.state = state

    def move(self, target: RunState) -> RunState:
        if target not in _TRANSITIONS[self.state]:
            raise InvalidTransition(self.state, target)
        self.state = target
        return self.state

    def finish(self, target: RunState) -> None:
        """Move forward to a terminal state when the run stops early."""

        if self.terminal:
            return
        if target in _TRANSITIONS[self.state]:
            self.move(target)
            return
        for state in (
            RunState.VALIDATING,
            RunState.PLANNING,
            RunState.FETCHING,
            RunState.ANALYZING,
            RunState.VERIFYING,
        ):
            if self.terminal:
                return
            if state in _TRANSITIONS[self.state]:
                self.move(state)
            if target in _TRANSITIONS[self.state]:
                self.move(target)
                return
        raise InvalidTransition(self.state, target)

    @property
    def terminal(self) -> bool:
        return self.state in {
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
            RunState.PARTIAL,
        }
