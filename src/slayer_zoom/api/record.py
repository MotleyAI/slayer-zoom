"""Record answers as traces. Needs the live demo database; agent runs and narration need an API key.

python -m slayer_zoom.api.record "<question>"     agent ladder + narration
python -m slayer_zoom.api.record --narrate NAME   add narration to a stored trace (no database)
python -m slayer_zoom.api.record --handwritten    the hand-written M1 ladder, without narration
"""

import argparse
import sys

from slayer_zoom.agent import answer_live
from slayer_zoom.core import query_hash, resolve_level
from slayer_zoom.executor import demo_executor
from slayer_zoom.narrator import live_narrator
from slayer_zoom.traces import LADDER, ReplayRunner, Trace, load_trace, save_trace, slug

DEMO_TRACE = "revenue_ytd"


def narrate(trace: Trace) -> Trace:
    narrator = live_narrator(trace.ladder.question)
    runner = ReplayRunner(trace)
    for level in trace.ladder.levels:
        narrator.narrate(resolve_level(level, runner))
        print("narrated level", level.index + 1, file=sys.stderr)
    return trace.model_copy(update={"narration": narrator.segments})


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("question", nargs="?")
    parser.add_argument("--name", help="trace file name; defaults to agent_<slug of the question>")
    parser.add_argument("--narrate", metavar="NAME", help="narrate a stored trace in place")
    parser.add_argument("--handwritten", action="store_true")
    args = parser.parse_args()
    if args.handwritten:
        executor = demo_executor()
        queries = {query_hash(p.query): p.query for level in LADDER.levels for p in level.panels}
        print(
            save_trace(
                DEMO_TRACE, Trace(ladder=LADDER, results={k: executor.run(q) for k, q in queries.items()})
            )
        )
    elif args.narrate:
        print(save_trace(args.narrate, narrate(load_trace(args.narrate))))
    elif args.question:
        trace = answer_live(args.question, emit=lambda kind, data: print(kind, data, file=sys.stderr))
        if trace is None:
            sys.exit("The agent submitted no level; nothing to save.")
        print(save_trace(args.name or f"agent_{slug(args.question)}", narrate(trace)))
    else:
        parser.error("give a question, --narrate NAME or --handwritten")


if __name__ == "__main__":
    main()
