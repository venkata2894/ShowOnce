"""
Analyze module for ShowOnce.

This module handles AI-powered analysis of workflow screenshots:
- Claude Vision API integration (ClaudeVision)
- Prompt templates for analysis (prompts)
- Action inference engine (ActionInferenceEngine)
"""

from showonce.analyze.vision import ClaudeVision, create_vision_client
from showonce.analyze.prompts import (
    SYSTEM_PROMPT,
    TRANSITION_ANALYSIS_PROMPT,
    ELEMENT_DETECTION_PROMPT,
    build_transition_prompt,
    build_element_prompt,
    parse_analysis_response,
    get_system_prompt,
)
from showonce.analyze.inference import ActionInferenceEngine, analyze_workflow

__all__ = [
    # Vision
    "ClaudeVision",
    "create_vision_client",
    # Prompts
    "SYSTEM_PROMPT",
    "TRANSITION_ANALYSIS_PROMPT",
    "ELEMENT_DETECTION_PROMPT",
    "build_transition_prompt",
    "build_element_prompt",
    "parse_analysis_response",
    "get_system_prompt",
    # Inference
    "ActionInferenceEngine",
    "analyze_workflow",
]
