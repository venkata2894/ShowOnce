"""
Tests for ShowOnce data models.

Run with: pytest tests/test_models.py -v
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from showonce.models.workflow import Workflow, WorkflowStep, StepMetadata
from showonce.models.actions import (
    Action, ActionType, ElementTarget, 
    Selector, SelectorStrategy, ActionSequence
)


class TestWorkflowStep:
    """Tests for WorkflowStep model."""
    
    def test_create_step(self):
        """Test creating a basic workflow step."""
        step = WorkflowStep(
            step_number=1,
            description="Click login button"
        )
        
        assert step.step_number == 1
        assert step.description == "Click login button"
        assert not step.has_screenshot()
    
    def test_step_with_screenshot(self):
        """Test step with base64 screenshot."""
        # Simple 1x1 pixel PNG in base64
        tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        step = WorkflowStep(
            step_number=1,
            description="Test step",
            screenshot_base64=tiny_png
        )
        
        assert step.has_screenshot()
        assert step.load_screenshot_bytes() is not None
    
    def test_step_metadata(self):
        """Test step with metadata."""
        step = WorkflowStep(
            step_number=1,
            description="Test",
            metadata=StepMetadata(
                active_window="Chrome",
                mouse_position=(100, 200),
                screen_resolution=(1920, 1080)
            )
        )
        
        assert step.metadata.active_window == "Chrome"
        assert step.metadata.mouse_position == (100, 200)


class TestWorkflow:
    """Tests for Workflow model."""
    
    def test_create_workflow(self):
        """Test creating a basic workflow."""
        workflow = Workflow(
            name="test_workflow",
            description="A test workflow"
        )
        
        assert workflow.name == "test_workflow"
        assert workflow.description == "A test workflow"
        assert workflow.step_count == 0
    
    def test_add_steps(self):
        """Test adding steps to workflow."""
        workflow = Workflow(name="test")
        
        workflow.add_step(description="Step 1")
        workflow.add_step(description="Step 2")
        workflow.add_step(description="Step 3")
        
        assert workflow.step_count == 3
        assert workflow.transition_count == 2
        
        step = workflow.get_step(2)
        assert step is not None
        assert step.description == "Step 2"
    
    def test_remove_step(self):
        """Test removing a step."""
        workflow = Workflow(name="test")
        workflow.add_step(description="Step 1")
        workflow.add_step(description="Step 2")
        workflow.add_step(description="Step 3")
        
        workflow.remove_step(2)
        
        assert workflow.step_count == 2
        assert workflow.steps[1].step_number == 2
        assert workflow.steps[1].description == "Step 3"
    
    def test_save_and_load(self):
        """Test saving and loading workflow."""
        workflow = Workflow(
            name="save_test",
            description="Test save/load"
        )
        workflow.add_step(description="Step 1")
        workflow.add_step(description="Step 2")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_workflow"
            workflow.save(save_path, save_screenshots=False)
            
            # Verify files exist
            assert (save_path / "workflow.json").exists()
            
            # Load and verify
            loaded = Workflow.load(save_path)
            assert loaded.name == "save_test"
            assert loaded.step_count == 2
            assert loaded.steps[0].description == "Step 1"
    
    def test_get_screenshot_pairs(self):
        """Test getting consecutive step pairs."""
        workflow = Workflow(name="test")
        workflow.add_step(description="A")
        workflow.add_step(description="B")
        workflow.add_step(description="C")
        
        pairs = workflow.get_screenshot_pairs()
        
        assert len(pairs) == 2
        assert pairs[0][0].description == "A"
        assert pairs[0][1].description == "B"
        assert pairs[1][0].description == "B"
        assert pairs[1][1].description == "C"
    
    def test_workflow_summary(self):
        """Test workflow summary output."""
        workflow = Workflow(name="summary_test")
        workflow.add_step(description="Open page")
        workflow.add_step(description="Click button")
        
        summary = workflow.summary()
        
        assert "summary_test" in summary
        assert "Open page" in summary
        assert "Click button" in summary


class TestElementTarget:
    """Tests for ElementTarget model."""
    
    def test_create_target(self):
        """Test creating element target."""
        target = ElementTarget(
            description="Login button",
            visual_description="Blue button at bottom"
        )
        
        assert target.description == "Login button"
        assert len(target.selectors) == 0
    
    def test_add_selectors(self):
        """Test adding selectors to target."""
        target = ElementTarget(description="Button")
        
        target.add_selector(SelectorStrategy.CSS, "button#login", confidence=0.95)
        target.add_selector(SelectorStrategy.TEXT, "Log In", confidence=0.8)
        
        assert len(target.selectors) == 2
        
        primary = target.get_primary_selector()
        assert primary is not None
        assert primary.confidence == 0.95
        assert primary.value == "button#login"
    
    def test_playwright_selectors(self):
        """Test converting to Playwright format."""
        target = ElementTarget(description="Test")
        target.add_selector(SelectorStrategy.CSS, "div.test")
        target.add_selector(SelectorStrategy.TEXT, "Click me")
        
        selectors = target.get_playwright_selectors()
        
        assert "div.test" in selectors
        assert "text=Click me" in selectors


class TestAction:
    """Tests for Action model."""
    
    def test_create_click_action(self):
        """Test creating click action."""
        target = ElementTarget(description="Submit button")
        target.add_selector(SelectorStrategy.CSS, "button[type='submit']")
        
        action = Action(
            action_type=ActionType.CLICK,
            sequence=1,
            target=target,
            confidence=0.9
        )
        
        assert action.action_type == ActionType.CLICK
        assert action.confidence == 0.9
    
    def test_create_type_action(self):
        """Test creating type action."""
        target = ElementTarget(description="Username field")
        target.add_selector(SelectorStrategy.CSS, "input#username")
        
        action = Action(
            action_type=ActionType.TYPE,
            sequence=2,
            target=target,
            value="testuser",
            is_variable=True,
            variable_name="username"
        )
        
        assert action.action_type == ActionType.TYPE
        assert action.value == "testuser"
        assert action.is_variable
        assert action.variable_name == "username"
    
    def test_to_playwright_code(self):
        """Test generating Playwright code."""
        target = ElementTarget(description="Button")
        target.add_selector(SelectorStrategy.CSS, "button#submit")
        
        action = Action(
            action_type=ActionType.CLICK,
            sequence=1,
            target=target
        )
        
        code = action.to_playwright_code()
        
        assert "await page.click" in code
        assert "button#submit" in code
    
    def test_to_description(self):
        """Test generating action description."""
        target = ElementTarget(description="login button")
        
        action = Action(
            action_type=ActionType.CLICK,
            sequence=1,
            target=target
        )
        
        desc = action.to_description()
        
        assert "Click" in desc
        assert "login button" in desc


class TestActionSequence:
    """Tests for ActionSequence model."""
    
    def test_create_sequence(self):
        """Test creating action sequence."""
        sequence = ActionSequence(workflow_name="test")
        
        assert sequence.workflow_name == "test"
        assert len(sequence.actions) == 0
    
    def test_add_actions(self):
        """Test adding actions to sequence."""
        sequence = ActionSequence(workflow_name="test")
        
        action1 = Action(
            action_type=ActionType.NAVIGATE,
            sequence=1,  # Will be updated by add_action
            url="https://example.com"
        )
        
        action2 = Action(
            action_type=ActionType.CLICK,
            sequence=1,  # Will be updated by add_action
            target=ElementTarget(description="Button")
        )
        
        sequence.add_action(action1)
        sequence.add_action(action2)
        
        assert len(sequence.actions) == 2
        assert sequence.actions[0].sequence == 1
        assert sequence.actions[1].sequence == 2
    
    def test_parameter_tracking(self):
        """Test that variables are tracked."""
        sequence = ActionSequence(workflow_name="test")
        
        action = Action(
            action_type=ActionType.TYPE,
            sequence=1,  # Will be updated by add_action
            target=ElementTarget(description="Email field"),
            value="test@example.com",
            is_variable=True,
            variable_name="email"
        )
        
        sequence.add_action(action)
        
        assert len(sequence.parameters) == 1
        assert sequence.parameters[0]["name"] == "email"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
