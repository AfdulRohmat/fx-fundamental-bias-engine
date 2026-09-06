"""Command-line entry points for the fundamental-bias research."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .phase02_fetch import fetch_phase02
from .phase02_panel import build_phase02
from .phase03_models import build_phase03
from .phase04_fx import build_phase04
from .phase05_gate import build_phase05
from .qualification import load_catalog, summarize, write_matrix, write_summary
from .research_config import load_research_config
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

    fetch = commands.add_parser("phase02-fetch")
    fetch.add_argument("--config", type=Path, required=True)
    fetch.add_argument("--raw-root", type=Path, required=True)

    panel = commands.add_parser("phase02-build")
    panel.add_argument("--config", type=Path, required=True)
    panel.add_argument("--raw-root", type=Path, required=True)
    panel.add_argument("--output", type=Path, required=True)

    models = commands.add_parser("phase03-build")
    models.add_argument("--config", type=Path, required=True)
    models.add_argument("--panel", type=Path, required=True)
    models.add_argument("--phase02-summary", type=Path, required=True)
    models.add_argument("--output", type=Path, required=True)

    fx = commands.add_parser("phase04-build")
    fx.add_argument("--config", type=Path, required=True)
    fx.add_argument("--predictions", type=Path, required=True)
    fx.add_argument("--ecb", type=Path, required=True)
    fx.add_argument("--output", type=Path, required=True)

    gate = commands.add_parser("phase05-build")
    gate.add_argument("--config", type=Path, required=True)
    gate.add_argument("--phase02", type=Path, required=True)
    gate.add_argument("--phase03", type=Path, required=True)
    gate.add_argument("--phase04", type=Path, required=True)
    gate.add_argument("--output", type=Path, required=True)
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
    if arguments.command == "phase02-fetch":
        config = load_research_config(arguments.config)
        result = fetch_phase02(config, arguments.raw_root)
        print(
            f"alfred_files={result['alfred_file_count']} "
            f"eiopa_files={result['eiopa_file_count']}"
        )
        return 0
    if arguments.command == "phase02-build":
        config = load_research_config(arguments.config)
        result = build_phase02(config, arguments.raw_root, arguments.output)
        print(
            f"status={result['status']} rows={result['row_count']} "
            f"complete={result['complete_row_count']}"
        )
        return 0
    if arguments.command == "phase03-build":
        config = load_research_config(arguments.config)
        result = build_phase03(
            config,
            arguments.panel,
            arguments.phase02_summary,
            arguments.output,
        )
        print(
            f"status={result['status']} "
            f"h1={result['FB_H1_POLICY_SKILL_P1Y']} "
            f"h2={result['FB_H2_PROXY_REPRICING_SKILL_P1Y']}"
        )
        return 0
    if arguments.command == "phase04-build":
        config = load_research_config(arguments.config)
        result = build_phase04(
            config, arguments.predictions, arguments.ecb, arguments.output
        )
        print(
            f"status={result['status']} "
            f"g10_months={result['low_history_exploratory']['full_g10_month_count']}"
        )
        return 0
    if arguments.command == "phase05-build":
        config = load_research_config(arguments.config)
        result = build_phase05(
            config,
            arguments.phase02,
            arguments.phase03,
            arguments.phase04,
            arguments.output,
        )
        print(
            f"decision={result['decision']} "
            f"gates={result['passed_gate_count']}/{result['gate_count']}"
        )
        return 0
    raise AssertionError(f"Unhandled command: {arguments.command}")
