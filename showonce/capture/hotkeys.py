"""Hotkey listener for ShowOnce."""

from pynput import keyboard
from typing import Callable, Dict, Set, Optional, Tuple, Union, List
import threading
from showonce.utils.logger import log

class HotkeyListener:
    """Listen for global hotkey combinations."""
    
    def __init__(self):
        """Initialize the hotkey listener."""
        # Map hotkey string to the pynput HotKey object
        self._hotkey_handlers: Dict[str, keyboard.HotKey] = {}
        
        self._listener: Optional[keyboard.Listener] = None
        self._running = False
        self._lock = threading.RLock()
        
        log.debug("Initializing HotkeyListener")

    def parse_hotkey(self, hotkey_str: str) -> List[Union[keyboard.Key, keyboard.KeyCode]]:
        """
        Parse hotkey string like 'ctrl+shift+s' into components.
        
        Returns:
            List of keys that make up the hotkey.
        """
        # Normalize modifiers to pynput format (<ctrl>, <shift>, etc.)
        # We assume the user creates strings like "ctrl+shift+s"
        # We need to turn them into "<ctrl>+<shift>+s" ONLY for the modifiers.
        
        parts = hotkey_str.split('+')
        normalized_parts = []
        
        modifiers = {'ctrl', 'shift', 'alt', 'cmd', 'win'}
        
        for part in parts:
            p = part.strip().lower()
            if p in modifiers:
                normalized_parts.append(f"<{p}>")
            elif len(p) > 1 and not p.startswith('<'):
                # Handle special keys like 'enter', 'esc' -> <enter>, <esc> if not already wrapped
                # But don't double wrap
                try:
                    # Check if it's a known key in pynput
                    if hasattr(keyboard.Key, p):
                        normalized_parts.append(f"<{p}>")
                    else:
                        normalized_parts.append(p)
                except:
                    normalized_parts.append(p)
            else:
                normalized_parts.append(p)
                
        fixed_hotkey = '+'.join(normalized_parts)
        log.debug(f"Normalized hotkey '{hotkey_str}' to '{fixed_hotkey}'")
        
        return keyboard.HotKey.parse(fixed_hotkey)

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """
        Register a hotkey with its callback.
        
        Args:
            hotkey: String representation (e.g., "<ctrl>+<shift>+s")
            callback: Function to call when hotkey is triggered.
        """
        with self._lock:
            # We normalize logic by using pynput's HotKey class
            # which handles the state machine for us.
            
            normalized_str = hotkey.lower()
            
            # Wrap callback to run in thread to avoid blocking listener
            def safe_callback():
                try:
                    log.debug(f"Hotkey triggered: {hotkey}")
                    callback()
                except Exception as e:
                    log.error(f"Error in hotkey callback for {hotkey}: {e}")

            try:
                keys = self.parse_hotkey(hotkey)
                handler = keyboard.HotKey(keys, safe_callback)
                self._hotkey_handlers[normalized_str] = handler
                log.info(f"Registered hotkey: {hotkey}")
            except Exception as e:
                log.error(f"Failed to register hotkey '{hotkey}': {e}")
                raise ValueError(f"Invalid hotkey: {hotkey}")

    def unregister(self, hotkey: str) -> None:
        """Unregister a hotkey."""
        with self._lock:
            normalized = hotkey.lower()
            if normalized in self._hotkey_handlers:
                del self._hotkey_handlers[normalized]
                log.info(f"Unregistered hotkey: {hotkey}")

    def start(self) -> None:
        """Start listening for hotkeys in background."""
        with self._lock:
            if self._running:
                log.warning("HotkeyListener already running")
                return
            
            self._running = True
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self._listener.start()
            log.info("HotkeyListener started")

    def stop(self) -> None:
        """Stop the hotkey listener."""
        with self._lock:
            if self._listener:
                self._listener.stop()
                self._listener = None
            self._running = False
            log.info("HotkeyListener stopped")

    def is_running(self) -> bool:
        """Check if listener is active."""
        return self._running and self._listener is not None and self._listener.is_alive()

    def _canonicalize(self, key):
        """Convert specific keys to generic ones for matching."""
        if hasattr(key, 'value'):
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                return keyboard.Key.ctrl
            if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                return keyboard.Key.shift
            if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                return keyboard.Key.alt
            if key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                return keyboard.Key.cmd
        return key

    def _on_press(self, key):
        """Internal handler for key press."""
        if not self._running:
            return
            
        canonical_key = self._canonicalize(key)
        
        # Forward to all handlers
        for handler in list(self._hotkey_handlers.values()):
            handler.press(canonical_key)

    def _on_release(self, key):
        """Internal handler for key release."""
        if not self._running:
            return
            
        canonical_key = self._canonicalize(key)
        
        for handler in list(self._hotkey_handlers.values()):
            handler.release(canonical_key)
