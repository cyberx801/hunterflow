"""Worker entrypoint: `python -m app.jobs.worker [--processes N] [--threads M]`."""

from __future__ import annotations

import argparse

from dramatiq.cli import main as dramatiq_main
from dramatiq.cli import make_argument_parser

from ..core.config import get_settings
from .broker import setup_broker


def main() -> None:
    parser = argparse.ArgumentParser(description="HunterFlow worker")
    parser.add_argument("--processes", type=int, default=2)
    parser.add_argument("--threads", type=int, default=8)
    options = parser.parse_args()

    settings = get_settings()
    setup_broker(settings, stub=False)

    cli_parser = make_argument_parser()
    args = cli_parser.parse_args(
        [
            "app.jobs.actors",
            "--processes",
            str(options.processes),
            "--threads",
            str(options.threads),
        ]
    )
    raise SystemExit(dramatiq_main(args))


if __name__ == "__main__":
    main()
