"""
Symbolica command-line interface with DAG support.

Examples:
    $ python -m symbolica.cli compile        # build rulepack.rpack (legacy or DAG)
    $ python -m symbolica.cli compile-dag    # build rulepack with DAG features
    $ python -m symbolica.cli pack-info      # inspect rulepack metadata
    $ python -m symbolica.cli dag rules/     # show DAG analysis for folder
"""
from __future__ import annotations

import json
import pathlib
import sys
import typer
from typing import Optional

from symbolica.compiler import lint as lint_mod
from symbolica.compiler import packager
from symbolica.compiler import (
    create_default_compiler, 
    create_legacy_compiler
)
from symbolica.compiler.dag import build_execution_dag, visualize_execution_dag
from symbolica.runtime import loader, evaluator, api as rest_api
from symbolica.runtime.loader import load_pack

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
@CLI.command("compile")
def compile_rules(
    rules_path: str = typer.Argument(..., help="Path to YAML rules file/folder"),
    output: str = typer.Option("rulepack.rpack", help="Output .rpack filename"),
    enable_dag: bool = typer.Option(True, help="Enable DAG features (default) or use legacy mode")
):
    """Compile YAML rules → .rpack file."""
    
    if enable_dag:
        compiler = create_default_compiler()
        typer.secho(f"✔ DAG-enabled rulepack written to {output}", fg=typer.colors.GREEN)
    else:
        compiler = create_legacy_compiler()
        typer.secho(f"✔ Legacy rulepack written to {output}", fg=typer.colors.GREEN)
    
    compiler.compile_file_or_directory(rules_path, output)


# ─────────────────────────────────────────────────────────── compile-dag
@CLI.command("compile-dag")
def compile_dag_rules(
    rules_path: str = typer.Argument(..., help="Path to YAML rules file/folder"),
    output: str = typer.Option("rulepack.rpack", help="Output .rpack filename")
):
    """Compile YAML → .rpack with DAG features."""
    compiler = create_default_compiler()
    compiler.compile_file_or_directory(rules_path, output)
    typer.secho(f"✔ DAG-enabled rulepack written to {output}", fg=typer.colors.GREEN)


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


# ───────────────────────────────────────────────────────────── dag
@CLI.command()
def dag(
    rules: str = typer.Option("symbolica_rules", help="Folder containing YAML rule files"),
    format: str = typer.Option("layers", help="Output format: layers, summary"),
    output: Optional[str] = typer.Option(None, help="Output file (default: stdout)"),
) -> None:
    "Analyze and visualize rule execution DAG with parallel layers."
    try:
        from symbolica.compiler.dag import build_execution_dag, visualize_execution_dag
        from symbolica.compiler.parser import parse_yaml_file
        import pathlib as path_lib
        
        # Load all rules
        rules_list = []
        rules_dir = path_lib.Path(rules)
        
        if not rules_dir.exists():
            typer.secho(f"Rules directory not found: {rules}", fg=typer.colors.RED)
            raise typer.Exit(1)
        
        for yaml_file in rules_dir.rglob("*.yaml"):
            if yaml_file.name.endswith(".reg.yaml"):
                continue  # Skip registry files
            try:
                parsed_rules = parse_yaml_file(yaml_file)
                for raw_rule in parsed_rules:
                    rule_dict = {
                        "id": raw_rule["id"],
                        "priority": raw_rule["priority"],
                        "if": raw_rule["if_"],
                        "then": raw_rule["then"],
                        "tags": raw_rule["tags"]
                    }
                    rules_list.append(rule_dict)
            except Exception as e:
                typer.secho(f"Error parsing {yaml_file}: {e}", fg=typer.colors.YELLOW)
                continue
        
        if not rules_list:
            typer.secho("No rules found to analyze", fg=typer.colors.RED)
            raise typer.Exit(1)
        
        # Build ExecutionDAG
        execution_dag = build_execution_dag(rules_list)
        
        # Generate visualization  
        result = visualize_execution_dag(execution_dag, format)
        
        if output:
            pathlib.Path(output).write_text(result)
            typer.secho(f"DAG visualization written to {output}", fg=typer.colors.GREEN)
        else:
            typer.echo(result)
        
        # Print summary to stderr
        parallel_rules = sum(len(layer.rules) for layer in execution_dag.execution_layers if len(layer.rules) > 1)
        resolvable_conflicts = sum(1 for c in execution_dag.conflicts if c.resolvable)
        unresolvable_conflicts = len(execution_dag.conflicts) - resolvable_conflicts
        
        summary_lines = [
            f"Analyzed {len(execution_dag.rules)} rules in {len(execution_dag.execution_layers)} layers",
            f"Parallel opportunities: {parallel_rules} rules",
            f"Conflicts: {resolvable_conflicts} resolvable, {unresolvable_conflicts} unresolvable"
        ]
        
        for line in summary_lines:
            typer.secho(line, fg=typer.colors.BLUE, err=True)
            
    except ImportError as e:
        typer.secho(f"DAG analysis not available: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error analyzing DAG: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


# ───────────────────────────────────────────────────────────── dag-info
@CLI.command("dag-info")
def dag_info(
    rpack: str = typer.Option("rulepack.rpack", help="Path to .rpack file"),
) -> None:
    "Show execution DAG information from compiled .rpack file."
    try:
        pack_info = packager.get_pack_info(rpack)
        
        typer.echo(f"Pack: {pack_info['path']}")
        typer.echo(f"Version: {pack_info['version']}")
        typer.echo(f"Rules: {pack_info['rule_count']}")
        typer.echo(f"DAG Enabled: {pack_info['dag_enabled']}")
        
        if pack_info.get('dag_info'):
            dag_info = pack_info['dag_info']
            typer.echo(f"\nDAG Information:")
            typer.echo(f"  Execution Layers: {dag_info['execution_layers']}")
            typer.echo(f"  Parallel Opportunities: {dag_info['parallel_opportunities']}")
            typer.echo(f"  Input Fields: {dag_info['input_fields']}")
            typer.echo(f"  Output Fields: {dag_info['output_fields']}")
            typer.echo(f"  Conflicts: {dag_info['conflicts']}")
        else:
            typer.secho("No DAG information available (legacy pack)", fg=typer.colors.YELLOW)
        
    except Exception as e:
        typer.secho(f"Error reading DAG info: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


# ───────────────────────────────────────────────────────────── pack-info
@CLI.command("pack-info")  
def pack_info(
    rpack: str = typer.Option("rulepack.rpack", help="Path to .rpack file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    "Inspect compiled .rpack file details."
    try:
        info = packager.get_pack_info(rpack)
        
        typer.echo("Pack Information:")
        typer.echo("=" * 20)
        typer.echo(f"Path: {info['path']}")
        typer.echo(f"Version: {info['version']}")
        typer.echo(f"Built: {info['built']}")
        typer.echo(f"Rules: {info['rule_count']}")
        typer.echo(f"File Size: {info['file_size']} bytes")
        typer.echo(f"Agents: {', '.join(info['agents']) if info['agents'] else 'None'}")
        typer.echo(f"DAG Enabled: {info['dag_enabled']}")
        
        if info.get('dag_info'):
            dag_info = info['dag_info']
            typer.echo(f"\nDAG Details:")
            typer.echo(f"  Execution Layers: {dag_info['execution_layers']}")
            typer.echo(f"  Parallel Rules: {dag_info['parallel_opportunities']}")
            typer.echo(f"  Input Fields: {dag_info['input_fields']}")
            typer.echo(f"  Output Fields: {dag_info['output_fields']}")
            typer.echo(f"  Conflicts: {dag_info['conflicts']}")
        
        if verbose:
            typer.echo(f"\nRaw data:")
            typer.echo(json.dumps(info, indent=2))
        
    except Exception as e:
        typer.secho(f"Error reading pack info: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


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
