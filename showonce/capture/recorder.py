"""Recording session manager for ShowOnce."""

import time
import threading
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

from showonce.models.workflow import Workflow, WorkflowStep
from showonce.config import get_config
from showonce.capture.screenshot import ScreenCapture
from showonce.capture.hotkeys import HotkeyListener
from showonce.capture.metadata import MetadataCollector
from showonce.utils.logger import log

class RecordingSession:
    """Manage a workflow recording session."""
    
    def __init__(self, workflow_name: str, description: Optional[str] = None, no_prompt: bool = False):
        """
        Initialize recording session.
        
        Args:
            workflow_name: Name of the workflow
            description: Optional description
            no_prompt: If True, don't prompt for descriptions (uses default)
        """
        self.config = get_config()
        self.workflow = Workflow(name=workflow_name, description=description)
        self.no_prompt = no_prompt
        
        # Components
        self.screen_capture = ScreenCapture()
        self.hotkey_listener = HotkeyListener()
        self.metadata_collector = MetadataCollector()
        self.console = Console()
        
        # State
        self.is_recording = False
        self._stop_event = threading.Event()
        
        log.debug(f"Initialized RecordingSession for '{workflow_name}'")
    
    def start(self) -> Workflow:
        """
        Start the recording session.
        
        Listens for hotkeys and captures screenshots until stopped.
        Returns the completed Workflow.
        """
        self.console.clear()
        self.console.print(Panel.fit(
            f"[bold cyan]ShowOnce Recording: {self.workflow.name}[/bold cyan]\n\n"
            f"Capture Hotkey: [green]{self.config.capture.capture_hotkey}[/green]\n"
            f"Stop Hotkey:    [red]{self.config.capture.stop_hotkey}[/red]",
            title="Recording Session"
        ))
        
        self.is_recording = True
        self._stop_event.clear()
        
        # Register hotkeys
        self.hotkey_listener.register(self.config.capture.capture_hotkey, self._on_capture_hotkey)
        self.hotkey_listener.register(self.config.capture.stop_hotkey, self._on_stop_hotkey)
        
        self.hotkey_listener.start()
        
        # Wait until stopped
        try:
            while not self._stop_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()
            
        return self.workflow
    
    def capture_step(self) -> None:
        """Capture a single step (called on hotkey press)."""
        # 1. Capture Screenshot immediately
        log.info("Capturing step...")
        try:
            # We assume full screen for now, or primary monitor
            image = self.screen_capture.capture_full_screen()
            image_bytes = self.screen_capture.image_to_bytes(image, format=self.config.capture.screenshot_format)
            
            # 2. Collect Metadata
            meta = self.metadata_collector.collect()
            
            # 3. Prompt for Description
            # We pause hotkey listener to avoid accidental triggers while typing
            # (Though our listener is async, the console prompt blocks this thread if called directly.
            # But this method is called from a thread usually. We need to handle UI carefully.)
            
            # Since this is called from the HotkeyListener thread, we shouldn't block it too long 
            # OR we should coordinate with the main thread.
            # However, prompt is interactive.
            # Best practice: Signal main thread to prompt? 
            # Or just prompt here (Rich Prompt is blocking on stdin).
            
            # Important: If we block the hotkey listener thread, keys won't process?
            # HotkeyListener runs callbacks in separate threads? 
            # My logic in HotkeyListener implementation: "threading.Thread(target=callback, daemon=True).start()"
            # So yes, we are in a NEW thread. We can block safely without stopping the listener loop.
            # BUT we might face stdin contention if multiple threads try to read.
            # We should probably lock around prompting.
            
            if self.no_prompt:
                description = f"Captured at {meta.timestamp.strftime('%H:%M:%S')}"
            else:
                description = self._prompt_description()
            
            # 4. Create Step
            step = self.workflow.add_step(
                description=description,
                screenshot_bytes=image_bytes,
                timestamp=meta.timestamp,
                active_window=meta.active_window,
                window_title=meta.window_title,
                mouse_position=meta.mouse_position,
                screen_resolution=meta.screen_resolution,
                platform=meta.platform
            )
            
            self._display_status()
            
        except Exception as e:
            log.error(f"Failed to capture step: {e}")
            self.console.print(f"[bold red]Error capturing step: {e}[/bold red]")
    
    def stop(self) -> None:
        """Stop the recording session."""
        if not self.is_recording:
            return
            
        log.info("Stopping recording session...")
        self.is_recording = False
        
        self.hotkey_listener.stop()
        self._stop_event.set()
        
        self.console.print("\n[bold yellow]Recording stopped.[/bold yellow]")
        self.console.print(f"Captured {self.workflow.step_count} steps.")
        
        if self.workflow.step_count > 0:
            self.save()
        else:
            self.console.print("[dim]No steps captured, skipping save.[/dim]")
    
    def save(self) -> Path:
        """Save the workflow to disk."""
        directory = self.config.paths.workflows_dir / self.workflow.name
        
        self.console.print(f"Saving to [cyan]{directory}[/cyan]...")
        try:
            path = self.workflow.save(directory)
            self.console.print("[bold green]Workflow saved successfully![/bold green]")
            return path
        except Exception as e:
            log.error(f"Failed to save workflow: {e}")
            self.console.print(f"[bold red]Error saving workflow: {e}[/bold red]")
            raise
    
    def _on_capture_hotkey(self) -> None:
        """Callback for capture hotkey."""
        if self.is_recording:
            self.capture_step()
    
    def _on_stop_hotkey(self) -> None:
        """Callback for stop hotkey."""
        self.stop()
    
    def _prompt_description(self) -> str:
        """Prompt user for step description."""
        # Use a plain print first to grab attention
        print("\n\a") # Bell sound
        self.console.print(f"[bold green]📸 Step {self.workflow.step_count + 1} Captured![/bold green]")
        
        # Prompt
        description = Prompt.ask("What did you just do?", console=self.console)
        return description
    
    def _display_status(self) -> None:
        """Display current recording status."""
        self.console.print(f"[dim]Total steps: {self.workflow.step_count}[/dim]")
        self.console.print("[dim]Press Hotkey to capture next step...[/dim]\n")


def record_workflow(name: str, description: Optional[str] = None) -> Workflow:
    """
    Convenience function to record a workflow.
    
    Usage:
        workflow = record_workflow("login_demo")
    """
    session = RecordingSession(name, description)
    return session.start()
