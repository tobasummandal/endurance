"""`helios-review` CLI — what an agent's tool runtime invokes via subprocess
when it doesn't want to import Python directly.

Usage:
    helios-review path/to/file.py            # static-only
    helios-review --deep path/to/file.py     # static + LLM
    cat foo.py | helios-review -             # stdin
    helios-review --json path/to/file.py     # machine-readable
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .client import HeliosClient
from .review import review_code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="helios-review",
        description="Audit scientific Python for silent bugs (off-by-one, "
                    "unit mismatches, numerical instability, etc.).",
    )
    p.add_argument("path", help="Path to .py file, or '-' for stdin")
    p.add_argument("--deep", action="store_true",
                   help="Run LLM audit in addition to static checks")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of human-readable text")
    p.add_argument("--api", default=None, help="Helios API base URL")
    p.add_argument("--filename", default=None,
                   help="Override filename used in prompts/findings")
    p.add_argument("--ignore-warning", action="store_true",
                   help="Suppress the non-scientific-code warning")
    args = p.parse_args(argv)

    if args.path == "-":
        source = sys.stdin.read()
        filename = args.filename or "stdin.py"
    else:
        path = Path(args.path)
        if not path.exists():
            print(f"helios-review: file not found: {path}", file=sys.stderr)
            return 2
        source = path.read_text()
        filename = args.filename or path.name

    client = HeliosClient(base_url=args.api) if args.api else HeliosClient()
    review = review_code(source, filename=filename, deep=args.deep, client=client)

    if args.json:
        out = review.to_dict()
        if args.ignore_warning:
            out["warning"] = None
        print(json.dumps(out, indent=2))
    else:
        if review.warning and not args.ignore_warning:
            print(review.warning, file=sys.stderr)
            print("", file=sys.stderr)
        print(review.to_agent_text())

    if review.error:
        return 3
    high = sum(1 for f in review.findings if f.get("severity") in ("high", "critical"))
    return 1 if high else 0


if __name__ == "__main__":
    raise SystemExit(main())
