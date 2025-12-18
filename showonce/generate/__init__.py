"""
Generate module for ShowOnce.

This module handles code generation from analyzed workflows:
- PlaywrightGenerator: Modern async browser automation
- SeleniumGenerator: Classic WebDriver-based automation
- PyAutoGUIGenerator: Desktop/coordinate-based automation
- Factory: Get appropriate generator by framework name
- Runner: Execute generated scripts
"""

from showonce.generate.playwright_gen import PlaywrightGenerator, generate_playwright_script
from showonce.generate.selenium_gen import SeleniumGenerator, generate_selenium_script
from showonce.generate.pyautogui_gen import PyAutoGUIGenerator, generate_pyautogui_script
from showonce.generate.factory import (
    get_generator, 
    list_frameworks, 
    get_framework_info,
    check_framework_dependencies,
    FrameworkType
)
from showonce.generate.runner import ScriptRunner, run_script

__all__ = [
    # Playwright
    "PlaywrightGenerator",
    "generate_playwright_script",
    # Selenium
    "SeleniumGenerator", 
    "generate_selenium_script",
    # PyAutoGUI
    "PyAutoGUIGenerator",
    "generate_pyautogui_script",
    # Factory
    "get_generator",
    "list_frameworks",
    "get_framework_info",
    "check_framework_dependencies",
    "FrameworkType",
    # Runner
    "ScriptRunner",
    "run_script",
]
