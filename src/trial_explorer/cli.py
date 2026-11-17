"""Command-line entry point for snapshot collection."""

import argparse
import json
import sys
from pathlib import Path
import sqlite3
from contextlib import closing
from dataclasses import asdict

from trial_explorer.store import connect_database, get_passages, get_study, import_snapshot
from trial_explorer.snapshots import collect_snapshot


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Expected a positive integer")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trial-explorer")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Collect a public study snapshot")
    fetch.add_argument("--output-root", type=Path, default=Path("data/raw"))
    importer = commands.add_parser(
        "import-snapshot", help="Import a complete snapshot into SQLite"
    )
    importer.add_argument("--snapshot", type=Path, required=True)
    importer.add_argument("--db", type=Path, required=True)
    for name in ("read-study", "read-passages"):
        reader = commands.add_parser(name, help="Read saved evidence from SQLite")
        reader.add_argument("--db", type=Path, required=True)
        reader.add_argument("--snapshot-id", required=True)
        reader.add_argument("--nct-id", required=True)
        if name == "read-passages":
            reader.add_argument("--limit", type=positive_integer)
    args = parser.parse_args(argv)
    if args.command in ("read-study", "read-passages"):
        try:
            uri = args.db.resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                study = get_study(connection, args.snapshot_id, args.nct_id)
                if study is None:
                    print(json.dumps({"error": "study_not_found"}), file=sys.stderr)
                    return 2
                if args.command == "read-study":
                    result = asdict(study)
                    result["retrieved_at"] = study.retrieved_at.isoformat()
                else:
                    passages = get_passages(connection, args.snapshot_id, args.nct_id)
                    items = passages[:args.limit]
                    result = {
                        "snapshot_id": args.snapshot_id,
                        "nct_id": args.nct_id,
                        "total": len(passages),
                        "returned_count": len(items),
                        "items": [asdict(passage) for passage in items],
                    }
        except (OSError, sqlite3.Error, ValueError) as error:
            print(json.dumps({"error": "read_failed", "message": str(error)}), file=sys.stderr)
            return 3
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "import-snapshot":
        try:
            with closing(connect_database(args.db)) as connection:
                study_count, passage_count = import_snapshot(
                    connection, args.snapshot
                )
        except ValueError as error:
            print(
                json.dumps({"error": "invalid_snapshot", "message": str(error)}),
                file=sys.stderr,
            )
            return 2
        except (OSError, sqlite3.Error) as error:
            print(
                json.dumps({"error": "import_failed", "message": str(error)}),
                file=sys.stderr,
            )
            return 3

        print(json.dumps({
            "database_path": str(args.db),
            "study_count": study_count,
            "passage_count": passage_count,
        }))
        return 0
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
