"""Command-line entry point for snapshot collection."""

import argparse
import json
import sys
from pathlib import Path

from trial_explorer.snapshots import collect_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trial-explorer")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Collect a public study snapshot")
    fetch.add_argument("--output-root", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)

    try:
        path, manifest = collect_snapshot(args.output_root)
    except OSError as error:
        print(json.dumps({"error": "snapshot_write_failed", "message": str(error)}), file=sys.stderr)
        return 3

    print(json.dumps({
        "snapshot_id": manifest["snapshot_id"],
        "manifest_path": str(path),
        "fetch_status": manifest["fetch_status"],
        "stop_reason": manifest["stop_reason"],
        "selected_count": manifest["selected_count"],
        "target_met": manifest["target_met"],
    }))
    if manifest["fetch_status"] == "partial":
        print(json.dumps({"error": manifest["error_code"], "path": manifest["error_path"]}), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
