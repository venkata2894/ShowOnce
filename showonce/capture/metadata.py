"""Metadata collection for ShowOnce."""

import platform
import sys
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from showonce.utils.logger import log

# Import dependencies with graceful fallbacks
try:
    import pyautogui
except ImportError:
    log.warning("pyautogui not available. Mouse tracking and resolution will be limited.")
    pyautogui = None

try:
    import pygetwindow as gw
except ImportError:
    log.warning("pygetwindow not available. Window tracking will be limited.")
    gw = None

@dataclass
class CaptureMetadata:
    """Metadata captured with each screenshot."""
    timestamp: datetime
    active_window: Optional[str]
    window_title: Optional[str]
    application_name: Optional[str]
    mouse_position: Optional[Tuple[int, int]]
    screen_resolution: Optional[Tuple[int, int]]
    platform: str
    url: Optional[str] = None

class MetadataCollector:
    """Collect system metadata at capture time."""
    
    def __init__(self):
        """Initialize metadata collector."""
        self.platform = platform.system()
        log.debug(f"Initializing MetadataCollector on {self.platform}")
        
    def collect(self) -> CaptureMetadata:
        """Collect all available metadata."""
        start_time = time.time()
        
        metadata = CaptureMetadata(
            timestamp=datetime.now(),
            active_window=None, # Usually same as title for simple cases
            window_title=self.get_active_window(),
            application_name=self.get_application_name(),
            mouse_position=self.get_mouse_position(),
            screen_resolution=self.get_screen_resolution(),
            platform=self.platform,
            url=None # Requires browser integration
        )
        
        # Heuristic for active window vs title
        # In this simple implementation, we assume active_window ID or handle is not strictly required yet,
        # but the prompt asked for separate fields.
        # "Active window title" -> window_title
        # "Active application name" -> application_name
        metadata.active_window = metadata.window_title # Duplicate for now unless we have a handle
        
        duration = (time.time() - start_time) * 1000
        if duration > 100:
            log.warning(f"Metadata collection took {duration:.2f}ms")
            
        return metadata
    
    def get_active_window(self) -> Optional[str]:
        """Get the currently active window title."""
        if not gw:
            return None
            
        try:
            if self.platform == "Windows":
                # pygetwindow works well on Windows
                window = gw.getActiveWindow()
                if window:
                    return window.title
            elif self.platform == "Darwin": # macOS
                 # pygetwindow on mac might be limited or require permissions.
                 # Fallback to AppKit or osascript if needed, but pygetwindow tries its best.
                 # Standard pygetwindow might generic active window using NSWorkspace if installed.
                 # If gw fails/returns None, we could try AppleScript.
                 try:
                    window = gw.getActiveWindow()
                    if window:
                        return window.title
                 except:
                    # Fallback to AppleScript for macOS title
                    import subprocess
                    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
                    try:
                        res = subprocess.check_output(["osascript", "-e", script]).decode().strip()
                        return res
                    except:
                        pass
            elif self.platform == "Linux":
                # pygetwindow on Linux uses xdotool/xprop usually
                try:
                    window = gw.getActiveWindow()
                    if window:
                        return window.title
                except:
                    pass
        except Exception as e:
            log.error(f"Error getting active window: {e}")
        return None
    
    def get_application_name(self) -> Optional[str]:
        """Get the active application name."""
        # This is often inferred from window title or system APIs.
        # On Windows, pygetwindow doesn't easily give process name without handle walking.
        # We can implement a heuristic or use psutil if we had the PID (gw doesn't give PID by default).
        
        title = self.get_active_window()
        if not title:
            return None
            
        # Simple heuristic: last part of title?
        # Browsers: "Title - Google Chrome"
        # VS Code: "file.py - Visual Studio Code"
        if " - " in title:
            return title.split(" - ")[-1]
        
        return None # Hard to get accurate app name without PID
    
    def get_mouse_position(self) -> Optional[Tuple[int, int]]:
        """Get current mouse cursor position."""
        if pyautogui:
            try:
                # pyautogui.position() returns Point(x, y)
                x, y = pyautogui.position()
                return (x, y)
            except Exception as e:
                # Can fail active corner protection or similar
                log.debug(f"Failed to get mouse position: {e}")
        return None
    
    def get_screen_resolution(self) -> Tuple[int, int]:
        """Get primary screen resolution."""
        if pyautogui:
            try:
                 width, height = pyautogui.size()
                 return (width, height)
            except Exception:
                pass
        return None
    
    def to_dict(self, metadata: CaptureMetadata) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        d = asdict(metadata)
        # Convert timestamp to ISO string
        d['timestamp'] = d['timestamp'].isoformat()
        return d
