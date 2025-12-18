"""Action inference engine for ShowOnce."""

from typing import List, Optional, Callable, Dict, Any
from datetime import datetime

from showonce.models.workflow import Workflow, WorkflowStep
from showonce.models.actions import (
    Action, ActionType, ElementTarget, ActionSequence, 
    Selector, SelectorStrategy
)
from showonce.analyze.vision import ClaudeVision, create_vision_client
from showonce.analyze.prompts import (
    build_transition_prompt, parse_analysis_response, 
    get_system_prompt
)
from showonce.config import get_config
from showonce.utils.logger import log


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
        """
        Analyze complete workflow and infer all actions.
        
        Args:
            workflow: Workflow to analyze
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            ActionSequence with all inferred actions
        """
        log.info(f"Analyzing workflow: {workflow.name} ({workflow.step_count} steps)")
        
        if workflow.step_count < 2:
            log.warning("Workflow has fewer than 2 steps, nothing to analyze")
            return ActionSequence(
                workflow_name=workflow.name,
                total_transitions=0,
                analyzed_at=datetime.now().isoformat(),
                model_used=self.config.analyze.model
            )
        
        action_sequence = ActionSequence(
            workflow_name=workflow.name,
            total_transitions=workflow.step_count - 1,
            analyzed_at=datetime.now().isoformat(),
            model_used=self.config.analyze.model
        )
        
        steps = workflow.steps
        total_transitions = len(steps) - 1
        action_counter = 1
        
        for i in range(total_transitions):
            before_step = steps[i]
            after_step = steps[i + 1]
            
            if progress_callback:
                progress_callback(i + 1, total_transitions)
            
            log.info(f"Analyzing transition {i+1}/{total_transitions}: "
                    f"Step {before_step.step_number} -> Step {after_step.step_number}")
            
            try:
                actions = self.analyze_transition(
                    before_step, after_step, 
                    sequence_start=action_counter,
                    context={
                        "workflow_name": workflow.name,
                        "step_number": before_step.step_number
                    }
                )
                
                for action in actions:
                    action_sequence.add_action(action)
                    action_counter += 1
                    
            except Exception as e:
                log.error(f"Failed to analyze transition {i+1}: {e}")
                # Add a fallback action so we don't lose the step
                fallback = Action(
                    action_type=ActionType.UNKNOWN,
                    sequence=action_counter,
                    description=after_step.description or f"Step {after_step.step_number}",
                    confidence=0.0,
                    reasoning=f"Analysis failed: {str(e)}"
                )
                action_sequence.add_action(fallback)
                action_counter += 1
        
        log.success(f"Workflow analysis complete: {len(action_sequence.actions)} actions inferred")
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
            response = self.vision.analyze_transition(
                before_image=before_image,
                after_image=after_image,
                user_description=user_description,
                system_prompt=system_prompt
            )
            
            # Response is already parsed dict from vision.py
            if "error" in response:
                log.error(f"Analysis returned error: {response['error']}")
                return [Action(
                    action_type=ActionType.UNKNOWN,
                    sequence=sequence_start,
                    description=after_step.description or "Unknown",
                    confidence=0.0,
                    reasoning=response.get("error", "Unknown error")
                )]
            
            return self._parse_to_actions(response, sequence_start)
            
        except Exception as e:
            log.error(f"Vision analysis failed: {e}")
            raise
    
    def _parse_to_actions(self, analysis: dict, sequence_start: int) -> List[Action]:
        """Convert parsed analysis to Action objects."""
        actions = []
        
        # Handle both single action and multiple actions
        action_list = analysis.get("actions", [])
        if not action_list:
            # Maybe it's a single action format
            if "action_type" in analysis:
                action_list = [analysis]
        
        for i, action_data in enumerate(action_list):
            try:
                action_type = self._determine_action_type(
                    action_data.get("type") or action_data.get("action_type", "unknown")
                )
                
                target = None
                target_data = action_data.get("target")
                if target_data:
                    target = self._create_element_target(target_data)
                
                action = Action(
                    action_type=action_type,
                    sequence=sequence_start + i,
                    target=target,
                    value=action_data.get("value"),
                    description=action_data.get("description") or 
                               target_data.get("description") if target_data else None,
                    confidence=float(action_data.get("confidence", 0.5)),
                    is_variable=action_data.get("is_variable", False),
                    variable_name=action_data.get("variable_name"),
                    reasoning=action_data.get("reasoning")
                )
                actions.append(action)
                
            except Exception as e:
                log.warning(f"Failed to parse action {i}: {e}")
                # Add fallback
                actions.append(Action(
                    action_type=ActionType.UNKNOWN,
                    sequence=sequence_start + i,
                    confidence=0.0,
                    reasoning=f"Parse error: {str(e)}"
                ))
        
        if not actions:
            # No actions parsed, return unknown
            actions.append(Action(
                action_type=ActionType.UNKNOWN,
                sequence=sequence_start,
                confidence=0.0,
                reasoning="No actions detected in analysis"
            ))
        
        return actions
    
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
