"""Selenium code generator for ShowOnce."""

from typing import List, Optional
from pathlib import Path
from datetime import datetime
import re

from showonce.models.actions import ActionSequence, Action, ActionType
from showonce.config import get_config
from showonce.utils.logger import log


class SeleniumGenerator:
    """Generate Selenium automation scripts from ActionSequence."""
    
    def __init__(self, browser: str = "chrome", headless: bool = False):
        """
        Initialize generator with settings.
        
        Args:
            browser: Browser to use (chrome, firefox, edge)
            headless: Run browser in headless mode
        """
        self.browser = browser.lower()
        self.headless = headless
        self.config = get_config()
        self.indent = "    "  # 4 spaces
        
        log.debug(f"SeleniumGenerator initialized (browser={browser}, headless={headless})")
    
    def generate(self, action_sequence: ActionSequence) -> str:
        """
        Generate complete Selenium script.
        
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
                lines.append(f"{self.indent * 2}{line}")
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
            ActionType.REFRESH: self._generate_refresh,
            ActionType.GO_BACK: self._generate_go_back,
            ActionType.GO_FORWARD: self._generate_go_forward,
        }
        
        handler = handlers.get(action.action_type, self._generate_unknown)
        
        # Add comment with step description
        lines = [f"# Step {action.sequence}: {action.to_description()}"]
        lines.extend(handler(action))
        
        # Add a small wait after actions
        if action.action_type not in [ActionType.WAIT, ActionType.WAIT_FOR_ELEMENT, ActionType.NAVIGATE]:
            lines.append("time.sleep(0.3)  # Brief pause")
        
        return lines
    
    def _generate_click(self, action: Action) -> List[str]:
        """Generate click action code."""
        locator = self._get_locator(action)
        return [
            f"element = wait.until(EC.element_to_be_clickable({locator}))",
            "element.click()"
        ]
    
    def _generate_double_click(self, action: Action) -> List[str]:
        """Generate double click action code."""
        locator = self._get_locator(action)
        return [
            f"element = wait.until(EC.element_to_be_clickable({locator}))",
            "ActionChains(driver).double_click(element).perform()"
        ]
    
    def _generate_right_click(self, action: Action) -> List[str]:
        """Generate right click action code."""
        locator = self._get_locator(action)
        return [
            f"element = wait.until(EC.element_to_be_clickable({locator}))",
            "ActionChains(driver).context_click(element).perform()"
        ]
    
    def _generate_type(self, action: Action) -> List[str]:
        """Generate type/fill action code."""
        locator = self._get_locator(action)
        
        if action.is_variable and action.variable_name:
            value = action.variable_name
        else:
            value = f'"{self._escape_string(action.value or "")}"'
        
        return [
            f"element = wait.until(EC.presence_of_element_located({locator}))",
            "element.clear()",
            f"element.send_keys({value})"
        ]
    
    def _generate_select(self, action: Action) -> List[str]:
        """Generate select/dropdown action code."""
        locator = self._get_locator(action)
        value = f'"{self._escape_string(action.value or "")}"'
        return [
            f"dropdown = Select(wait.until(EC.presence_of_element_located({locator})))",
            f"dropdown.select_by_visible_text({value})"
        ]
    
    def _generate_navigate(self, action: Action) -> List[str]:
        """Generate navigation action code."""
        url = action.url or ""
        return [
            f'driver.get("{url}")',
            "wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))"
        ]
    
    def _generate_wait(self, action: Action) -> List[str]:
        """Generate wait action code."""
        return ["time.sleep(2)  # Wait for page to stabilize"]
    
    def _generate_wait_for_element(self, action: Action) -> List[str]:
        """Generate wait for element action code."""
        locator = self._get_locator(action)
        return [f"wait.until(EC.presence_of_element_located({locator}))"]
    
    def _generate_scroll(self, action: Action) -> List[str]:
        """Generate scroll action code."""
        amount = action.scroll_amount or 300
        
        if action.action_type == ActionType.SCROLL_UP:
            amount = -abs(amount)
        elif action.action_type == ActionType.SCROLL_TO:
            locator = self._get_locator(action)
            return [
                f"element = driver.find_element({locator})",
                "driver.execute_script('arguments[0].scrollIntoView(true);', element)"
            ]
        
        return [f"driver.execute_script('window.scrollBy(0, {amount});')"]
    
    def _generate_press_key(self, action: Action) -> List[str]:
        """Generate key press action code."""
        key = action.key or "RETURN"
        key_upper = key.upper()
        return [f"ActionChains(driver).send_keys(Keys.{key_upper}).perform()"]
    
    def _generate_hotkey(self, action: Action) -> List[str]:
        """Generate hotkey/keyboard shortcut action code."""
        modifiers = action.modifiers or []
        key = action.key or ""
        
        keys = []
        for mod in modifiers:
            keys.append(f"Keys.{mod.upper()}")
        keys.append(f"'{key}'")
        
        chain = ", ".join(keys)
        return [f"ActionChains(driver).key_down({chain}).key_up({chain}).perform()"]
    
    def _generate_hover(self, action: Action) -> List[str]:
        """Generate hover action code."""
        locator = self._get_locator(action)
        return [
            f"element = wait.until(EC.presence_of_element_located({locator}))",
            "ActionChains(driver).move_to_element(element).perform()"
        ]
    
    def _generate_check(self, action: Action) -> List[str]:
        """Generate checkbox check action code."""
        locator = self._get_locator(action)
        return [
            f"checkbox = wait.until(EC.element_to_be_clickable({locator}))",
            "if not checkbox.is_selected():",
            "    checkbox.click()"
        ]
    
    def _generate_uncheck(self, action: Action) -> List[str]:
        """Generate checkbox uncheck action code."""
        locator = self._get_locator(action)
        return [
            f"checkbox = wait.until(EC.element_to_be_clickable({locator}))",
            "if checkbox.is_selected():",
            "    checkbox.click()"
        ]
    
    def _generate_refresh(self, action: Action) -> List[str]:
        """Generate page refresh action code."""
        return ["driver.refresh()"]
    
    def _generate_go_back(self, action: Action) -> List[str]:
        """Generate go back action code."""
        return ["driver.back()"]
    
    def _generate_go_forward(self, action: Action) -> List[str]:
        """Generate go forward action code."""
        return ["driver.forward()"]
    
    def _generate_unknown(self, action: Action) -> List[str]:
        """Generate placeholder for unknown action types."""
        return [f"# TODO: Unknown action type - {action.action_type}"]
    
    def _get_locator(self, action: Action) -> str:
        """Generate Selenium locator tuple."""
        if not action.target:
            return '(By.TAG_NAME, "body")'
        
        primary = action.target.get_primary_selector()
        if not primary:
            if action.target.text_content:
                return f'(By.XPATH, "//*[contains(text(), \'{action.target.text_content}\')]")'
            return '(By.TAG_NAME, "body")'
        
        # Convert to Selenium By locator
        by_type, value = primary.to_selenium()
        return f'({by_type}, "{self._escape_string(value)}")'
    
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
        
        # Browser setup
        if self.browser == "firefox":
            driver_setup = "driver = webdriver.Firefox(options=options)"
            options_class = "FirefoxOptions"
            import_browser = "from selenium.webdriver.firefox.options import Options as FirefoxOptions"
        elif self.browser == "edge":
            driver_setup = "driver = webdriver.Edge(options=options)"
            options_class = "EdgeOptions"
            import_browser = "from selenium.webdriver.edge.options import Options as EdgeOptions"
        else:
            driver_setup = "driver = webdriver.Chrome(options=options)"
            options_class = "ChromeOptions"
            import_browser = "from selenium.webdriver.chrome.options import Options as ChromeOptions"
        
        headless_line = 'options.add_argument("--headless")' if self.headless else "# options.add_argument('--headless')  # Uncomment for headless mode"
        
        header = f'''# Auto-generated by ShowOnce
# Workflow: {action_sequence.workflow_name}
# Generated: {datetime.now().isoformat()}
# Actions: {len(action_sequence.actions)}

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
{import_browser}


def {func_name}({params_str}):
    """
    Automated workflow: {action_sequence.workflow_name}
    
    Parameters:
{param_docs_str}
    """
    options = {options_class}()
    {headless_line}
    options.add_argument("--start-maximized")
    
    {driver_setup}
    wait = WebDriverWait(driver, 10)
    
    try:
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
    except Exception as e:
        print(f"Error during automation: {{e}}")
        raise
    finally:
        driver.quit()
        print("Workflow completed!")


if __name__ == "__main__":
{param_input if param_input else "    pass"}
    {func_name}({example_str})
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


def generate_selenium_script(
    action_sequence: ActionSequence,
    browser: str = "chrome",
    headless: bool = False
) -> str:
    """Convenience function to generate Selenium script."""
    generator = SeleniumGenerator(browser=browser, headless=headless)
    return generator.generate(action_sequence)
