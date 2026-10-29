"""Worker entrypoint: `python -m app.jobs.worker [--processes N] [--threads M]`."""

from __future__ import annotations

import argparse

from ..core.config import get_settings
from . import actors  # noqa: F401 (registers actors)
from .broker import setup_broker

try:
    from dramatiq.cli import main as dramatiq_main
except ImportError:  # pragma: no cover
    dramatiq_main = None


def main() -> None:
    parser = argparse.ArgumentParser(description="HunterFlow worker")
    parser.add_argument("--processes", type=int, default=2)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()

    settings = get_settings()
    setup_broker(settings, stub=False)

    if dramatiq_main is not None:
        raise SystemExit(
            dramatiq_main(
                [
                    "app.jobs.actors",
                    "--processes",
                    str(args.processes),
                    "--threads",
                    str(args.threads),
                ]
            )
        )


if __name__ == "__main__":
    main()
