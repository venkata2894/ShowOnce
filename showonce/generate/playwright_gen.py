"""Playwright code generator for ShowOnce."""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import re

from showonce.models.actions import ActionSequence, Action, ActionType
from showonce.config import get_config
from showonce.utils.logger import log


class PlaywrightGenerator:
    """Generate Playwright automation scripts from ActionSequence."""
    
    def __init__(self, headless: bool = False, browser: str = "chromium"):
        """
        Initialize generator with settings.
        
        Args:
            headless: Run browser in headless mode
            browser: Browser to use (chromium, firefox, webkit)
        """
        self.headless = headless
        self.browser = browser
        self.config = get_config()
        self.indent = "    "  # 4 spaces
        
        log.debug(f"PlaywrightGenerator initialized (headless={headless}, browser={browser})")
    
    def generate(self, action_sequence: ActionSequence) -> str:
        """
        Generate complete Playwright script.
        
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
                lines.append(f"{self.indent * 3}{line}")
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
            ActionType.SELECT: self._generate_select,
            ActionType.NAVIGATE: self._generate_navigate,
            ActionType.WAIT: self._generate_wait,
            ActionType.WAIT_FOR_ELEMENT: self._generate_wait_for_element,
            ActionType.SCROLL_DOWN: self._generate_scroll,
            ActionType.SCROLL_UP: self._generate_scroll,
            ActionType.SCROLL_TO: self._generate_scroll,
            ActionType.PRESS_KEY: self._generate_press_key,
            ActionType.HOTKEY: self._generate_hotkey,
            ActionType.HOVER: self._generate_hover,
            ActionType.CHECK: self._generate_check,
            ActionType.UNCHECK: self._generate_uncheck,
            ActionType.DRAG: self._generate_drag,
            ActionType.REFRESH: self._generate_refresh,
            ActionType.GO_BACK: self._generate_go_back,
            ActionType.GO_FORWARD: self._generate_go_forward,
        }
        
        handler = handlers.get(action.action_type, self._generate_unknown)
        
        # Add comment with step description
        lines = [f"# Step {action.sequence}: {action.to_description()}"]
        lines.extend(handler(action))
        
        # Add a small wait after actions (configurable)
        if action.action_type not in [ActionType.WAIT, ActionType.WAIT_FOR_ELEMENT, ActionType.NAVIGATE]:
            lines.append("await page.wait_for_timeout(300)  # Brief pause")
        
        return lines
    
    def _generate_click(self, action: Action) -> List[str]:
        """Generate click action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.click({selector})"]
    
    def _generate_double_click(self, action: Action) -> List[str]:
        """Generate double click action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.dblclick({selector})"]
    
    def _generate_right_click(self, action: Action) -> List[str]:
        """Generate right click action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.click({selector}, button='right')"]
    
    def _generate_type(self, action: Action) -> List[str]:
        """Generate type/fill action code."""
        selector = self._get_selector_with_fallback(action)
        
        if action.is_variable and action.variable_name:
            value = action.variable_name
        else:
            # Escape quotes in value
            value = f'"{self._escape_string(action.value or "")}"'
        
        return [
            f"await page.click({selector})  # Focus the field",
            f"await page.fill({selector}, {value})"
        ]
    
    def _generate_select(self, action: Action) -> List[str]:
        """Generate select/dropdown action code."""
        selector = self._get_selector_with_fallback(action)
        value = f'"{self._escape_string(action.value or "")}"'
        return [f"await page.select_option({selector}, {value})"]
    
    def _generate_navigate(self, action: Action) -> List[str]:
        """Generate navigation action code."""
        url = action.url or ""
        return [
            f'await page.goto("{url}")',
            'await page.wait_for_load_state("networkidle")'
        ]
    
    def _generate_wait(self, action: Action) -> List[str]:
        """Generate wait action code."""
        return ['await page.wait_for_load_state("networkidle")']
    
    def _generate_wait_for_element(self, action: Action) -> List[str]:
        """Generate wait for element action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.wait_for_selector({selector}, timeout=10000)"]
    
    def _generate_scroll(self, action: Action) -> List[str]:
        """Generate scroll action code."""
        amount = action.scroll_amount or 300
        
        if action.action_type == ActionType.SCROLL_UP:
            amount = -abs(amount)
        elif action.action_type == ActionType.SCROLL_TO:
            selector = self._get_selector_with_fallback(action)
            return [f"await page.locator({selector}).scroll_into_view_if_needed()"]
        
        return [f"await page.mouse.wheel(0, {amount})"]
    
    def _generate_press_key(self, action: Action) -> List[str]:
        """Generate key press action code."""
        key = action.key or "Enter"
        return [f'await page.keyboard.press("{key}")']
    
    def _generate_hotkey(self, action: Action) -> List[str]:
        """Generate hotkey/keyboard shortcut action code."""
        modifiers = action.modifiers or []
        key = action.key or ""
        
        # Build key combination
        keys = "+".join(modifiers + [key])
        return [f'await page.keyboard.press("{keys}")']
    
    def _generate_hover(self, action: Action) -> List[str]:
        """Generate hover action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.hover({selector})"]
    
    def _generate_check(self, action: Action) -> List[str]:
        """Generate checkbox check action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.check({selector})"]
    
    def _generate_uncheck(self, action: Action) -> List[str]:
        """Generate checkbox uncheck action code."""
        selector = self._get_selector_with_fallback(action)
        return [f"await page.uncheck({selector})"]
    
    def _generate_drag(self, action: Action) -> List[str]:
        """Generate drag action code."""
        if action.drag_start and action.drag_end:
            sx, sy = action.drag_start
            ex, ey = action.drag_end
            return [
                f"await page.mouse.move({sx}, {sy})",
                "await page.mouse.down()",
                f"await page.mouse.move({ex}, {ey})",
                "await page.mouse.up()"
            ]
        selector = self._get_selector_with_fallback(action)
        return [f"# TODO: Drag action needs coordinates - {selector}"]
    
    def _generate_refresh(self, action: Action) -> List[str]:
        """Generate page refresh action code."""
        return ["await page.reload()"]
    
    def _generate_go_back(self, action: Action) -> List[str]:
        """Generate go back action code."""
        return ["await page.go_back()"]
    
    def _generate_go_forward(self, action: Action) -> List[str]:
        """Generate go forward action code."""
        return ["await page.go_forward()"]
    
    def _generate_unknown(self, action: Action) -> List[str]:
        """Generate placeholder for unknown action types."""
        return [f"# TODO: Unknown action type - {action.action_type}"]
    
    def _get_selector_with_fallback(self, action: Action) -> str:
        """
        Generate selector code with fallback logic.
        
        Returns a string representing the selector, with fallback comments.
        """
        if not action.target:
            return '"body"  # No target specified'
        
        primary = action.target.get_primary_selector()
        if not primary:
            # Use coordinates as fallback
            if action.target.coordinates:
                x, y = action.target.coordinates
                return f'"body", position={{"x": {x}, "y": {y}}}'
            return f'"*:has-text(\"{action.target.description}\")"  # Fallback'
        
        # Return the playwright selector
        selector_value = primary.to_playwright()
        return f'"{self._escape_string(selector_value)}"'
    
    def _escape_string(self, s: str) -> str:
        """Escape special characters in strings."""
        if s is None:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    
    def _generate_header(self, action_sequence: ActionSequence) -> str:
        """Generate script header with imports and function definition."""
        # Build function name from workflow name
        func_name = self._to_function_name(action_sequence.workflow_name)
        
        # Build parameters from variables
        params = []
        param_docs = []
        example_values = []
        
        for param in action_sequence.parameters:
            name = param.get("name", "param")
            params.append(f"{name}: str")
            param_docs.append(f"        {name}: Value for {param.get('description', 'parameter')}")
            example_values.append(f'{name}="example"')
        
        params_str = ", ".join(params) if params else ""
        param_docs_str = "\n".join(param_docs) if param_docs else "        None"
        example_str = ", ".join(example_values) if example_values else ""
        
        header = f'''# Auto-generated by ShowOnce
# Workflow: {action_sequence.workflow_name}
# Generated: {datetime.now().isoformat()}
# Actions: {len(action_sequence.actions)}

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


async def {func_name}({params_str}):
    """
    Automated workflow: {action_sequence.workflow_name}
    
    Parameters:
{param_docs_str}
    """
    async with async_playwright() as p:
        browser = await p.{self.browser}.launch(headless={self.headless})
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
'''
        return header
    
    def _generate_footer(self, action_sequence: ActionSequence) -> str:
        """Generate script footer with main block."""
        func_name = self._to_function_name(action_sequence.workflow_name)
        
        # Build example call with parameters
        example_params = []
        for param in action_sequence.parameters:
            name = param.get("name", "param")
            example_params.append(f'{name}="YOUR_VALUE"')
        
        example_str = ", ".join(example_params) if example_params else ""
        param_input = ""
        
        if example_params:
            param_input = "\n".join([
                f'    {p.get("name")} = input("Enter {p.get("name")}: ")'
                for p in action_sequence.parameters
            ])
            example_str = ", ".join([p.get("name") for p in action_sequence.parameters])
        
        footer = f'''
        except PlaywrightTimeout as e:
            print(f"Timeout error: {{e}}")
            raise
        except Exception as e:
            print(f"Error during automation: {{e}}")
            raise
        finally:
            await browser.close()
            print("Workflow completed!")


if __name__ == "__main__":
{param_input if param_input else "    pass"}
    asyncio.run({func_name}({example_str}))
'''
        return footer
    
    def _to_function_name(self, name: str) -> str:
        """Convert workflow name to valid Python function name."""
        # Replace spaces and special chars with underscores
        func_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        # Remove consecutive underscores
        func_name = re.sub(r'_+', '_', func_name)
        # Remove leading/trailing underscores
        func_name = func_name.strip('_')
        # Ensure it starts with a letter
        if func_name and func_name[0].isdigit():
            func_name = 'workflow_' + func_name
        return func_name or 'run_workflow'
    
    def save(self, code: str, path: Path) -> Path:
        """
        Save generated code to file.
        
        Args:
            code: Generated Python code
            path: Path to save to
            
        Returns:
            Path to saved file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        log.success(f"Generated script saved to: {path}")
        return path


def generate_playwright_script(
    action_sequence: ActionSequence,
    headless: bool = False,
    browser: str = "chromium"
) -> str:
    """
    Convenience function to generate Playwright script.
    
    Args:
        action_sequence: Actions to convert
        headless: Run in headless mode
        browser: Browser to use
        
    Returns:
        Generated Python script
    """
    generator = PlaywrightGenerator(headless=headless, browser=browser)
    return generator.generate(action_sequence)
