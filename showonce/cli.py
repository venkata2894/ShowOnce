"""
Command Line Interface for ShowOnce.

Provides commands for recording, analyzing, generating, and running workflows.

Usage:
    showonce record --name "my_workflow"
    showonce analyze --workflow "my_workflow"
    showonce generate --workflow "my_workflow"
    showonce run --workflow "my_workflow"
    showonce list
    showonce info --workflow "my_workflow"
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from showonce import __version__
from showonce.config import get_config
from showonce.models import Workflow
from showonce.utils.logger import log, setup_logging


# Rich console for output
console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="ShowOnce")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def main(debug: bool):
    """
    ShowOnce - AI-powered workflow automation from screenshots.
    
    Show me once. I'll do it forever.
    """
    level = "DEBUG" if debug else "INFO"
    setup_logging(level=level)


@main.command()
@click.option("--name", "-n", required=True, help="Name for the workflow")
@click.option("--description", "-d", default=None, help="Workflow description")
def record(name: str, description: Optional[str]):
    """
    Record a new workflow by capturing screenshots.
    
    Press Ctrl+Shift+S to capture each step.
    Press Ctrl+Shift+Q to stop recording.
    """
    # Import here to avoid circular dependencies if any, and ensure clean startup
    from showonce.capture import record_workflow
    
    try:
        workflow = record_workflow(name, description)
        
        if workflow and workflow.step_count > 0:
            console.print()
            log.success(f"Workflow '{name}' recorded successfully!")
            console.print(workflow.summary())
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording cancelled.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error during recording: {e}[/bold red]")


@main.command()
@click.option("--workflow", "-w", required=True, help="Workflow name to analyze")
def analyze(workflow: str):
    """
    Analyze a recorded workflow using AI vision.
    
    Processes screenshots to infer actions between steps.
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from showonce.analyze import ActionInferenceEngine
    
    log.banner()
    log.section(f"Analyzing: {workflow}")
    
    config = get_config()
    
    # Check API key
    if not config.analyze.api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not set[/red]")
        console.print("Please add your API key to .env file")
        sys.exit(1)
    
    # Load workflow
    workflow_path = config.paths.workflows_dir / workflow
    if not workflow_path.exists():
        console.print(f"[red]Error: Workflow not found: {workflow}[/red]")
        sys.exit(1)
    
    wf = Workflow.load(workflow_path)
    console.print(f"[cyan]Loaded workflow with {wf.step_count} steps[/cyan]")
    
    if wf.step_count < 2:
        console.print("[yellow]Workflow needs at least 2 steps to analyze transitions.[/yellow]")
        return
    
    total_transitions = wf.step_count - 1
    console.print(f"[dim]Analyzing {total_transitions} transition(s)...[/dim]\n")
    
    try:
        engine = ActionInferenceEngine()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing...", total=total_transitions)
            
            def update_progress(current: int, total: int):
                progress.update(task, completed=current, description=f"Step {current}/{total}")
            
            action_sequence = engine.analyze_workflow(wf, progress_callback=update_progress)
        
        # Display results
        console.print()
        log.section("Inferred Actions")
        
        for action in action_sequence.actions:
            action_type = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)
            confidence_pct = int(action.confidence * 100)
            
            # Color based on confidence
            if confidence_pct >= 80:
                conf_color = "green"
            elif confidence_pct >= 50:
                conf_color = "yellow"
            else:
                conf_color = "red"
            
            console.print(
                f"  [{conf_color}]●[/{conf_color}] "
                f"[bold]{action.sequence}.[/bold] "
                f"[cyan]{action_type.upper()}[/cyan] - "
                f"{action.description or 'No description'} "
                f"[dim]({confidence_pct}% confidence)[/dim]"
            )
            
            if action.target and action.target.get_primary_selector():
                sel = action.target.get_primary_selector()
                console.print(f"      [dim]Selector: {sel.value}[/dim]")
        
        # Save analysis to workflow
        wf.analyzed = True
        # Store action sequence data in workflow metadata or as separate file
        # For now, save the workflow to mark it as analyzed
        wf.save(workflow_path)
        
        console.print()
        log.success(f"Analysis complete! {len(action_sequence.actions)} actions inferred.")
        console.print(f"[dim]Workflow saved to: {workflow_path}[/dim]")
        
    except Exception as e:
        console.print(f"\n[bold red]Error during analysis: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--workflow", "-w", required=True, help="Workflow name to generate code for")
@click.option("--framework", "-f", default=None, 
              type=click.Choice(["playwright", "selenium", "pyautogui"]),
              help="Automation framework to use")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--headless", is_flag=True, help="Generate with headless mode enabled")
def generate(workflow: str, framework: Optional[str], output: Optional[str], headless: bool):
    """
    Generate automation script from analyzed workflow.
    """
    import json
    from showonce.generate import get_generator
    from showonce.analyze import ActionInferenceEngine
    
    log.banner()
    log.section(f"Generating: {workflow}")
    
    config = get_config()
    framework = framework or config.generate.default_framework
    
    # Load workflow
    workflow_path = config.paths.workflows_dir / workflow
    if not workflow_path.exists():
        console.print(f"[red]Error: Workflow not found: {workflow}[/red]")
        sys.exit(1)
    
    wf = Workflow.load(workflow_path)
    console.print(f"[cyan]Loaded workflow with {wf.step_count} steps[/cyan]")
    
    # Check if analyzed
    if not wf.analyzed:
        console.print("[yellow]Warning: Workflow has not been analyzed yet[/yellow]")
        console.print("[dim]Running analysis first...[/dim]\n")
        
        # Run analysis
        if not config.analyze.api_key:
            console.print("[red]Error: Cannot analyze - ANTHROPIC_API_KEY not set[/red]")
            sys.exit(1)
        
        engine = ActionInferenceEngine()
        action_sequence = engine.analyze_workflow(wf)
        wf.analyzed = True
        wf.save(workflow_path)
    else:
        # Load existing analysis or re-analyze
        console.print("[green]Workflow already analyzed[/green]")
        engine = ActionInferenceEngine()
        action_sequence = engine.analyze_workflow(wf)
    
    console.print(f"[cyan]Framework:[/cyan] {framework}")
    console.print(f"[cyan]Actions:[/cyan] {len(action_sequence.actions)}")
    
    try:
        # Get appropriate generator
        generator = get_generator(framework, headless=headless)
        
        # Generate code
        code = generator.generate(action_sequence)
        
        # Determine output path
        if output:
            output_path = Path(output)
        else:
            output_path = config.paths.output_dir / f"{workflow}_{framework}.py"
        
        # Save code
        generator.save(code, output_path)
        
        # Display summary
        console.print()
        log.section("Generated Script")
        
        # Show first 30 lines
        lines = code.split('\n')
        preview_lines = lines[:30]
        for i, line in enumerate(preview_lines, 1):
            console.print(f"[dim]{i:3}[/dim] {line}")
        
        if len(lines) > 30:
            console.print(f"[dim]... ({len(lines) - 30} more lines)[/dim]")
        
        console.print()
        log.success(f"Script generated: {output_path}")
        console.print(f"[dim]Run with: python {output_path}[/dim]")
        
    except Exception as e:
        console.print(f"\n[bold red]Error during generation: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--workflow", "-w", required=True, help="Workflow name to run")
@click.option("--params", "-p", default=None, help="JSON parameters for the workflow")
@click.option("--framework", "-f", default=None,
              type=click.Choice(["playwright", "selenium", "pyautogui"]),
              help="Framework of script to run")
@click.option("--timeout", "-t", default=300, help="Execution timeout in seconds")
def run(workflow: str, params: Optional[str], framework: Optional[str], timeout: int):
    """
    Execute a generated automation script.
    """
    import json
    from showonce.generate import ScriptRunner
    
    log.banner()
    log.section(f"Running: {workflow}")
    
    config = get_config()
    framework = framework or config.generate.default_framework
    
    # Find generated script
    script_path = config.paths.output_dir / f"{workflow}_{framework}.py"
    
    if not script_path.exists():
        console.print(f"[red]Error: Generated script not found: {script_path}[/red]")
        console.print(f"[dim]Run 'showonce generate -w {workflow}' first[/dim]")
        sys.exit(1)
    
    console.print(f"[cyan]Script:[/cyan] {script_path}")
    console.print(f"[cyan]Framework:[/cyan] {framework}")
    console.print(f"[cyan]Timeout:[/cyan] {timeout}s")
    
    # Parse parameters
    parsed_params = {}
    if params:
        try:
            parsed_params = json.loads(params)
            console.print(f"[cyan]Parameters:[/cyan] {parsed_params}")
        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON parameters: {e}[/red]")
            sys.exit(1)
    
    try:
        runner = ScriptRunner(script_path)
        
        # Validate script first
        is_valid, error = runner.validate_script()
        if not is_valid:
            console.print(f"[red]Script validation failed: {error}[/red]")
            sys.exit(1)
        
        # Check dependencies
        deps_ok, missing = runner.check_dependencies()
        if not deps_ok:
            console.print(f"[yellow]Warning: Missing dependencies: {missing}[/yellow]")
            console.print(f"[dim]Install with: pip install {' '.join(missing)}[/dim]")
        
        console.print()
        log.section("Execution Output")
        console.print()
        
        # Run interactively so user can see output and provide input
        exit_code = runner.run_interactive(params=parsed_params, timeout=timeout)
        
        console.print()
        if exit_code == 0:
            log.success("Script executed successfully!")
        else:
            console.print(f"[red]Script exited with code: {exit_code}[/red]")
            sys.exit(exit_code)
            
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error during execution: {e}[/bold red]")
        sys.exit(1)


@main.command(name="list")
def list_workflows():
    """
    List all recorded workflows.
    """
    log.banner()
    log.section("Workflows")
    
    config = get_config()
    workflows_dir = config.paths.workflows_dir
    
    # Find all workflow directories
    workflows = []
    for path in workflows_dir.iterdir():
        if path.is_dir() and (path / "workflow.json").exists():
            try:
                wf = Workflow.load(path)
                workflows.append({
                    "name": wf.name,
                    "steps": wf.step_count,
                    "analyzed": "✓" if wf.analyzed else "✗",
                    "created": wf.metadata.created_at.strftime("%Y-%m-%d %H:%M"),
                    "path": str(path)
                })
            except Exception as e:
                workflows.append({
                    "name": path.name,
                    "steps": "?",
                    "analyzed": "?",
                    "created": "Error",
                    "path": str(path)
                })
    
    if not workflows:
        console.print("[yellow]No workflows found[/yellow]")
        console.print(f"Create one with: showonce record --name 'my_workflow'")
        return
    
    # Create table
    table = Table(title="Recorded Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Steps", justify="center")
    table.add_column("Analyzed", justify="center")
    table.add_column("Created", style="dim")
    
    for wf in workflows:
        table.add_row(
            wf["name"],
            str(wf["steps"]),
            wf["analyzed"],
            wf["created"]
        )
    
    console.print(table)


@main.command()
@click.option("--workflow", "-w", required=True, help="Workflow name to inspect")
def info(workflow: str):
    """
    Show detailed information about a workflow.
    """
    log.banner()
    
    config = get_config()
    workflow_path = config.paths.workflows_dir / workflow
    
    if not workflow_path.exists():
        console.print(f"[red]Error: Workflow not found: {workflow}[/red]")
        sys.exit(1)
    
    wf = Workflow.load(workflow_path)
    
    log.section(f"Workflow: {wf.name}")
    
    console.print(wf.summary())
    
    console.print()
    log.key_value("Path", str(workflow_path))
    log.key_value("Framework", wf.metadata.framework)
    if wf.metadata.tags:
        log.key_value("Tags", ", ".join(wf.metadata.tags))
    if wf.metadata.notes:
        log.key_value("Notes", wf.metadata.notes)


@main.command()
def config():
    """
    Show current configuration.
    """
    log.banner()
    log.section("Configuration")
    
    cfg = get_config()
    cfg.print_status()


@main.command()
def init():
    """
    Initialize ShowOnce in current directory.
    
    Creates necessary directories and .env file.
    """
    log.banner()
    log.section("Initializing ShowOnce")
    
    config = get_config()
    
    # Create directories
    config.paths.workflows_dir.mkdir(parents=True, exist_ok=True)
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)
    
    log.success(f"Created workflows directory: {config.paths.workflows_dir}")
    log.success(f"Created output directory: {config.paths.output_dir}")
    
    # Check for .env
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        console.print()
        console.print("[yellow]Note: .env file not found[/yellow]")
        console.print("Copy .env.example to .env and add your ANTHROPIC_API_KEY")
    
    console.print()
    log.success("ShowOnce initialized successfully!")
    console.print()
    console.print("Next steps:")
    console.print("  1. Add your ANTHROPIC_API_KEY to .env")
    console.print("  2. Run: showonce record --name 'my_first_workflow'")


if __name__ == "__main__":
    main()
