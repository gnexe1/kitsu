"""POPAL main entry point."""

from __future__ import annotations

import sys

from popal.cli.shell import Shell


def main() -> None:
    """Launch the POPAL CLI."""
    shell = Shell()
    try:
        shell.run()
    except KeyboardInterrupt:
        print("\nPOPAL interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()