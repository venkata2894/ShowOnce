"""Mouse event listener for ShowOnce."""

from pynput import mouse
from typing import Callable, Optional
import threading
from showonce.utils.logger import log

class MouseListener:
    """Listen for global mouse click events."""
    
    def __init__(self, on_click: Optional[Callable[[int, int, bool], None]] = None):
        """
        Initialize the mouse listener.
        
        Args:
            on_click: Callback when mouse is clicked. Signature: (x, y, pressed)
        """
        self.on_click_callback = on_click
        self._listener: Optional[mouse.Listener] = None
        self._running = False
        self._lock = threading.RLock()
        
        log.debug("Initializing MouseListener")

    def start(self) -> None:
        """Start listening for mouse events in background."""
        with self._lock:
            if self._running:
                log.warning("MouseListener already running")
                return
            
            self._running = True
            self._listener = mouse.Listener(
                on_click=self._on_click
            )
            self._listener.start()
            log.info("MouseListener started")

    def stop(self) -> None:
        """Stop the mouse listener."""
        with self._lock:
            if self._listener:
                self._listener.stop()
                self._listener = None
            self._running = False
            log.info("MouseListener stopped")

    def is_running(self) -> bool:
        """Check if listener is active."""
        return self._running and self._listener is not None and self._listener.is_alive()

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        """Internal handler for mouse clicks."""
        if not self._running:
            return
            
        # We only trigger on press (not release) and usually for left button
        # button.name can be 'left', 'right', 'middle'
        if pressed and self.on_click_callback:
            try:
                # We normalize the button name if possible or just pass the event
                log.debug(f"Mouse click detected at ({x}, {y}) with {button}")
                self.on_click_callback(x, y, pressed)
            except Exception as e:
                log.error(f"Error in mouse click callback: {e}")
