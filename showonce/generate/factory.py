"""Generator factory for ShowOnce."""

from typing import Literal, Union, Any

from showonce.generate.playwright_gen import PlaywrightGenerator
from showonce.generate.selenium_gen import SeleniumGenerator
from showonce.generate.pyautogui_gen import PyAutoGUIGenerator
from showonce.utils.logger import log


FrameworkType = Literal["playwright", "selenium", "pyautogui"]

# Registry of available frameworks
FRAMEWORK_REGISTRY = {
    "playwright": {
        "class": PlaywrightGenerator,
        "description": "Modern browser automation with async support",
        "default_options": {"headless": False, "browser": "chromium"},
        "dependencies": ["playwright"],
    },
    "selenium": {
        "class": SeleniumGenerator,
        "description": "Classic browser automation with WebDriver",
        "default_options": {"headless": False, "browser": "chrome"},
        "dependencies": ["selenium"],
    },
    "pyautogui": {
        "class": PyAutoGUIGenerator,
        "description": "Desktop automation with screen coordinates",
        "default_options": {"failsafe": True, "pause": 0.5},
        "dependencies": ["pyautogui"],
    },
}


def get_generator(
    framework: FrameworkType, 
    **kwargs
) -> Union[PlaywrightGenerator, SeleniumGenerator, PyAutoGUIGenerator]:
    """
    Get appropriate generator for framework.
    
    Args:
        framework: One of 'playwright', 'selenium', 'pyautogui'
        **kwargs: Framework-specific options (headless, browser, etc.)
        
    Returns:
        Generator instance configured with options
        
    Raises:
        ValueError: If framework is not supported
    """
    framework = framework.lower()
    
    if framework not in FRAMEWORK_REGISTRY:
        available = ", ".join(FRAMEWORK_REGISTRY.keys())
        raise ValueError(f"Unknown framework: {framework}. Available: {available}")
    
    registry_entry = FRAMEWORK_REGISTRY[framework]
    generator_class = registry_entry["class"]
    
    # Merge default options with user-provided kwargs
    options = {**registry_entry["default_options"], **kwargs}
    
    log.debug(f"Creating {framework} generator with options: {options}")
    
    return generator_class(**options)


def list_frameworks() -> list[str]:
    """
    List available frameworks.
    
    Returns:
        List of framework names
    """
    return list(FRAMEWORK_REGISTRY.keys())


def get_framework_info(framework: FrameworkType) -> dict:
    """
    Get information about a framework.
    
    Args:
        framework: Framework name
        
    Returns:
        Dict with description, default_options, dependencies
    """
    framework = framework.lower()
    
    if framework not in FRAMEWORK_REGISTRY:
        raise ValueError(f"Unknown framework: {framework}")
    
    entry = FRAMEWORK_REGISTRY[framework]
    return {
        "name": framework,
        "description": entry["description"],
        "default_options": entry["default_options"],
        "dependencies": entry["dependencies"],
    }


def get_all_frameworks_info() -> list[dict]:
    """
    Get information about all available frameworks.
    
    Returns:
        List of framework info dicts
    """
    return [get_framework_info(name) for name in FRAMEWORK_REGISTRY.keys()]


def check_framework_dependencies(framework: FrameworkType) -> tuple[bool, list[str]]:
    """
    Check if required dependencies for a framework are installed.
    
    Args:
        framework: Framework to check
        
    Returns:
        Tuple of (all_installed, missing_packages)
    """
    import importlib
    
    framework = framework.lower()
    if framework not in FRAMEWORK_REGISTRY:
        raise ValueError(f"Unknown framework: {framework}")
    
    dependencies = FRAMEWORK_REGISTRY[framework]["dependencies"]
    missing = []
    
    for dep in dependencies:
        try:
            importlib.import_module(dep)
        except ImportError:
            missing.append(dep)
    
    return (len(missing) == 0, missing)
