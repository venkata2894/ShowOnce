"""Action inference engine for ShowOnce."""

from typing import List, Optional, Callable, Dict, Any
from datetime import datetime

from showonce.models.workflow import Workflow, WorkflowStep
from showonce.models.actions import (
    Action, ActionType, ElementTarget, ActionSequence, 
    Selector, SelectorStrategy
)
from showonce.analyze.vision import ClaudeVision, create_vision_client
from showonce.analyze.prompts import build_transition_prompt, parse_api_response, get_system_prompt
from showonce.config import get_config
from showonce.utils.logger import log
import re
import json


class ActionInferenceEngine:
    """Infer actions from workflow screenshots using AI."""
    
    def __init__(self, vision_client: Optional[ClaudeVision] = None):
        """Initialize inference engine."""
        self.vision = vision_client or create_vision_client()
        self.config = get_config()
        self._cache: Dict[str, Any] = {}
        
        log.debug("ActionInferenceEngine initialized")
    
    def analyze_workflow(
        self, 
        workflow: Workflow,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ActionSequence:
        """Analyze complete workflow and infer all actions with accurate reporting."""
        log.info(f"Analyzing workflow: {workflow.name} ({workflow.step_count} steps)")
        
        action_sequence = ActionSequence(
            workflow_name=workflow.name,
            total_transitions=workflow.transition_count,
            analyzed_at=datetime.now().isoformat(),
            model_used=self.config.analyze.model
        )
        
        pairs = workflow.get_screenshot_pairs()
        successful_parses = 0
        failed_parses = 0
        action_counter = 1
        
        for i, (before_step, after_step) in enumerate(pairs):
            if progress_callback:
                progress_callback(i + 1, len(pairs))
            
            log.info(f"Analyzing transition {i+1}/{len(pairs)}: Step {before_step.step_number} -> {after_step.step_number}")
            
            try:
                actions = self.analyze_transition(
                    before_step, after_step, 
                    sequence_start=action_counter,
                    context={
                        "workflow_name": workflow.name,
                        "step_number": before_step.step_number
                    }
                )
                
                # Count only valid, non-unknown actions
                valid_actions = [a for a in actions 
                              if a.action_type != ActionType.UNKNOWN 
                              and (a.description != "" or a.target is not None)]
                
                if valid_actions:
                    for action in valid_actions:
                        action_sequence.add_action(action)
                        action_counter += 1
                    successful_parses += 1
                else:
                    failed_parses += 1
                    log.warning(f"Transition {i+1}: No valid actions parsed")
                    # Still add a fallback so the sequence isn't broken
                    fallback = Action(
                        action_type=ActionType.UNKNOWN,
                        sequence=action_counter,
                        description=after_step.description or f"Step {after_step.step_number}",
                        confidence=0.0
                    )
                    action_sequence.add_action(fallback)
                    action_counter += 1
                    
            except Exception as e:
                failed_parses += 1
                log.error(f"Transition {i+1} failed: {e}")
                fallback = Action(
                    action_type=ActionType.UNKNOWN,
                    sequence=action_counter,
                    description=after_step.description or f"Step {after_step.step_number}",
                    confidence=0.0
                )
                action_sequence.add_action(fallback)
                action_counter += 1
        
        # Accurate reporting
        total = len(pairs)
        if total > 0:
            if failed_parses == total:
                log.error(f"❌ Analysis FAILED: All {total} transitions failed to parse")
            elif failed_parses > 0:
                log.warning(f"⚠️ Partial: {successful_parses}/{total} transitions successful")
            else:
                log.success(f"✓ Success: All {total} transitions analyzed")
                
        return action_sequence
    
    def analyze_transition(
        self,
        before_step: WorkflowStep,
        after_step: WorkflowStep,
        sequence_start: int = 1,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Action]:
        """
        Analyze single transition between two steps.
        
        Returns list because one transition might contain multiple actions.
        """
        # Get screenshot data
        before_image = before_step.get_screenshot_data()
        after_image = after_step.get_screenshot_data()
        
        if not before_image or not after_image:
            log.warning("Missing screenshot data for transition")
            return [Action(
                action_type=ActionType.UNKNOWN,
                sequence=sequence_start,
                description=after_step.description or "Unknown action",
                confidence=0.0,
                reasoning="Missing screenshot data"
            )]
        
        # Build prompt
        user_description = after_step.description or "User performed an action"
        prompt = build_transition_prompt(user_description, context)
        system_prompt = get_system_prompt("detailed")
        
        # Call Claude Vision
        try:
            response_text = self.vision.analyze_transition(
                before_image=before_image,
                after_image=after_image,
                user_description=prompt, # Pass the formatted prompt as user_description
                system_prompt=system_prompt
            )
            
            # Response is now raw text, parse it
            return self._parse_to_actions(response_text, sequence_start)
            
        except Exception as e:
            log.error(f"Vision analysis failed: {e}")
            raise
    
    def _parse_to_actions(self, response_text: str, sequence_start: int = 1) -> List[Action]:
        """Convert API response text to a list of Action objects."""
        # Use robust parser from prompts.py
        analysis = parse_api_response(response_text)
        
        if not analysis or "actions" not in analysis:
            log.error("API response missing 'actions' key")
            return []
        
        actions = []
        for i, action_data in enumerate(analysis.get("actions", [])):
            try:
                # 1. Ensure description exists (handled by Action validator too, but good to be explicit)
                if "description" not in action_data or action_data["description"] is None:
                    action_data["description"] = f"Action {sequence_start + i}"
                
                # 2. Create action with safe defaults
                action = self._create_action_safe(action_data, sequence_start + i)
                if action:
                    actions.append(action)
                    
            except Exception as e:
                log.error(f"Failed to parse action {i}: {e}")
                continue
                
        return actions
    
    def _create_action_safe(self, action_data: dict, sequence: int) -> Optional[Action]:
        """Create Action with safe defaults for missing fields."""
        try:
            # Map action type safely
            action_type_str = action_data.get("type") or action_data.get("action_type", "unknown")
            action_type = self._determine_action_type(action_type_str)
            
            # Build target if present
            target = None
            target_data = action_data.get("target")
            if target_data:
                target = self._create_element_target(target_data)
            
            # Create action with all required fields
            return Action(
                action_type=action_type,
                sequence=sequence,
                target=target,
                description=action_data.get("description") or f"Step {sequence}",
                value=action_data.get("value"),
                is_variable=action_data.get("is_variable", False),
                variable_name=action_data.get("variable_name"),
                confidence=float(action_data.get("confidence", 0.5)),
                raw_analysis=action_data
            )
        except Exception as e:
            log.error(f"Failed to create action: {e}")
            return None
    
    def _create_element_target(self, target_data: dict) -> ElementTarget:
        """Create ElementTarget from analysis data."""
        target = ElementTarget(
            description=target_data.get("description", "Unknown element"),
            visual_description=target_data.get("visual_description"),
            element_type=target_data.get("element_type")
        )
        
        # Add selectors
        selectors = target_data.get("selectors", [])
        for sel in selectors:
            strategy_str = sel.get("strategy", "css").lower()
            value = sel.get("value")
            confidence = float(sel.get("confidence", 0.8))
            
            if value:
                # Map strategy string to enum
                strategy_map = {
                    "css": SelectorStrategy.CSS,
                    "xpath": SelectorStrategy.XPATH,
                    "text": SelectorStrategy.TEXT,
                    "role": SelectorStrategy.ROLE,
                    "label": SelectorStrategy.LABEL,
                    "placeholder": SelectorStrategy.PLACEHOLDER,
                    "test_id": SelectorStrategy.TEST_ID,
                    "testid": SelectorStrategy.TEST_ID,
                    "data-testid": SelectorStrategy.TEST_ID,
                    "coordinates": SelectorStrategy.COORDINATES,
                }
                strategy = strategy_map.get(strategy_str, SelectorStrategy.CSS)
                target.add_selector(strategy, value, confidence)
        
        return target
    
    def _determine_action_type(self, type_str: str) -> ActionType:
        """Map string action type to ActionType enum."""
        type_map = {
            "click": ActionType.CLICK,
            "double_click": ActionType.DOUBLE_CLICK,
            "right_click": ActionType.RIGHT_CLICK,
            "type": ActionType.TYPE,
            "input": ActionType.TYPE,
            "fill": ActionType.TYPE,
            "scroll": ActionType.SCROLL_DOWN,  # Default scroll to scroll_down
            "scroll_up": ActionType.SCROLL_UP,
            "scroll_down": ActionType.SCROLL_DOWN,
            "scroll_to": ActionType.SCROLL_TO,
            "select": ActionType.SELECT,
            "choose": ActionType.SELECT,
            "dropdown": ActionType.SELECT,
            "check": ActionType.CHECK,
            "uncheck": ActionType.UNCHECK,
            "hover": ActionType.HOVER,
            "key_press": ActionType.PRESS_KEY,
            "press_key": ActionType.PRESS_KEY,
            "keyboard": ActionType.PRESS_KEY,
            "hotkey": ActionType.HOTKEY,
            "navigate": ActionType.NAVIGATE,
            "goto": ActionType.NAVIGATE,
            "url": ActionType.NAVIGATE,
            "go_back": ActionType.GO_BACK,
            "go_forward": ActionType.GO_FORWARD,
            "wait": ActionType.WAIT,
            "wait_for_element": ActionType.WAIT_FOR_ELEMENT,
            "drag": ActionType.DRAG,
            "upload": ActionType.UPLOAD,
            "download": ActionType.DOWNLOAD,
            "switch_tab": ActionType.SWITCH_TAB,
            "new_tab": ActionType.NEW_TAB,
            "close_tab": ActionType.CLOSE_TAB,
            "refresh": ActionType.REFRESH,
            "submit": ActionType.CLICK,  # Submit usually is a click
        }
        
        normalized = type_str.lower().strip()
        return type_map.get(normalized, ActionType.UNKNOWN)


def analyze_workflow(workflow: Workflow) -> ActionSequence:
    """
    Convenience function to analyze a workflow.
    
    Usage:
        actions = analyze_workflow(workflow)
    """
    engine = ActionInferenceEngine()
    return engine.analyze_workflow(workflow)
