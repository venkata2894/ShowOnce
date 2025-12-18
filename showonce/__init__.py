"""
ShowOnce - AI-powered workflow automation from screenshots.

Show me once. I'll do it forever.

This package provides tools to:
- Record workflows through screenshots and descriptions
- Analyze screenshots using Claude AI to infer actions
- Generate executable automation scripts
- Run automations with custom parameters
"""

__version__ = "0.1.0"
__author__ = "Venkata Sai"
__description__ = "AI-powered tool that learns automation workflows from screenshots"

# Package-level imports for convenience
from showonce.models.workflow import Workflow, WorkflowStep
from showonce.models.actions import Action, ActionType, ElementTarget
from showonce.config import Config

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__description__",
    # Models
    "Workflow",
    "WorkflowStep",
    "Action",
    "ActionType",
    "ElementTarget",
    # Config
    "Config",
]
