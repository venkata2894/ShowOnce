"""
Logging configuration for ShowOnce.

Provides consistent, beautiful logging using Rich library.
"""

import logging
import sys
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Custom theme for ShowOnce
SHOWONCE_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green",
    "step": "magenta",
})

# Shared console instance
console = Console(theme=SHOWONCE_THEME)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    show_path: bool = False
) -> logging.Logger:
    """
    Set up logging for ShowOnce.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path to write logs to
        show_path: Whether to show file paths in log output
        
    Returns:
        Configured logger instance
    """
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create handlers
    handlers = []
    
    # Rich console handler (pretty output)
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=show_path,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True,
    )
    rich_handler.setLevel(log_level)
    handlers.append(rich_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Get ShowOnce logger
    logger = logging.getLogger("showonce")
    logger.setLevel(log_level)
    
    return logger


def get_logger(name: str = "showonce") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (will be prefixed with 'showonce.')
        
    Returns:
        Logger instance
    """
    if not name.startswith("showonce"):
        name = f"showonce.{name}"
    return logging.getLogger(name)


class ShowOnceLogger:
    """
    Custom logger with ShowOnce-specific methods.
    
    Provides convenient methods for common logging patterns
    used throughout the application.
    """
    
    def __init__(self, name: str = "showonce"):
        self.logger = get_logger(name)
        self.console = console
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)
    
    def success(self, message: str):
        """Log success message (shows as info with green styling)."""
        self.console.print(f"[success]✓ {message}[/success]")
    
    def step(self, step_num: int, message: str):
        """Log a workflow step."""
        self.console.print(f"[step]Step {step_num}:[/step] {message}")
    
    def capture(self, step_num: int, description: str):
        """Log a screenshot capture."""
        self.console.print(f"[cyan]📸 Captured[/cyan] Step {step_num}: {description}")
    
    def action(self, action_type: str, target: str):
        """Log an inferred action."""
        self.console.print(f"[magenta]→[/magenta] {action_type}: {target}")
    
    def progress(self, current: int, total: int, message: str = ""):
        """Log progress."""
        percent = (current / total) * 100 if total > 0 else 0
        bar_length = 20
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        self.console.print(f"[cyan]{bar}[/cyan] {percent:.0f}% {message}")
    
    def section(self, title: str):
        """Print a section header."""
        self.console.print()
        self.console.rule(f"[bold cyan]{title}[/bold cyan]")
        self.console.print()
    
    def key_value(self, key: str, value: str):
        """Print a key-value pair."""
        self.console.print(f"  [cyan]{key}:[/cyan] {value}")
    
    def banner(self):
        """Print ShowOnce banner."""
        banner_text = """
[bold cyan]
  ███████╗██╗  ██╗ ██████╗ ██╗    ██╗ ██████╗ ███╗   ██╗ ██████╗███████╗
  ██╔════╝██║  ██║██╔═══██╗██║    ██║██╔═══██╗████╗  ██║██╔════╝██╔════╝
  ███████╗███████║██║   ██║██║ █╗ ██║██║   ██║██╔██╗ ██║██║     █████╗  
  ╚════██║██╔══██║██║   ██║██║███╗██║██║   ██║██║╚██╗██║██║     ██╔══╝  
  ███████║██║  ██║╚██████╔╝╚███╔███╔╝╚██████╔╝██║ ╚████║╚██████╗███████╗
  ╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚══════╝
[/bold cyan]
[dim]Show me once. I'll do it forever.[/dim]
        """
        self.console.print(banner_text)


# Default logger instance
log = ShowOnceLogger()


if __name__ == "__main__":
    # Test logging
    setup_logging(level="DEBUG")
    
    log.banner()
    log.section("Testing Logger")
    
    log.info("This is an info message")
    log.debug("This is a debug message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.success("This is a success message")
    
    log.section("Workflow Simulation")
    
    log.capture(1, "Open login page")
    log.capture(2, "Enter username")
    log.capture(3, "Click submit")
    
    log.section("Action Inference")
    
    log.action("click", "Login button")
    log.action("type", "Username field")
    
    log.section("Progress Demo")
    
    for i in range(1, 6):
        log.progress(i, 5, f"Processing step {i}")
