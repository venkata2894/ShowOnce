"""
Configuration management for ShowOnce.

Handles loading settings from environment variables and .env files.
Provides a central Config class that all modules can import.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


@dataclass
class CaptureConfig:
    """Settings for the capture module."""
    
    capture_hotkey: str = "ctrl+shift+s"
    stop_hotkey: str = "ctrl+shift+q"
    screenshot_format: str = "png"
    screenshot_quality: int = 95
    
    def __post_init__(self):
        self.capture_hotkey = os.getenv("CAPTURE_HOTKEY", self.capture_hotkey)
        self.stop_hotkey = os.getenv("STOP_HOTKEY", self.stop_hotkey)
        self.screenshot_format = os.getenv("SCREENSHOT_FORMAT", self.screenshot_format)
        self.screenshot_quality = int(os.getenv("SCREENSHOT_QUALITY", self.screenshot_quality))


@dataclass
class AnalyzeConfig:
    """Settings for the AI analysis module."""
    
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    api_key: Optional[str] = None
    
    def __post_init__(self):
        self.model = os.getenv("CLAUDE_MODEL", self.model)
        self.max_tokens = int(os.getenv("MAX_TOKENS", self.max_tokens))
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            # Don't raise error at import time, only when actually used
            pass


@dataclass
class GenerateConfig:
    """Settings for the code generation module."""
    
    default_framework: str = "playwright"
    browser_type: str = "chromium"
    headless: bool = False
    
    def __post_init__(self):
        self.default_framework = os.getenv("DEFAULT_FRAMEWORK", self.default_framework)
        self.browser_type = os.getenv("BROWSER_TYPE", self.browser_type)
        self.headless = os.getenv("HEADLESS", "false").lower() == "true"


@dataclass
class PathsConfig:
    """Settings for file paths."""
    
    workflows_dir: Path = field(default_factory=lambda: Path("./workflows"))
    output_dir: Path = field(default_factory=lambda: Path("./generated"))
    
    def __post_init__(self):
        self.workflows_dir = Path(os.getenv("WORKFLOWS_DIR", self.workflows_dir))
        self.output_dir = Path(os.getenv("OUTPUT_DIR", self.output_dir))
        
        # Create directories if they don't exist
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class LoggingConfig:
    """Settings for logging."""
    
    level: str = "INFO"
    log_file: Optional[str] = None
    
    def __post_init__(self):
        self.level = os.getenv("LOG_LEVEL", self.level).upper()
        self.log_file = os.getenv("LOG_FILE") or None


class Config:
    """
    Central configuration class for ShowOnce.
    
    Usage:
        from showonce.config import Config
        
        config = Config()
        print(config.analyze.model)  # claude-sonnet-4-20250514
        print(config.paths.workflows_dir)  # ./workflows
    """
    
    _instance: Optional["Config"] = None
    
    def __new__(cls):
        """Singleton pattern - only one Config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize all configuration sections."""
        self.capture = CaptureConfig()
        self.analyze = AnalyzeConfig()
        self.generate = GenerateConfig()
        self.paths = PathsConfig()
        self.logging = LoggingConfig()
    
    def validate(self) -> list[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.analyze.api_key:
            errors.append("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")
        
        if self.capture.screenshot_format not in ["png", "jpg"]:
            errors.append(f"Invalid screenshot format: {self.capture.screenshot_format}")
        
        if self.generate.default_framework not in ["playwright", "selenium", "pyautogui"]:
            errors.append(f"Invalid framework: {self.generate.default_framework}")
        
        if self.generate.browser_type not in ["chromium", "firefox", "webkit"]:
            errors.append(f"Invalid browser type: {self.generate.browser_type}")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0
    
    def print_status(self):
        """Print configuration status for debugging."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        table = Table(title="ShowOnce Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        
        # API Key
        api_status = "✓" if self.analyze.api_key else "✗ Missing"
        api_display = "***" + self.analyze.api_key[-4:] if self.analyze.api_key else "Not set"
        table.add_row("API Key", api_display, api_status)
        
        # Model
        table.add_row("Claude Model", self.analyze.model, "✓")
        
        # Paths
        table.add_row("Workflows Dir", str(self.paths.workflows_dir), "✓")
        table.add_row("Output Dir", str(self.paths.output_dir), "✓")
        
        # Capture
        table.add_row("Capture Hotkey", self.capture.capture_hotkey, "✓")
        table.add_row("Stop Hotkey", self.capture.stop_hotkey, "✓")
        
        # Generate
        table.add_row("Framework", self.generate.default_framework, "✓")
        table.add_row("Browser", self.generate.browser_type, "✓")
        
        console.print(table)
        
        # Print any errors
        errors = self.validate()
        if errors:
            console.print("\n[red]Configuration Errors:[/red]")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")


# Convenience function to get config
def get_config() -> Config:
    """Get the singleton Config instance."""
    return Config()


if __name__ == "__main__":
    # Test configuration
    config = get_config()
    config.print_status()
