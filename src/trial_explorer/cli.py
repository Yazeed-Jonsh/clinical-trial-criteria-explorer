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
from trial_explorer.search import keyword_search
from trial_explorer.evaluation import evaluate_retrieval, load_evaluation_cases
from trial_explorer.store import get_snapshot_passages


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

    search = commands.add_parser("search", help="Search stored criteria passages")
    search.add_argument("--db", type=Path, required=True)
    search.add_argument("--snapshot-id", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--mode", choices=["keyword"], default="keyword")
    search.add_argument("--nct-id", action="append", help="Restrict to a study; repeat for multiple IDs")
    search.add_argument(
        "--recruitment-status", action="append",
        help="Restrict to a recruitment status; repeat for multiple statuses",
    )

    evaluator = commands.add_parser("evaluate-retrieval", help="Measure labeled passage recall@5")
    evaluator.add_argument("--db", type=Path, required=True)
    evaluator.add_argument("--snapshot-id", required=True)
    evaluator.add_argument("--cases", type=Path, required=True)
    evaluator.add_argument("--output", type=Path, required=True)
    evaluator.add_argument("--mode", choices=["keyword"], default="keyword")

    args = parser.parse_args(argv)
    if args.command == "evaluate-retrieval":
        try:
            cases = load_evaluation_cases(args.cases)
            uri = args.db.resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                report = evaluate_retrieval(connection, cases, args.snapshot_id)
            serialized = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
            with args.output.open("x", encoding="utf-8") as output:
                output.write(serialized)
        except ValueError as error:
            print(json.dumps({"error": "invalid_evaluation_labels", "message": str(error)}), file=sys.stderr)
            return 5
        except (OSError, sqlite3.Error) as error:
            print(json.dumps({"error": "evaluation_failed", "message": str(error)}), file=sys.stderr)
            return 3
        print(json.dumps({
            "report_path": str(args.output), "case_count": report["case_count"],
            "check_count": report["check_count"], "summaries": report["summaries"],
        }, indent=2))
        return 0
    if args.command == "search":
        try:
            uri = args.db.resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                result = keyword_search(
                    connection, args.snapshot_id, args.query,
                    nct_ids=args.nct_id,
                    recruitment_statuses=args.recruitment_status,
                )
        except ValueError as error:
            print(
                json.dumps({"error": "invalid_search", "message": str(error)}),
                file=sys.stderr,
            )
            return 2
        except (OSError, sqlite3.Error) as error:
            print(
                json.dumps({"error": "search_failed", "message": str(error)}),
                file=sys.stderr,
            )
            return 3

        print(json.dumps(result, indent=2))
        return 0

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
