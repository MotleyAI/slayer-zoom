"""The ladder agent: Claude in a Tool Runner loop over the session's tools."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import anthropic
from anthropic import beta_tool
from anthropic.lib.tools import BetaFunctionTool, ToolError

from slayer_zoom.agent.prompts import system_prompt
from slayer_zoom.agent.session import Budget, Emit, LadderSession, ToolFailure
from slayer_zoom.catalog import demo_catalog
from slayer_zoom.context import load_context
from slayer_zoom.core import Panel, SlayerQuery
from slayer_zoom.executor import demo_executor
from slayer_zoom.traces import RecordingRunner, Trace

MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
EFFORT = "medium"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

TOOL_NAMES = (
    "list_models",
    "describe_model",
    "profile_dimension",
    "read_context",
    "validate_query",
    "probe_query",
    "submit_level",
    "finish",
)


def _guard[**P](session: LadderSession, call: Callable[P, str]) -> Callable[P, str]:
    def guarded(*args: P.args, **kwargs: P.kwargs) -> str:
        try:
            return call(*args, **kwargs)
        except ToolFailure as error:
            session.fail(str(error))
            raise ToolError(str(error)) from error

    return guarded


def _add_usage(session: LadderSession, usage: object) -> None:
    for field in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        value = getattr(usage, field, None)
        if isinstance(value, int):
            session.usage[field] = session.usage.get(field, 0) + value


def build_tools(session: LadderSession) -> list[BetaFunctionTool[Any]]:
    """The agent's whole surface: reads of the semantic layer, probes, and levels made of SLayer queries."""

    @beta_tool
    def list_models() -> str:
        """List the semantic layer's models with their descriptions and saved measures."""
        return _guard(session, session.list_models)()

    @beta_tool
    def describe_model(name: str) -> str:
        """Describe one model: columns (types, labels, descriptions), saved measures with formulas, and joins.

        Args:
            name: The model name, for example "orders".
        """
        return _guard(session, session.describe_model)(name)

    @beta_tool
    def profile_dimension(model: str, dimension: str) -> str:
        """Profile a dimension: rows per value (top values first), share of the top value, share of nulls,
        and the first and last date for a time dimension.

        Args:
            model: The model to count rows of, for example "orders".
            dimension: A column of the model or a joined column by path, for example "stores.name".
        """
        return _guard(session, session.profile_dimension)(model, dimension)

    @beta_tool
    def read_context() -> str:
        """Read the business context: glossary, fiscal calendar, audience and known caveats."""
        return _guard(session, session.read_context)()

    @beta_tool
    def validate_query(query: SlayerQuery) -> str:
        """Check a SLayer query without running it. Returns "valid" or the errors.

        Args:
            query: The SLayer query.
        """
        return _guard(session, session.validate_query)(query)

    @beta_tool
    def probe_query(query: SlayerQuery) -> str:
        """Run a small SLayer query (at most 20 rows) to check that a step is viable, for example whether
        last year's data exists. Probe results are for you; the reader never sees them.

        Args:
            query: The SLayer query.
        """
        return _guard(session, session.probe_query)(query)

    @beta_tool
    def submit_level(title: str, panels: list[Panel], rationale: str) -> str:
        """Submit the next level of the ladder. It is validated against the semantic layer and the monotonic
        rule, then run and shown to the reader at once. On errors nothing is shown; fix them and submit again.

        Args:
            title: One or two words naming the level, for example "Split".
            panels: Every panel of the level, including the previous level's panels that it keeps.
            rationale: One sentence on what this level adds, with no numbers in it.
        """
        return _guard(session, session.submit_level)(title, panels, rationale)

    @beta_tool
    def finish(summary: str) -> str:
        """End the ladder once 2 to 6 levels are accepted.

        Args:
            summary: One sentence describing the ladder, with no numbers in it.
        """
        return _guard(session, session.finish)(summary)

    return [
        list_models,
        describe_model,
        profile_dimension,
        read_context,
        validate_query,
        probe_query,
        submit_level,
        finish,
    ]


def run_agent(session: LadderSession, client: anthropic.Anthropic, system: str) -> None:
    """Runs the loop until the agent finishes, the budget runs out, or the model declines."""
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=build_tools(session),
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": session.question}],
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT},
        cache_control={"type": "ephemeral"},
        betas=[FALLBACK_BETA],
        fallbacks="default",
        max_iterations=session.budget.max_tool_calls + 5,
    )
    for message in runner:
        if session.finished:
            break
        _add_usage(session, getattr(message, "usage", None))
        for block in message.content:
            if block.type == "text" and block.text.strip():
                session.note(block.text.strip())
        if message.stop_reason == "refusal":
            session.note("The model declined to continue; the levels already built stand.")
            break
    if not session.finished:
        session.finished = True
        session.summary = (
            session.summary or "The run ended before the agent finished; the levels built stand."
        )


def answer_live(
    question: str,
    emit: Emit | None = None,
    storage_path: str | Path = ".slayer",
    client: anthropic.Anthropic | None = None,
    budget: Budget | None = None,
) -> Trace | None:
    """Builds a ladder for the question on the live demo database, and returns it as a trace to store."""
    catalog = demo_catalog(storage_path)
    recorder = RecordingRunner(demo_executor(storage_path))
    context = load_context("jaffle_shop")
    session = LadderSession(question, catalog, recorder, context, budget=budget, emit=emit)
    run_agent(session, client or anthropic.Anthropic(), system_prompt(context, catalog.list_models()))
    ladder = session.ladder()
    if ladder is None:
        return None
    return Trace(
        ladder=ladder,
        results=recorder.results,
        steps=session.steps,
        summary=session.summary,
        usage=session.usage,
    )
