"""Command-line entry points for the fundamental-bias research."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .qualification import load_catalog, summarize, write_matrix, write_summary
from .source_poc import build_phase01_evidence, write_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fbias")
    commands = parser.add_subparsers(dest="command", required=True)

    matrix = commands.add_parser("phase01-matrix")
    matrix.add_argument("--catalog", type=Path, required=True)
    matrix.add_argument("--matrix", type=Path, required=True)
    matrix.add_argument("--summary", type=Path, required=True)

    poc = commands.add_parser("phase01-poc")
    poc.add_argument("--eiopa", type=Path, action="append", required=True)
    poc.add_argument("--ecb", type=Path, required=True)
    poc.add_argument("--bis", type=Path, required=True)
    poc.add_argument("--alfred", type=Path, action="append", required=True)
    poc.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command == "phase01-matrix":
        rows = load_catalog(arguments.catalog)
        result = summarize(rows)
        write_matrix(arguments.matrix, rows)
        write_summary(arguments.summary, result)
        print(f"phase_decision={result['phase_decision']} rows={result['row_count']}")
        return 0
    if arguments.command == "phase01-poc":
        result = build_phase01_evidence(
            eiopa_paths=arguments.eiopa,
            ecb_path=arguments.ecb,
            bis_path=arguments.bis,
            alfred_paths=arguments.alfred,
        )
        write_json(arguments.output, result)
        print(f"phase_decision={result['phase_decision']}")
        return 0
    raise AssertionError(f"Unhandled command: {arguments.command}")
