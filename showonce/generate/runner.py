"""Script runner for ShowOnce."""

import subprocess
import sys
import ast
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from showonce.utils.logger import log


class ScriptRunner:
    """Execute generated automation scripts."""
    
    def __init__(self, script_path: Path):
        """
        Initialize with script to run.
        
        Args:
            script_path: Path to the Python script
        """
        self.script_path = Path(script_path)
        
        if not self.script_path.exists():
            raise FileNotFoundError(f"Script not found: {self.script_path}")
        
        log.debug(f"ScriptRunner initialized for: {self.script_path}")
    
    def run(
        self, 
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> dict:
        """
        Execute the script.
        
        Args:
            params: Parameters to pass as environment variables
            timeout: Execution timeout in seconds
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            {success: bool, output: str, error: str, return_code: int}
        """
        log.info(f"Running script: {self.script_path}")
        
        # Build environment with parameters
        import os
        env = os.environ.copy()
        
        if params:
            for key, value in params.items():
                env[f"SHOWONCE_{key.upper()}"] = str(value)
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path)],
                env=env,
                timeout=timeout,
                capture_output=capture_output,
                text=True
            )
            
            success = result.returncode == 0
            
            if success:
                log.success("Script executed successfully")
            else:
                log.error(f"Script failed with code: {result.returncode}")
            
            return {
                "success": success,
                "output": result.stdout if capture_output else "",
                "error": result.stderr if capture_output else "",
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            log.error(f"Script timed out after {timeout}s")
            return {
                "success": False,
                "output": "",
                "error": f"Script timed out after {timeout} seconds",
                "return_code": -1
            }
        except Exception as e:
            log.error(f"Script execution error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1
            }
    
    def run_interactive(
        self,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> int:
        """
        Run script interactively (for scripts that need user input).
        
        Args:
            params: Parameters as environment variables
            timeout: Execution timeout
            
        Returns:
            Exit code
        """
        log.info(f"Running script interactively: {self.script_path}")
        
        import os
        env = os.environ.copy()
        
        if params:
            for key, value in params.items():
                env[f"SHOWONCE_{key.upper()}"] = str(value)
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path)],
                env=env,
                timeout=timeout
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            log.error(f"Script timed out after {timeout}s")
            return -1
    
    def validate_script(self) -> tuple[bool, str]:
        """
        Validate script syntax without running.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse the AST to check syntax
            ast.parse(source)
            
            log.debug("Script syntax is valid")
            return (True, "")
            
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            log.error(error_msg)
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            log.error(error_msg)
            return (False, error_msg)
    
    def check_dependencies(self) -> tuple[bool, List[str]]:
        """
        Check if required packages are installed.
        
        Analyzes import statements in the script.
        
        Returns:
            Tuple of (all_installed, missing_packages)
        """
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse AST to find imports
            tree = ast.parse(source)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
            
            # Check each import
            missing = []
            builtin_modules = {
                'asyncio', 'time', 'sys', 'os', 'subprocess', 're', 
                'json', 'datetime', 'pathlib', 'typing', 'webbrowser'
            }
            
            for module in imports:
                if module in builtin_modules:
                    continue
                if module == 'showonce':
                    continue
                
                try:
                    __import__(module)
                except ImportError:
                    missing.append(module)
            
            if missing:
                log.warning(f"Missing dependencies: {missing}")
            else:
                log.debug("All dependencies are installed")
            
            return (len(missing) == 0, missing)
            
        except Exception as e:
            log.error(f"Error checking dependencies: {e}")
            return (False, [f"Error: {str(e)}"])
    
    def get_script_info(self) -> dict:
        """
        Extract information about the script.
        
        Returns:
            Dict with name, docstring, parameters
        """
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            info = {
                "name": self.script_path.stem,
                "path": str(self.script_path),
                "docstring": None,
                "functions": [],
                "parameters": []
            }
            
            # Get module docstring
            if tree.body and isinstance(tree.body[0], ast.Expr):
                if isinstance(tree.body[0].value, ast.Constant):
                    info["docstring"] = tree.body[0].value.value
            
            # Find functions and their parameters
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "parameters": [arg.arg for arg in node.args.args if arg.arg != 'self'],
                        "is_async": isinstance(node, ast.AsyncFunctionDef)
                    }
                    info["functions"].append(func_info)
                    
                    # Collect parameters from main function
                    if node.name not in ['__init__', 'main']:
                        info["parameters"].extend(func_info["parameters"])
            
            return info
            
        except Exception as e:
            return {
                "name": self.script_path.stem,
                "path": str(self.script_path),
                "error": str(e)
            }


def run_script(
    script_path: Path,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None
) -> dict:
    """
    Convenience function to run a script.
    
    Args:
        script_path: Path to script
        params: Parameters to pass
        timeout: Execution timeout
        
    Returns:
        Execution result dict
    """
    runner = ScriptRunner(script_path)
    return runner.run(params=params, timeout=timeout)
