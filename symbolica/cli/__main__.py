"""
Symbolica command-line interface.

$ python -m symbolica.cli lint           # YAML lint
$ python -m symbolica.cli test           # unit / dataset test
$ python -m symbolica.cli compile        # build rulepack.rpack
$ python -m symbolica.cli run            # local REST server
$ python -m symbolica.cli infer          # one-shot inference
$ python -m symbolica.cli trace          # pretty-print saved trace
"""
from __future__ import annotations

import json
import pathlib
import sys
import typer
from typing import Optional

from symbolica.compiler import lint as lint_mod
from symbolica.compiler import packager
from symbolica.runtime import loader, evaluator, api as rest_api

CLI = typer.Typer(add_help_option=True, pretty_exceptions_enable=False)


# ───────────────────────────────────────────────────────────── lint
@CLI.command()
def lint(
    rules: str = typer.Option(
        "symbolica_rules", help="Folder containing YAML rule files."
    )
) -> None:
    "Static-lint all YAML files; exit non-zero on error."
    errs = lint_mod.lint_folder(rules)
    if errs:
        typer.secho(f"{errs} lint error(s)", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho("No lint errors", fg=typer.colors.GREEN)


# ───────────────────────────────────────────────────────────── compile
@CLI.command()
def compile(
    rules: str = typer.Option("symbolica_rules"),
    output: str = typer.Option("rulepack.rpack"),
) -> None:
    "Compile YAML → .rpack."
    packager.build_pack(rules_dir=rules, output_path=output)
    typer.secho(f"✔ rulepack written to {output}", fg=typer.colors.GREEN)


# ───────────────────────────────────────────────────────────── run
@CLI.command()
def run(
    rpack: str = typer.Option("rulepack.rpack"),
    port: int = typer.Option(8080),
    reload_ms: int = typer.Option(1_000, help="Hot-reload watch interval ms"),
) -> None:
    "Start a local REST server that serves /infer."
    from fastapi import FastAPI
    import uvicorn

    loader.load_pack(rpack)
    app: Optional[FastAPI] = rest_api.app
    if app is None:
        typer.secho("fastapi not installed", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Serving {rpack} on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)


# ───────────────────────────────────────────────────────────── infer
@CLI.command()
def infer(
    facts_file: pathlib.Path = typer.Argument(..., exists=True),
    agent: str = typer.Option(..., help="Agent name / registry"),
    rpack: str = typer.Option("rulepack.rpack"),
    trace_level: str = typer.Option("compact"),
) -> None:
    "Run a single inference on a JSON fact file."
    loader.load_pack(rpack)
    facts = json.loads(facts_file.read_text())
    verdict, trace = evaluator.infer(facts, agent, trace_level)
    print(json.dumps({"verdict": verdict, "trace": trace}, indent=2))


# ───────────────────────────────────────────────────────────── trace
@CLI.command()
def trace(
    file: pathlib.Path = typer.Argument(..., exists=True, readable=True),
    id: Optional[str] = typer.Option(None, help="Filter by run_id or claim_id"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    "Pretty-print stored trace JSON lines."
    for line in file.open():
        obj = json.loads(line)
        if id and id not in (obj.get("run_id") or ""):
            continue
        if verbose:
            print(json.dumps(obj, indent=2))
        else:
            print(obj.get("final") or obj)


# ───────────────────────────────────────────────────────────── test (stub)
@CLI.command()
def test(
    dataset: pathlib.Path = typer.Option(
        None, help="JSONL dataset file for regression tests."
    ),
    agent: str = typer.Option("ClaimDecider"),
    rpack: str = typer.Option("rulepack.rpack"),
) -> None:
    "Run rulepack against a dataset; simple accuracy report (stub)."
    if dataset is None:
        typer.echo("provide --dataset path", err=True)
        raise typer.Exit(1)

    loader.load_pack(rpack)
    good = bad = 0
    for line in dataset.open():
        rec = json.loads(line)
        expected = rec.get("expected_status")
        verdict, _ = evaluator.infer(rec, agent, trace_level="compact")
        if verdict.get("decision_status") == expected:
            good += 1
        else:
            bad += 1
    total = good + bad
    typer.secho(f"Accuracy {good}/{total} = {good/total:.2%}", fg=typer.colors.GREEN)


# ───────────────────────────────────────────────────────────── entry
def _main() -> None:  # pragma: no cover
    CLI()


if __name__ == "__main__":
    _main()
