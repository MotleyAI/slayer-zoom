"""Every recorded agent trace replays on its own and obeys the ladder invariants."""

import pytest

from slayer_zoom.core import StepKind, monotonic_violations
from slayer_zoom.traces import ReplayRunner, Trace, load_traces

AGENT_TRACES = [trace for trace in load_traces() if trace.steps]


def test_at_least_one_agent_trace_is_recorded() -> None:
    assert AGENT_TRACES


@pytest.mark.parametrize("trace", AGENT_TRACES, ids=lambda t: t.ladder.question)
def test_agent_trace_is_monotonic_and_replays_every_panel(trace: Trace) -> None:
    assert monotonic_violations(trace.ladder) == []
    runner = ReplayRunner(trace)
    for level in trace.ladder.levels:
        for panel in level.panels:
            assert runner.run(panel.query).rows, panel.id


@pytest.mark.parametrize("trace", AGENT_TRACES, ids=lambda t: t.ladder.question)
def test_agent_trace_records_each_level_once_in_order(trace: Trace) -> None:
    landed = [step.level for step in trace.steps if step.kind == StepKind.LEVEL]
    assert landed == list(range(len(trace.ladder.levels)))
    assert trace.summary
