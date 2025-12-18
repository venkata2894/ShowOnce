"""
Workflow data models.

Defines the structure for recorded workflows and their steps.
"""

import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field


class StepMetadata(BaseModel):
    """Metadata captured with each screenshot step."""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    active_window: Optional[str] = None
    window_title: Optional[str] = None
    mouse_position: Optional[tuple[int, int]] = None
    screen_resolution: Optional[tuple[int, int]] = None
    url: Optional[str] = None  # For browser-based workflows
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowStep(BaseModel):
    """
    A single step in a workflow recording.
    
    Each step captures:
    - A screenshot of the current state
    - User's description of what they're doing
    - Metadata about the capture context
    """
    
    step_number: int = Field(ge=1, description="Step sequence number")
    description: str = Field(description="User's description of the action")
    screenshot_path: Optional[str] = Field(default=None, description="Path to screenshot file")
    screenshot_base64: Optional[str] = Field(default=None, description="Base64 encoded screenshot")
    metadata: StepMetadata = Field(default_factory=StepMetadata)
    
    def has_screenshot(self) -> bool:
        """Check if this step has a screenshot."""
        return bool(self.screenshot_path or self.screenshot_base64)
    
    def load_screenshot_bytes(self) -> Optional[bytes]:
        """Load screenshot as bytes from file or base64."""
        if self.screenshot_base64:
            return base64.b64decode(self.screenshot_base64)
        elif self.screenshot_path:
            path = Path(self.screenshot_path)
            if path.exists():
                return path.read_bytes()
        return None
    
    def save_screenshot(self, directory: Path, image_bytes: bytes, format: str = "png"):
        """Save screenshot to file and update path."""
        filename = f"step_{self.step_number:03d}.{format}"
        filepath = directory / filename
        filepath.write_bytes(image_bytes)
        self.screenshot_path = str(filepath)
        # Clear base64 to save memory
        self.screenshot_base64 = None


class WorkflowMetadata(BaseModel):
    """Metadata for the entire workflow."""
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    framework: str = Field(default="playwright")
    platform: Optional[str] = None  # web, desktop, mobile
    application: Optional[str] = None  # e.g., "Chrome", "Excel"
    notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Workflow(BaseModel):
    """
    A complete workflow recording.
    
    A workflow consists of multiple steps, each capturing a screenshot
    and user description. The workflow can be saved/loaded from disk
    and used for analysis and code generation.
    
    Usage:
        # Create new workflow
        workflow = Workflow(name="login_demo")
        
        # Add steps
        workflow.add_step(
            description="Enter username",
            screenshot_bytes=image_bytes
        )
        
        # Save to disk
        workflow.save("./workflows/login_demo")
        
        # Load from disk
        loaded = Workflow.load("./workflows/login_demo")
    """
    
    name: str = Field(description="Workflow identifier name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    steps: List[WorkflowStep] = Field(default_factory=list)
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    
    # Analysis results (populated after AI analysis)
    analyzed: bool = Field(default=False)
    analysis_results: Optional[Dict[str, Any]] = None
    
    def add_step(
        self,
        description: str,
        screenshot_bytes: Optional[bytes] = None,
        screenshot_base64: Optional[str] = None,
        **metadata_kwargs
    ) -> WorkflowStep:
        """
        Add a new step to the workflow.
        
        Args:
            description: User's description of the action
            screenshot_bytes: Raw screenshot bytes
            screenshot_base64: Base64 encoded screenshot
            **metadata_kwargs: Additional metadata fields
            
        Returns:
            The created WorkflowStep
        """
        step_number = len(self.steps) + 1
        
        # Convert bytes to base64 if provided
        if screenshot_bytes and not screenshot_base64:
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        step = WorkflowStep(
            step_number=step_number,
            description=description,
            screenshot_base64=screenshot_base64,
            metadata=StepMetadata(**metadata_kwargs)
        )
        
        self.steps.append(step)
        self.metadata.updated_at = datetime.now()
        
        return step
    
    def get_step(self, step_number: int) -> Optional[WorkflowStep]:
        """Get a step by its number (1-indexed)."""
        if 1 <= step_number <= len(self.steps):
            return self.steps[step_number - 1]
        return None
    
    def remove_step(self, step_number: int) -> bool:
        """Remove a step by its number and renumber remaining steps."""
        if 1 <= step_number <= len(self.steps):
            self.steps.pop(step_number - 1)
            # Renumber remaining steps
            for i, step in enumerate(self.steps):
                step.step_number = i + 1
            self.metadata.updated_at = datetime.now()
            return True
        return False
    
    @property
    def step_count(self) -> int:
        """Get the number of steps in this workflow."""
        return len(self.steps)
    
    @property
    def transition_count(self) -> int:
        """Get the number of transitions (steps - 1)."""
        return max(0, len(self.steps) - 1)
    
    def save(self, directory: str | Path, save_screenshots: bool = True) -> Path:
        """
        Save workflow to a directory.
        
        Creates:
        - workflow.json: Workflow data
        - screenshots/: Directory with screenshot files
        
        Args:
            directory: Directory to save to
            save_screenshots: Whether to save screenshots as files
            
        Returns:
            Path to the saved workflow directory
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        # Save screenshots to files if requested
        if save_screenshots:
            screenshots_dir = directory / "screenshots"
            screenshots_dir.mkdir(exist_ok=True)
            
            for step in self.steps:
                if step.screenshot_base64:
                    image_bytes = base64.b64decode(step.screenshot_base64)
                    step.save_screenshot(screenshots_dir, image_bytes)
        
        # Save workflow JSON
        workflow_file = directory / "workflow.json"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            json.dump(self.model_dump(mode='json'), f, indent=2, default=str)
        
        return directory
    
    @classmethod
    def load(cls, directory: str | Path) -> "Workflow":
        """
        Load a workflow from a directory.
        
        Args:
            directory: Directory containing workflow.json
            
        Returns:
            Loaded Workflow instance
        """
        directory = Path(directory)
        workflow_file = directory / "workflow.json"
        
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_file}")
        
        with open(workflow_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls.model_validate(data)
    
    def get_screenshot_pairs(self) -> List[tuple[WorkflowStep, WorkflowStep]]:
        """
        Get pairs of consecutive steps for transition analysis.
        
        Returns:
            List of (before, after) step tuples
        """
        pairs = []
        for i in range(len(self.steps) - 1):
            pairs.append((self.steps[i], self.steps[i + 1]))
        return pairs
    
    def summary(self) -> str:
        """Get a text summary of the workflow."""
        lines = [
            f"Workflow: {self.name}",
            f"Description: {self.description or 'No description'}",
            f"Steps: {self.step_count}",
            f"Created: {self.metadata.created_at}",
            f"Analyzed: {'Yes' if self.analyzed else 'No'}",
            "",
            "Steps:",
        ]
        
        for step in self.steps:
            has_img = "📸" if step.has_screenshot() else "  "
            lines.append(f"  {step.step_number}. {has_img} {step.description}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        return f"Workflow(name='{self.name}', steps={self.step_count})"
    
    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    # Example usage
    workflow = Workflow(
        name="example_login",
        description="Example login workflow for testing"
    )
    
    # Add some test steps
    workflow.add_step(description="Open browser to login page")
    workflow.add_step(description="Enter username in the username field")
    workflow.add_step(description="Enter password in the password field")
    workflow.add_step(description="Click the login button")
    workflow.add_step(description="Verify dashboard is displayed")
    
    print(workflow.summary())
