"""PyAutoGUI code generator for ShowOnce."""

from typing import List, Optional
from pathlib import Path
from datetime import datetime
import re

from showonce.models.actions import ActionSequence, Action, ActionType
from showonce.config import get_config
from showonce.utils.logger import log


class PyAutoGUIGenerator:
    """Generate PyAutoGUI automation scripts from ActionSequence."""
    
    def __init__(self, failsafe: bool = True, pause: float = 0.5):
        """
        Initialize generator with settings.
        
        Args:
            failsafe: Enable PyAutoGUI failsafe (move mouse to corner to abort)
            pause: Default pause between actions
        """
        self.failsafe = failsafe
        self.pause = pause
        self.config = get_config()
        self.indent = "    "  # 4 spaces
        
        log.debug(f"PyAutoGUIGenerator initialized (failsafe={failsafe}, pause={pause})")
    
    def generate(self, action_sequence: ActionSequence) -> str:
        """
        Generate complete PyAutoGUI script.
        
        Args:
            action_sequence: ActionSequence with actions to convert
            
        Returns:
            Complete Python script as string
        """
        lines = []
        
        # Header with imports and function definition
        lines.append(self._generate_header(action_sequence))
        
        # Generate each action
        for action in action_sequence.actions:
            action_lines = self.generate_action(action)
            for line in action_lines:
                lines.append(f"{self.indent}{line}")
            lines.append("")  # Blank line between actions
        
        # Footer with main block
        lines.append(self._generate_footer(action_sequence))
        
        return "\n".join(lines)
    
    def generate_action(self, action: Action) -> List[str]:
        """Generate code lines for a single action."""
        handlers = {
            ActionType.CLICK: self._generate_click,
            ActionType.DOUBLE_CLICK: self._generate_double_click,
            ActionType.RIGHT_CLICK: self._generate_right_click,
            ActionType.TYPE: self._generate_type,
            ActionType.NAVIGATE: self._generate_navigate,
            ActionType.WAIT: self._generate_wait,
            ActionType.SCROLL_DOWN: self._generate_scroll,
            ActionType.SCROLL_UP: self._generate_scroll,
            ActionType.PRESS_KEY: self._generate_press_key,
            ActionType.HOTKEY: self._generate_hotkey,
            ActionType.HOVER: self._generate_hover,
            ActionType.DRAG: self._generate_drag,
        }
        
        handler = handlers.get(action.action_type, self._generate_unknown)
        
        # Add comment with step description
        lines = [f"# Step {action.sequence}: {action.to_description()}"]
        lines.extend(handler(action))
        
        return lines
    
    def _generate_click(self, action: Action) -> List[str]:
        """Generate click action code."""
        coords = self._get_coordinates(action)
        if coords:
            return [f"pyautogui.click({coords})"]
        
        # Try image-based location
        return self._generate_image_click(action)
    
    def _generate_double_click(self, action: Action) -> List[str]:
        """Generate double click action code."""
        coords = self._get_coordinates(action)
        if coords:
            return [f"pyautogui.doubleClick({coords})"]
        return self._generate_image_click(action, clicks=2)
    
    def _generate_right_click(self, action: Action) -> List[str]:
        """Generate right click action code."""
        coords = self._get_coordinates(action)
        if coords:
            return [f"pyautogui.rightClick({coords})"]
        return self._generate_image_click(action, button='right')
    
    def _generate_image_click(self, action: Action, clicks: int = 1, button: str = 'left') -> List[str]:
        """Generate image-based click with fallback."""
        desc = action.target.description if action.target else "element"
        safe_desc = re.sub(r'[^a-zA-Z0-9]', '_', desc.lower())[:20]
        
        return [
            f"# Image-based click for: {desc}",
            f"# Save a screenshot of the target element as '{safe_desc}.png'",
            f"location = pyautogui.locateOnScreen('{safe_desc}.png', confidence=0.8)",
            "if location:",
            f"    pyautogui.click(pyautogui.center(location), clicks={clicks}, button='{button}')",
            "else:",
            f"    print('Warning: Could not find {desc} on screen')",
            f"    # Fallback: manual coordinates may be needed"
        ]
    
    def _generate_type(self, action: Action) -> List[str]:
        """Generate type action code."""
        if action.is_variable and action.variable_name:
            value = action.variable_name
        else:
            value = f'"{self._escape_string(action.value or "")}"'
        
        lines = []
        
        # Click on field first if we have coordinates
        coords = self._get_coordinates(action)
        if coords:
            lines.append(f"pyautogui.click({coords})  # Focus the field")
        
        lines.append(f"pyautogui.typewrite({value}, interval=0.05)")
        
        return lines
    
    def _generate_navigate(self, action: Action) -> List[str]:
        """Generate navigation action code (open URL in browser)."""
        url = action.url or ""
        return [
            "import webbrowser",
            f'webbrowser.open("{url}")',
            "time.sleep(3)  # Wait for browser to load"
        ]
    
    def _generate_wait(self, action: Action) -> List[str]:
        """Generate wait action code."""
        return ["time.sleep(2)"]
    
    def _generate_scroll(self, action: Action) -> List[str]:
        """Generate scroll action code."""
        amount = action.scroll_amount or 3
        
        if action.action_type == ActionType.SCROLL_UP:
            amount = abs(amount)
        else:
            amount = -abs(amount)
        
        return [f"pyautogui.scroll({amount})"]
    
    def _generate_press_key(self, action: Action) -> List[str]:
        """Generate key press action code."""
        key = (action.key or "enter").lower()
        return [f"pyautogui.press('{key}')"]
    
    def _generate_hotkey(self, action: Action) -> List[str]:
        """Generate hotkey/keyboard shortcut action code."""
        modifiers = action.modifiers or []
        key = action.key or ""
        
        all_keys = [m.lower() for m in modifiers] + [key.lower()]
        keys_str = ", ".join([f"'{k}'" for k in all_keys])
        
        return [f"pyautogui.hotkey({keys_str})"]
    
    def _generate_hover(self, action: Action) -> List[str]:
        """Generate hover action code."""
        coords = self._get_coordinates(action)
        if coords:
            return [f"pyautogui.moveTo({coords})"]
        return ["# TODO: Hover needs coordinates"]
    
    def _generate_drag(self, action: Action) -> List[str]:
        """Generate drag action code."""
        if action.drag_start and action.drag_end:
            sx, sy = action.drag_start
            ex, ey = action.drag_end
            return [
                f"pyautogui.moveTo({sx}, {sy})",
                f"pyautogui.drag({ex - sx}, {ey - sy}, duration=0.5)"
            ]
        return ["# TODO: Drag action needs start and end coordinates"]
    
    def _generate_unknown(self, action: Action) -> List[str]:
        """Generate placeholder for unknown action types."""
        return [f"# TODO: {action.action_type} not supported in PyAutoGUI"]
    
    def _get_coordinates(self, action: Action) -> Optional[str]:
        """Get coordinates from action target if available."""
        if action.target and action.target.coordinates:
            x, y = action.target.coordinates
            return f"{x}, {y}"
        return None
    
    def _escape_string(self, s: str) -> str:
        """Escape special characters in strings."""
        if s is None:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    
    def _generate_header(self, action_sequence: ActionSequence) -> str:
        """Generate script header with imports and function definition."""
        func_name = self._to_function_name(action_sequence.workflow_name)
        
        # Build parameters from variables
        params = []
        param_docs = []
        
        for param in action_sequence.parameters:
            name = param.get("name", "param")
            params.append(f"{name}: str")
            param_docs.append(f"        {name}: Value for {param.get('description', 'parameter')}")
        
        params_str = ", ".join(params) if params else ""
        param_docs_str = "\n".join(param_docs) if param_docs else "        None"
        
        header = f'''# Auto-generated by ShowOnce
# Workflow: {action_sequence.workflow_name}
# Generated: {datetime.now().isoformat()}
# Actions: {len(action_sequence.actions)}
# Framework: PyAutoGUI (Desktop Automation)

import time
import pyautogui

# Safety settings
pyautogui.FAILSAFE = {self.failsafe}  # Move mouse to corner to abort
pyautogui.PAUSE = {self.pause}  # Pause between actions


def {func_name}({params_str}):
    """
    Automated workflow: {action_sequence.workflow_name}
    
    Note: This script uses screen coordinates and image matching.
    Ensure your screen resolution and window positions match recording.
    
    Parameters:
{param_docs_str}
    """
    print("Starting automation in 3 seconds...")
    print("Move mouse to top-left corner to abort (FAILSAFE)")
    time.sleep(3)
    
'''
        return header
    
    def _generate_footer(self, action_sequence: ActionSequence) -> str:
        """Generate script footer with main block."""
        func_name = self._to_function_name(action_sequence.workflow_name)
        
        param_input = ""
        example_str = ""
        
        if action_sequence.parameters:
            param_input = "\n".join([
                f'    {p.get("name")} = input("Enter {p.get("name")}: ")'
                for p in action_sequence.parameters
            ])
            example_str = ", ".join([p.get("name") for p in action_sequence.parameters])
        
        footer = f'''
    print("Workflow completed!")


if __name__ == "__main__":
{param_input if param_input else "    pass"}
    try:
        {func_name}({example_str})
    except pyautogui.FailSafeException:
        print("\\nAutomation aborted by user (failsafe triggered)")
    except Exception as e:
        print(f"Error: {{e}}")
'''
        return footer
    
    def _to_function_name(self, name: str) -> str:
        """Convert workflow name to valid Python function name."""
        func_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        func_name = re.sub(r'_+', '_', func_name).strip('_')
        if func_name and func_name[0].isdigit():
            func_name = 'workflow_' + func_name
        return func_name or 'run_workflow'
    
    def save(self, code: str, path: Path) -> Path:
        """Save generated code to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        log.success(f"Generated script saved to: {path}")
        return path


def generate_pyautogui_script(
    action_sequence: ActionSequence,
    failsafe: bool = True,
    pause: float = 0.5
) -> str:
    """Convenience function to generate PyAutoGUI script."""
    generator = PyAutoGUIGenerator(failsafe=failsafe, pause=pause)
    return generator.generate(action_sequence)
