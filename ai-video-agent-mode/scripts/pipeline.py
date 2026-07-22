"""Compatibility blocker for the retired monolithic pipeline entry point."""

import sys


def main() -> int:
    print(
        "pipeline.py has been retired. Start with route_task.py and follow the "
        "Phase 0-10 route selected in SKILL.md."
    )
    print(
        "For an existing validated run, use pipeline_runner.py for state inspection "
        "or export_with_validation.py for export."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
