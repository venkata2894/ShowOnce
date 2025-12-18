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
    
    # TODO: Stage 3 - Implement actual analysis logic
    console.print()
    console.print("[dim]Analysis functionality will be implemented in Stage 3[/dim]")


@main.command()
@click.option("--workflow", "-w", required=True, help="Workflow name to generate code for")
@click.option("--framework", "-f", default=None, 
              type=click.Choice(["playwright", "selenium", "pyautogui"]),
              help="Automation framework to use")
@click.option("--output", "-o", default=None, help="Output file path")
def generate(workflow: str, framework: Optional[str], output: Optional[str]):
    """
    Generate automation script from analyzed workflow.
    """
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
    
    if not wf.analyzed:
        console.print("[yellow]Warning: Workflow has not been analyzed yet[/yellow]")
        console.print("Run 'showonce analyze' first for best results")
    
    console.print(f"[cyan]Framework:[/cyan] {framework}")
    
    # TODO: Stage 4 - Implement actual generation logic
    console.print()
    console.print("[dim]Generation functionality will be implemented in Stage 4[/dim]")


@main.command()
@click.option("--workflow", "-w", required=True, help="Workflow name to run")
@click.option("--params", "-p", default=None, help="JSON parameters for the workflow")
@click.option("--headless", is_flag=True, help="Run browser in headless mode")
def run(workflow: str, params: Optional[str], headless: bool):
    """
    Execute a generated automation script.
    """
    log.banner()
    log.section(f"Running: {workflow}")
    
    config = get_config()
    
    # Load workflow
    workflow_path = config.paths.workflows_dir / workflow
    if not workflow_path.exists():
        console.print(f"[red]Error: Workflow not found: {workflow}[/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Headless:[/cyan] {headless}")
    if params:
        console.print(f"[cyan]Parameters:[/cyan] {params}")
    
    # TODO: Stage 4 - Implement actual run logic
    console.print()
    console.print("[dim]Run functionality will be implemented in Stage 4[/dim]")


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
