"""
Action data models.

Defines the structure for inferred actions and their targets.
These models represent what the AI determines happened between screenshots.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions that can be inferred from screenshots."""
    
    # Mouse actions
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    DRAG = "drag"
    
    # Keyboard actions
    TYPE = "type"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    
    # Scroll actions
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    SCROLL_TO = "scroll_to"
    
    # Form actions
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    
    # Navigation
    NAVIGATE = "navigate"
    GO_BACK = "go_back"
    GO_FORWARD = "go_forward"
    REFRESH = "refresh"
    
    # Wait actions
    WAIT = "wait"
    WAIT_FOR_ELEMENT = "wait_for_element"
    
    # File actions
    UPLOAD = "upload"
    DOWNLOAD = "download"
    
    # Window actions
    SWITCH_TAB = "switch_tab"
    CLOSE_TAB = "close_tab"
    NEW_TAB = "new_tab"
    
    # Unknown/custom
    UNKNOWN = "unknown"
    CUSTOM = "custom"


class SelectorStrategy(str, Enum):
    """Strategies for targeting elements."""
    
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEST_ID = "test_id"
    COORDINATES = "coordinates"


class Selector(BaseModel):
    """A single element selector with its strategy."""
    
    strategy: SelectorStrategy
    value: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    def to_playwright(self) -> str:
        """Convert to Playwright selector format."""
        if self.strategy == SelectorStrategy.CSS:
            return self.value
        elif self.strategy == SelectorStrategy.XPATH:
            return f"xpath={self.value}"
        elif self.strategy == SelectorStrategy.TEXT:
            return f"text={self.value}"
        elif self.strategy == SelectorStrategy.ROLE:
            return f"role={self.value}"
        elif self.strategy == SelectorStrategy.LABEL:
            return f"label={self.value}"
        elif self.strategy == SelectorStrategy.PLACEHOLDER:
            return f"placeholder={self.value}"
        elif self.strategy == SelectorStrategy.TEST_ID:
            return f"data-testid={self.value}"
        else:
            return self.value
    
    def to_selenium(self) -> tuple[str, str]:
        """Convert to Selenium By locator format."""
        from selenium.webdriver.common.by import By
        
        mapping = {
            SelectorStrategy.CSS: (By.CSS_SELECTOR, self.value),
            SelectorStrategy.XPATH: (By.XPATH, self.value),
            SelectorStrategy.TEXT: (By.LINK_TEXT, self.value),
            SelectorStrategy.LABEL: (By.NAME, self.value),
        }
        return mapping.get(self.strategy, (By.CSS_SELECTOR, self.value))


class ElementTarget(BaseModel):
    """
    Target element for an action.
    
    Contains multiple selector strategies ranked by reliability,
    allowing fallback if the primary selector fails.
    """
    
    # Human-readable description
    description: str = Field(description="Human-readable element description")
    visual_description: Optional[str] = Field(
        default=None, 
        description="Visual description for debugging"
    )
    
    # Selectors ranked by preference
    selectors: List[Selector] = Field(
        default_factory=list,
        description="List of selectors in order of preference"
    )
    
    # Fallback: coordinates (x, y)
    coordinates: Optional[tuple[int, int]] = Field(
        default=None,
        description="Screen coordinates as last resort"
    )
    
    # Bounding box if detected
    bounding_box: Optional[Dict[str, int]] = Field(
        default=None,
        description="Element bounding box: {x, y, width, height}"
    )
    
    # Element attributes detected
    tag_name: Optional[str] = None
    text_content: Optional[str] = None
    element_type: Optional[str] = None  # button, input, link, etc.
    
    def get_primary_selector(self) -> Optional[Selector]:
        """Get the highest confidence selector."""
        if not self.selectors:
            return None
        return max(self.selectors, key=lambda s: s.confidence)
    
    def get_playwright_selectors(self) -> List[str]:
        """Get all selectors in Playwright format."""
        return [s.to_playwright() for s in self.selectors]
    
    def add_selector(
        self, 
        strategy: SelectorStrategy | str, 
        value: str, 
        confidence: float = 0.8
    ):
        """Add a new selector."""
        if isinstance(strategy, str):
            strategy = SelectorStrategy(strategy)
        self.selectors.append(Selector(
            strategy=strategy,
            value=value,
            confidence=confidence
        ))


class Action(BaseModel):
    """
    An inferred action between two workflow steps.
    
    Represents what the AI determined happened between a "before"
    and "after" screenshot, including the action type, target element,
    any input value, and confidence level.
    """
    
    # Action identification
    action_type: ActionType = Field(description="Type of action performed")
    sequence: int = Field(ge=1, description="Order in the action sequence")
    
    # Target element (for most actions)
    target: Optional[ElementTarget] = Field(
        default=None,
        description="Target element of the action"
    )
    
    # Action parameters
    value: Optional[str] = Field(
        default=None,
        description="Value for the action (e.g., text to type)"
    )
    is_variable: bool = Field(
        default=False,
        description="Whether the value should be parameterized"
    )
    variable_name: Optional[str] = Field(
        default=None,
        description="Suggested parameter name if is_variable"
    )
    
    # For keyboard actions
    key: Optional[str] = Field(default=None, description="Key to press")
    modifiers: List[str] = Field(
        default_factory=list,
        description="Modifier keys (ctrl, alt, shift)"
    )
    
    # For scroll actions
    scroll_amount: Optional[int] = None
    
    # For navigation
    url: Optional[str] = None
    
    # For drag actions
    drag_start: Optional[tuple[int, int]] = None
    drag_end: Optional[tuple[int, int]] = None
    
    # Confidence and verification
    confidence: float = Field(
        ge=0.0, le=1.0, default=0.8,
        description="AI confidence in this inference"
    )
    
    # Pre/post conditions
    preconditions: List[str] = Field(
        default_factory=list,
        description="What must be true before this action"
    )
    postconditions: List[str] = Field(
        default_factory=list,
        description="What should be true after this action"
    )
    
    # Human-readable description
    description: str = Field(
        default="",
        description="Human-readable action description"
    )
    
    # Raw AI analysis output
    raw_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw output from AI analysis"
    )
    
    def to_playwright_code(self) -> str:
        """Generate Playwright code for this action."""
        if self.action_type == ActionType.CLICK:
            selector = self.target.get_primary_selector() if self.target else None
            if selector:
                return f'await page.click("{selector.to_playwright()}")'
            elif self.target and self.target.coordinates:
                x, y = self.target.coordinates
                return f'await page.click(position={{"x": {x}, "y": {y}}})'
        
        elif self.action_type == ActionType.TYPE:
            selector = self.target.get_primary_selector() if self.target else None
            value = f'{{{self.variable_name}}}' if self.is_variable else self.value
            if selector:
                return f'await page.fill("{selector.to_playwright()}", "{value}")'
        
        elif self.action_type == ActionType.NAVIGATE:
            return f'await page.goto("{self.url}")'
        
        elif self.action_type == ActionType.PRESS_KEY:
            return f'await page.keyboard.press("{self.key}")'
        
        elif self.action_type == ActionType.SCROLL_DOWN:
            amount = self.scroll_amount or 300
            return f'await page.mouse.wheel(0, {amount})'
        
        elif self.action_type == ActionType.WAIT:
            return 'await page.wait_for_load_state("networkidle")'
        
        # Default fallback
        return f'# TODO: Implement {self.action_type.value} action'
    
    def to_description(self) -> str:
        """Generate human-readable description."""
        if self.description:
            return self.description
        
        if self.action_type == ActionType.CLICK:
            target_desc = self.target.description if self.target else "element"
            return f"Click {target_desc}"
        
        elif self.action_type == ActionType.TYPE:
            target_desc = self.target.description if self.target else "field"
            if self.is_variable:
                return f"Type {{{self.variable_name}}} into {target_desc}"
            return f"Type '{self.value}' into {target_desc}"
        
        elif self.action_type == ActionType.NAVIGATE:
            return f"Navigate to {self.url}"
        
        elif self.action_type == ActionType.SELECT:
            target_desc = self.target.description if self.target else "dropdown"
            return f"Select '{self.value}' from {target_desc}"
        
        return f"{self.action_type.value.replace('_', ' ').title()}"
    
    class Config:
        use_enum_values = True


class ActionSequence(BaseModel):
    """A sequence of actions inferred from a workflow."""
    
    workflow_name: str
    actions: List[Action] = Field(default_factory=list)
    parameters: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Variables that need user input at runtime"
    )
    
    # Analysis metadata
    total_transitions: int = 0
    analyzed_at: Optional[str] = None
    model_used: Optional[str] = None
    
    def add_action(self, action: Action):
        """Add an action to the sequence."""
        action.sequence = len(self.actions) + 1
        self.actions.append(action)
        
        # Track variables
        if action.is_variable and action.variable_name:
            self.parameters.append({
                "name": action.variable_name,
                "action_sequence": action.sequence,
                "action_type": action.action_type,
                "description": action.target.description if action.target else ""
            })
    
    def get_code_comments(self) -> List[str]:
        """Get human-readable steps for code comments."""
        return [f"Step {a.sequence}: {a.to_description()}" for a in self.actions]


if __name__ == "__main__":
    # Example usage
    target = ElementTarget(
        description="Login button",
        visual_description="Blue button at bottom of form"
    )
    target.add_selector(SelectorStrategy.CSS, "button#login", confidence=0.95)
    target.add_selector(SelectorStrategy.TEXT, "Log In", confidence=0.8)
    
    action = Action(
        action_type=ActionType.CLICK,
        sequence=1,
        target=target,
        confidence=0.92,
        description="Click the login button to submit credentials"
    )
    
    print(f"Action: {action.to_description()}")
    print(f"Code: {action.to_playwright_code()}")
