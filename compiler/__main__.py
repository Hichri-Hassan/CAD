"""Allow running the compiler as `python -m compiler`."""

from compiler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
