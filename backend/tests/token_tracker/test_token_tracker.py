import logging
from datetime import datetime

from app.services.token_tracker import TokenTracker
from app.services import token_tracker as token_tracker_module


class _FixedDatetime:
    """Deterministic datetime provider for tests (supports only datetime.now())."""

    def __init__(self, times: list[datetime]):
        self._times = iter(times)

    def now(self) -> datetime:
        return next(self._times)


def test_get_current_context_tokens_returns_zero_without_warning_when_no_usage_data(caplog):
    tracker = TokenTracker()

    with caplog.at_level(logging.WARNING, logger="app.services.token_tracker"):
        assert tracker.get_current_context_tokens("nb-123") == 0

    # "No usage yet" is a normal state; it must not produce WARNING log spam.
    assert caplog.records == []


def test_get_current_context_tokens_returns_latest_input_tokens(monkeypatch):
    tracker = TokenTracker()

    t1 = datetime(2026, 1, 1, 0, 0, 0)
    t2 = datetime(2026, 1, 1, 0, 0, 1)
    monkeypatch.setattr(token_tracker_module, "datetime", _FixedDatetime([t1, t1, t2, t2]), raising=True)

    tracker.track_generation(
        notebook_id="nb-123",
        cell_id="cell-1",
        usage_data={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        generation_time_ms=12.3,
    )

    tracker.track_generation(
        notebook_id="nb-123",
        cell_id="cell-2",
        usage_data={"input_tokens": 20, "output_tokens": 2, "total_tokens": 22},
        generation_time_ms=4.5,
    )

    assert tracker.get_current_context_tokens("nb-123") == 20

