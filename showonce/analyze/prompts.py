"""Prompt templates for Claude Vision analysis."""

import json
from typing import Optional, Dict, Any

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT = '''You are an expert UI automation analyst. Your task is to analyze screenshots of user interfaces and identify the exact actions a user performed.

CORE CAPABILITIES:
1. Identify UI elements (buttons, inputs, links, dropdowns, etc.)
2. Detect visual changes between screenshots
3. Infer user actions from those changes
4. Generate reliable selectors for automation

OUTPUT RULES:
- Always respond with valid JSON only
- No markdown formatting around JSON
- Use null for missing values, not empty strings
- Confidence scores are 0.0 to 1.0
- Prefer specific selectors over generic ones

SELECTOR PRIORITY (highest to lowest confidence):
1. ID selectors (#unique-id)
2. Data attributes ([data-testid="value"])
3. Aria labels ([aria-label="text"])
4. Class + text content (.btn:contains("Submit"))
5. Text content alone
6. Position-based (last resort)

ACTION TYPES:
- click: Mouse click on element
- type: Keyboard input into field
- select: Dropdown/combobox selection
- scroll: Page or element scroll
- hover: Mouse hover (if change detected)
- key_press: Special key (Enter, Tab, Escape)
- navigate: URL change / page navigation
- wait: Intentional pause (rare)
'''

SYSTEM_PROMPT_DETAILED = SYSTEM_PROMPT + '''
ADDITIONAL ANALYSIS:
- Identify potential variables (usernames, passwords, search terms)
- Note any error states or validation messages
- Detect modal dialogs, popups, or overlays
- Identify form progress (multi-step forms)
- Note any loading states or spinners
'''

# =============================================================================
# TRANSITION ANALYSIS PROMPT
# =============================================================================

TRANSITION_ANALYSIS_PROMPT = '''Analyze the transition between the BEFORE and AFTER screenshots.

USER DESCRIPTION: {user_description}

{context_section}

TASK: Identify what action(s) the user performed to get from BEFORE to AFTER.

Return JSON in this exact format:
{{
  "actions": [
    {{
      "sequence": 1,
      "type": "click|type|scroll|select|key_press|navigate|hover|wait",
      "target": {{
        "description": "Human readable description of element",
        "selectors": [
          {{"strategy": "css", "value": "#submit-btn", "confidence": 0.95}},
          {{"strategy": "xpath", "value": "//button[@type='submit']", "confidence": 0.9}},
          {{"strategy": "text", "value": "Submit", "confidence": 0.8}}
        ],
        "visual_description": "Blue button at bottom right of form",
        "element_type": "button"
      }},
      "value": "text if typing, null otherwise",
      "is_variable": false,
      "variable_name": null,
      "confidence": 0.92
    }}
  ],
  "state_change": {{
    "before": "Description of the UI state before action",
    "after": "Description of the UI state after action"
  }},
  "observations": ["Any notable observations about the transition"]
}}

IMPORTANT:
- Focus on what CHANGED between the screenshots
- If typing, capture the exact text that appeared
- Mark sensitive data (passwords, emails) as is_variable=true
- Provide multiple selector strategies when possible
- Visual descriptions should help identify the element even if selectors fail
'''

# =============================================================================
# ELEMENT DETECTION PROMPT
# =============================================================================

ELEMENT_DETECTION_PROMPT = '''Analyze this screenshot and identify the UI element described below.

ELEMENT TO FIND: {element_description}

Return JSON in this exact format:
{{
  "found": true,
  "element": {{
    "description": "Human readable description",
    "selectors": [
      {{"strategy": "css", "value": "selector", "confidence": 0.95}},
      {{"strategy": "xpath", "value": "xpath", "confidence": 0.9}},
      {{"strategy": "text", "value": "visible text", "confidence": 0.8}}
    ],
    "visual_description": "Visual location and appearance",
    "element_type": "button|input|link|dropdown|...",
    "bounding_box": {{
      "approximate": true,
      "region": "top-left|top-center|top-right|center-left|center|center-right|bottom-left|bottom-center|bottom-right"
    }}
  }},
  "alternatives": [
    {{
      "description": "Similar element if ambiguous",
      "reason": "Why this might also match"
    }}
  ],
  "confidence": 0.95
}}

If the element is not found, return:
{{
  "found": false,
  "reason": "Why the element could not be found",
  "suggestions": ["Possible alternatives or clarifications"]
}}
'''

# =============================================================================
# FULL WORKFLOW ANALYSIS PROMPT
# =============================================================================

WORKFLOW_ANALYSIS_PROMPT = '''Analyze this complete workflow of {step_count} steps.

WORKFLOW NAME: {workflow_name}
DESCRIPTION: {workflow_description}

For each step, I will provide:
- Step number
- User's description of what they did
- Screenshot (before and after if available)

TASK: Create a complete automation script specification.

Return JSON in this format:
{{
  "workflow_name": "{workflow_name}",
  "summary": "Brief summary of what this workflow accomplishes",
  "variables": [
    {{
      "name": "variable_name",
      "description": "What this variable is for",
      "default_value": "example value",
      "required": true
    }}
  ],
  "steps": [
    {{
      "step": 1,
      "description": "What this step does",
      "actions": [...],
      "wait_condition": "Condition to wait for before proceeding"
    }}
  ],
  "error_handling": [
    {{
      "scenario": "Common error scenario",
      "detection": "How to detect this error",
      "recovery": "How to recover"
    }}
  ]
}}
'''

# =============================================================================
# BUILDER FUNCTIONS
# =============================================================================

def build_transition_prompt(
    user_description: str, 
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build prompt for transition analysis.
    
    Args:
        user_description: User's description of what they did
        context: Optional context (previous actions, workflow info, etc.)
    
    Returns:
        Formatted prompt string
    """
    context_section = ""
    if context:
        context_parts = []
        if context.get("previous_action"):
            context_parts.append(f"PREVIOUS ACTION: {context['previous_action']}")
        if context.get("workflow_name"):
            context_parts.append(f"WORKFLOW: {context['workflow_name']}")
        if context.get("step_number"):
            context_parts.append(f"STEP: {context['step_number']}")
        if context.get("url"):
            context_parts.append(f"URL: {context['url']}")
        context_section = "\n".join(context_parts)
    
    return TRANSITION_ANALYSIS_PROMPT.format(
        user_description=user_description,
        context_section=context_section if context_section else "No additional context provided."
    )


def build_element_prompt(element_description: str) -> str:
    """
    Build prompt for element detection.
    
    Args:
        element_description: Description of the element to find
        
    Returns:
        Formatted prompt string
    """
    return ELEMENT_DETECTION_PROMPT.format(element_description=element_description)


def build_workflow_prompt(
    workflow_name: str,
    workflow_description: str,
    step_count: int
) -> str:
    """
    Build prompt for full workflow analysis.
    
    Args:
        workflow_name: Name of the workflow
        workflow_description: Description of the workflow
        step_count: Number of steps in the workflow
        
    Returns:
        Formatted prompt string
    """
    return WORKFLOW_ANALYSIS_PROMPT.format(
        workflow_name=workflow_name,
        workflow_description=workflow_description or "No description provided",
        step_count=step_count
    )


def parse_analysis_response(response: str) -> Dict[str, Any]:
    """
    Parse Claude's JSON response safely.
    
    Args:
        response: Raw response string from Claude
        
    Returns:
        Parsed dictionary, or error dict if parsing fails
    """
    # Clean the response
    text = response.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Return error structure
        return {
            "error": "Failed to parse JSON response",
            "parse_error": str(e),
            "raw_response": response[:500]  # First 500 chars for debugging
        }


def get_system_prompt(detail_level: str = "standard") -> str:
    """
    Get system prompt based on detail level.
    
    Args:
        detail_level: "standard" or "detailed"
        
    Returns:
        System prompt string
    """
    if detail_level == "detailed":
        return SYSTEM_PROMPT_DETAILED
    return SYSTEM_PROMPT
