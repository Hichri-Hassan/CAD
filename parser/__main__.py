"""Allow running the parser as `python -m parser`."""

from parser.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
