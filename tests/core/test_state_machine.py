"""Tests for arktower.core.state_machine — transition logic."""

from __future__ import annotations

import pytest

from arktower.core.models import TaskStatus, Trigger
from arktower.core.state_machine import (
    TERMINAL_STATES,
    TRANSITION_TABLE,
    GateCheckError,
    InvalidTransition,
    StateMachine,
    TransitionError,
)


@pytest.fixture
def sm() -> StateMachine:
    return StateMachine()


# ── TRANSITION_TABLE structure ─────────────────────────────────────────────


class TestTransitionTable:
    def test_all_15_triggers_present(self) -> None:
        assert set(TRANSITION_TABLE.keys()) == set(Trigger)

    def test_submit_from_none(self) -> None:
        assert TRANSITION_TABLE[Trigger.SUBMIT][None] == TaskStatus.SUBMITTED

    def test_cancel_from_multiple_statuses(self) -> None:
        cancel_sources = set(TRANSITION_TABLE[Trigger.CANCEL].keys())
        expected = {
            TaskStatus.SUBMITTED, TaskStatus.QUEUED, TaskStatus.IN_PROGRESS,
            TaskStatus.REVIEW, TaskStatus.INPUT_REQUIRED, TaskStatus.BLOCKED,
        }
        assert cancel_sources == expected

    def test_timeout_from_three_statuses(self) -> None:
        timeout_sources = set(TRANSITION_TABLE[Trigger.TIMEOUT].keys())
        assert timeout_sources == {
            TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.INPUT_REQUIRED,
        }

    def test_reopen_from_all_terminal_states(self) -> None:
        reopen_sources = set(TRANSITION_TABLE[Trigger.REOPEN].keys())
        assert reopen_sources == TERMINAL_STATES


# ── TERMINAL_STATES ────────────────────────────────────────────────────────


class TestTerminalStates:
    def test_contains_four_states(self) -> None:
        assert len(TERMINAL_STATES) == 4

    def test_expected_members(self) -> None:
        assert TERMINAL_STATES == {
            TaskStatus.COMPLETED, TaskStatus.FAILED,
            TaskStatus.CANCELED, TaskStatus.TIMED_OUT,
        }


# ── validate_transition ───────────────────────────────────────────────────


class TestValidateTransition:
    def test_happy_path_enqueue(self, sm: StateMachine) -> None:
        target = sm.validate_transition(TaskStatus.SUBMITTED, Trigger.ENQUEUE)
        assert target == TaskStatus.QUEUED

    def test_happy_path_claim(self, sm: StateMachine) -> None:
        target = sm.validate_transition(TaskStatus.QUEUED, Trigger.CLAIM)
        assert target == TaskStatus.IN_PROGRESS

    def test_happy_path_complete(self, sm: StateMachine) -> None:
        target = sm.validate_transition(TaskStatus.IN_PROGRESS, Trigger.COMPLETE)
        assert target == TaskStatus.COMPLETED

    def test_happy_path_fail(self, sm: StateMachine) -> None:
        target = sm.validate_transition(TaskStatus.IN_PROGRESS, Trigger.FAIL)
        assert target == TaskStatus.FAILED

    def test_cancel_from_submitted(self, sm: StateMachine) -> None:
        assert sm.validate_transition(TaskStatus.SUBMITTED, Trigger.CANCEL) == TaskStatus.CANCELED

    def test_cancel_from_in_progress(self, sm: StateMachine) -> None:
        assert sm.validate_transition(TaskStatus.IN_PROGRESS, Trigger.CANCEL) == TaskStatus.CANCELED

    def test_reopen_from_completed(self, sm: StateMachine) -> None:
        assert sm.validate_transition(TaskStatus.COMPLETED, Trigger.REOPEN) == TaskStatus.QUEUED

    def test_reopen_from_failed(self, sm: StateMachine) -> None:
        assert sm.validate_transition(TaskStatus.FAILED, Trigger.REOPEN) == TaskStatus.QUEUED

    def test_review_flow(self, sm: StateMachine) -> None:
        assert sm.validate_transition(TaskStatus.IN_PROGRESS, Trigger.SEND_REVIEW) == TaskStatus.REVIEW
        assert sm.validate_transition(TaskStatus.REVIEW, Trigger.APPROVE) == TaskStatus.COMPLETED
        assert sm.validate_transition(TaskStatus.REVIEW, Trigger.REJECT) == TaskStatus.IN_PROGRESS

    def test_block_unblock_cycle(self, sm: StateMachine) -> None:
        assert sm.validate_transition(TaskStatus.IN_PROGRESS, Trigger.BLOCK) == TaskStatus.BLOCKED
        assert sm.validate_transition(TaskStatus.BLOCKED, Trigger.UNBLOCK) == TaskStatus.IN_PROGRESS

    def test_input_required_cycle(self, sm: StateMachine) -> None:
        assert sm.validate_transition(
            TaskStatus.IN_PROGRESS, Trigger.REQUEST_INPUT
        ) == TaskStatus.INPUT_REQUIRED
        assert sm.validate_transition(
            TaskStatus.INPUT_REQUIRED, Trigger.RESUME
        ) == TaskStatus.IN_PROGRESS

    def test_submit_from_none(self, sm: StateMachine) -> None:
        assert sm.validate_transition(None, Trigger.SUBMIT) == TaskStatus.SUBMITTED

    def test_invalid_raises(self, sm: StateMachine) -> None:
        with pytest.raises(InvalidTransition) as exc_info:
            sm.validate_transition(TaskStatus.COMPLETED, Trigger.CLAIM)
        assert exc_info.value.current == TaskStatus.COMPLETED
        assert exc_info.value.trigger == Trigger.CLAIM

    def test_invalid_trigger_from_wrong_status(self, sm: StateMachine) -> None:
        with pytest.raises(InvalidTransition):
            sm.validate_transition(TaskStatus.QUEUED, Trigger.COMPLETE)

    def test_cannot_complete_from_queued(self, sm: StateMachine) -> None:
        with pytest.raises(InvalidTransition):
            sm.validate_transition(TaskStatus.QUEUED, Trigger.COMPLETE)

    def test_cannot_cancel_from_completed(self, sm: StateMachine) -> None:
        with pytest.raises(InvalidTransition):
            sm.validate_transition(TaskStatus.COMPLETED, Trigger.CANCEL)

    def test_error_message_content(self, sm: StateMachine) -> None:
        with pytest.raises(InvalidTransition, match="Cannot apply trigger"):
            sm.validate_transition(TaskStatus.FAILED, Trigger.BLOCK)


# ── get_available_triggers ─────────────────────────────────────────────────


class TestGetAvailableTriggers:
    def test_submitted_triggers(self, sm: StateMachine) -> None:
        triggers = sm.get_available_triggers(TaskStatus.SUBMITTED)
        assert Trigger.ENQUEUE in triggers
        assert Trigger.CANCEL in triggers
        assert Trigger.CLAIM not in triggers

    def test_queued_triggers(self, sm: StateMachine) -> None:
        triggers = sm.get_available_triggers(TaskStatus.QUEUED)
        assert Trigger.CLAIM in triggers
        assert Trigger.CANCEL in triggers

    def test_in_progress_triggers(self, sm: StateMachine) -> None:
        triggers = sm.get_available_triggers(TaskStatus.IN_PROGRESS)
        expected = {
            Trigger.REQUEST_INPUT, Trigger.BLOCK, Trigger.SEND_REVIEW,
            Trigger.COMPLETE, Trigger.FAIL, Trigger.CANCEL, Trigger.TIMEOUT,
        }
        assert set(triggers) == expected

    def test_terminal_state_only_reopen(self, sm: StateMachine) -> None:
        for status in TERMINAL_STATES:
            triggers = sm.get_available_triggers(status)
            assert triggers == [Trigger.REOPEN], f"Unexpected triggers for {status}"

    def test_blocked_triggers(self, sm: StateMachine) -> None:
        triggers = sm.get_available_triggers(TaskStatus.BLOCKED)
        assert set(triggers) == {Trigger.UNBLOCK, Trigger.CANCEL, Trigger.TIMEOUT}

    def test_review_triggers(self, sm: StateMachine) -> None:
        triggers = sm.get_available_triggers(TaskStatus.REVIEW)
        assert set(triggers) == {Trigger.APPROVE, Trigger.REJECT, Trigger.CANCEL}


# ── is_terminal ────────────────────────────────────────────────────────────


class TestIsTerminal:
    def test_terminal_states(self, sm: StateMachine) -> None:
        assert sm.is_terminal(TaskStatus.COMPLETED) is True
        assert sm.is_terminal(TaskStatus.FAILED) is True
        assert sm.is_terminal(TaskStatus.CANCELED) is True
        assert sm.is_terminal(TaskStatus.TIMED_OUT) is True

    def test_non_terminal_states(self, sm: StateMachine) -> None:
        non_terminal = {
            TaskStatus.SUBMITTED, TaskStatus.QUEUED, TaskStatus.IN_PROGRESS,
            TaskStatus.REVIEW, TaskStatus.INPUT_REQUIRED, TaskStatus.BLOCKED,
        }
        for status in non_terminal:
            assert sm.is_terminal(status) is False, f"{status} should not be terminal"


# ── Exception aliases ──────────────────────────────────────────────────────


class TestExceptionAliases:
    def test_transition_error_is_invalid_transition(self) -> None:
        assert TransitionError is InvalidTransition

    def test_gate_check_error_is_exception(self) -> None:
        assert issubclass(GateCheckError, Exception)


# ── Full lifecycle walk-through ────────────────────────────────────────────


class TestLifecycleWalkthrough:
    def test_happy_path(self, sm: StateMachine) -> None:
        status = sm.validate_transition(None, Trigger.SUBMIT)
        assert status == TaskStatus.SUBMITTED
        status = sm.validate_transition(status, Trigger.ENQUEUE)
        assert status == TaskStatus.QUEUED
        status = sm.validate_transition(status, Trigger.CLAIM)
        assert status == TaskStatus.IN_PROGRESS
        status = sm.validate_transition(status, Trigger.COMPLETE)
        assert status == TaskStatus.COMPLETED
        assert sm.is_terminal(status)

    def test_review_approve_path(self, sm: StateMachine) -> None:
        status = TaskStatus.IN_PROGRESS
        status = sm.validate_transition(status, Trigger.SEND_REVIEW)
        assert status == TaskStatus.REVIEW
        status = sm.validate_transition(status, Trigger.APPROVE)
        assert status == TaskStatus.COMPLETED

    def test_block_unblock_complete(self, sm: StateMachine) -> None:
        status = TaskStatus.IN_PROGRESS
        status = sm.validate_transition(status, Trigger.BLOCK)
        assert status == TaskStatus.BLOCKED
        status = sm.validate_transition(status, Trigger.UNBLOCK)
        assert status == TaskStatus.IN_PROGRESS
        status = sm.validate_transition(status, Trigger.COMPLETE)
        assert status == TaskStatus.COMPLETED

    def test_fail_and_reopen(self, sm: StateMachine) -> None:
        status = TaskStatus.IN_PROGRESS
        status = sm.validate_transition(status, Trigger.FAIL)
        assert status == TaskStatus.FAILED
        status = sm.validate_transition(status, Trigger.REOPEN)
        assert status == TaskStatus.QUEUED
