"""Record an agent-built ladder: `python -m slayer_zoom.agent.record "<question>"`. Needs an API key."""

import argparse
import sys

from slayer_zoom.agent.loop import answer_live
from slayer_zoom.traces import save_trace, slug


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--name", help="trace file name; defaults to a slug of the question")
    args = parser.parse_args()
    trace = answer_live(args.question, emit=lambda kind, data: print(kind, data, file=sys.stderr))
    if trace is None:
        sys.exit("The agent submitted no level; nothing to save.")
    print(save_trace(args.name or f"agent_{slug(args.question)}", trace))


if __name__ == "__main__":
    main()
