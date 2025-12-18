"""
Tests for the analyze module.
"""

import pytest
import json
import base64
import io
from unittest.mock import MagicMock, patch
from PIL import Image
from datetime import datetime

from showonce.analyze.prompts import (
    build_transition_prompt,
    build_element_prompt,
    build_workflow_prompt,
    parse_analysis_response,
    get_system_prompt,
    SYSTEM_PROMPT,
    TRANSITION_ANALYSIS_PROMPT,
)
from showonce.analyze.vision import ClaudeVision
from showonce.analyze.inference import ActionInferenceEngine
from showonce.models.actions import ActionType, SelectorStrategy
from showonce.models.workflow import Workflow, WorkflowStep


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def dummy_image_bytes():
    """Create dummy image bytes for testing."""
    img = Image.new('RGB', (10, 10), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def sample_api_response():
    """Sample Claude API response for transition analysis."""
    return {
        "actions": [
            {
                "sequence": 1,
                "type": "click",
                "target": {
                    "description": "Login button",
                    "selectors": [
                        {"strategy": "css", "value": "#login-btn", "confidence": 0.95},
                        {"strategy": "text", "value": "Login", "confidence": 0.8}
                    ],
                    "visual_description": "Blue button at bottom of form",
                    "element_type": "button"
                },
                "value": None,
                "is_variable": False,
                "confidence": 0.92
            }
        ],
        "state_change": {
            "before": "Login form visible",
            "after": "Loading spinner shown"
        },
        "observations": ["Form submission initiated"]
    }


@pytest.fixture
def mock_workflow(dummy_image_bytes):
    """Create a mock workflow with steps."""
    wf = Workflow(name="test_workflow", description="Test")
    
    # Add steps with screenshot data
    wf.add_step(
        description="Open login page",
        screenshot_bytes=dummy_image_bytes,
        timestamp=datetime.now().isoformat()
    )
    wf.add_step(
        description="Click login button",
        screenshot_bytes=dummy_image_bytes,
        timestamp=datetime.now().isoformat()
    )
    
    return wf


# =============================================================================
# PROMPTS TESTS
# =============================================================================

class TestPrompts:
    """Tests for prompts.py"""
    
    def test_build_transition_prompt_basic(self):
        """Test basic transition prompt building."""
        prompt = build_transition_prompt("I clicked the submit button")
        
        assert "I clicked the submit button" in prompt
        assert "BEFORE" in prompt or "before" in prompt.lower()
        assert "AFTER" in prompt or "after" in prompt.lower()
    
    def test_build_transition_prompt_with_context(self):
        """Test transition prompt with context."""
        context = {
            "workflow_name": "login_flow",
            "step_number": 3,
            "previous_action": "Entered username"
        }
        prompt = build_transition_prompt("Entered password", context)
        
        assert "Entered password" in prompt
        assert "login_flow" in prompt or "WORKFLOW" in prompt
    
    def test_build_element_prompt(self):
        """Test element detection prompt."""
        prompt = build_element_prompt("Submit button at bottom of form")
        
        assert "Submit button at bottom of form" in prompt
        assert "selectors" in prompt.lower() or "selector" in prompt.lower()
    
    def test_build_workflow_prompt(self):
        """Test workflow analysis prompt."""
        prompt = build_workflow_prompt("login_demo", "User login flow", 5)
        
        assert "login_demo" in prompt
        assert "5" in prompt
    
    def test_parse_analysis_response_valid_json(self):
        """Test parsing valid JSON response."""
        json_str = '{"action_type": "click", "confidence": 0.9}'
        result = parse_analysis_response(json_str)
        
        assert result["action_type"] == "click"
        assert result["confidence"] == 0.9
    
    def test_parse_analysis_response_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        json_str = '```json\n{"action_type": "type", "value": "hello"}\n```'
        result = parse_analysis_response(json_str)
        
        assert result["action_type"] == "type"
        assert result["value"] == "hello"
    
    def test_parse_analysis_response_invalid_json(self):
        """Test parsing invalid JSON returns error structure."""
        result = parse_analysis_response("not valid json at all")
        
        assert "error" in result
        assert "parse_error" in result
    
    def test_get_system_prompt_standard(self):
        """Test getting standard system prompt."""
        prompt = get_system_prompt("standard")
        assert len(prompt) > 0
        assert "UI" in prompt or "action" in prompt.lower()
    
    def test_get_system_prompt_detailed(self):
        """Test getting detailed system prompt."""
        prompt = get_system_prompt("detailed")
        assert len(prompt) > len(get_system_prompt("standard"))


# =============================================================================
# VISION TESTS
# =============================================================================

class TestClaudeVision:
    """Tests for vision.py"""
    
    @patch('anthropic.Anthropic')
    def test_vision_initialization(self, mock_anthropic):
        """Test ClaudeVision initializes correctly."""
        vision = ClaudeVision(api_key="test-key")
        
        assert vision.api_key == "test-key"
        mock_anthropic.assert_called_once()
    
    @patch('anthropic.Anthropic')
    def test_prepare_image_from_bytes(self, mock_anthropic, dummy_image_bytes):
        """Test image preparation from bytes."""
        vision = ClaudeVision(api_key="test-key")
        result = vision._prepare_image(dummy_image_bytes)
        
        assert "media_type" in result
        assert "data" in result
        assert result["media_type"] == "image/png"
        # Verify it's valid base64
        decoded = base64.b64decode(result["data"])
        assert len(decoded) > 0
    
    @patch('anthropic.Anthropic')
    def test_analyze_image(self, mock_anthropic, dummy_image_bytes):
        """Test single image analysis."""
        mock_client = mock_anthropic.return_value
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.text = "This is a blue square."
        mock_response.content = [mock_message]
        mock_client.messages.create.return_value = mock_response
        
        vision = ClaudeVision(api_key="test-key")
        result = vision.analyze_image(dummy_image_bytes, "What is this?")
        
        assert result == "This is a blue square."
        mock_client.messages.create.assert_called_once()
    
    @patch('anthropic.Anthropic')
    def test_analyze_transition(self, mock_anthropic, dummy_image_bytes, sample_api_response):
        """Test transition analysis between two images."""
        mock_client = mock_anthropic.return_value
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.text = json.dumps(sample_api_response)
        mock_response.content = [mock_message]
        mock_client.messages.create.return_value = mock_response
        
        vision = ClaudeVision(api_key="test-key")
        result = vision.analyze_transition(
            dummy_image_bytes, 
            dummy_image_bytes, 
            "Clicked login"
        )
        
        assert "actions" in result
        assert len(result["actions"]) == 1
        assert result["actions"][0]["type"] == "click"
    
    @patch('anthropic.Anthropic')
    def test_api_error_handling(self, mock_anthropic):
        """Test API error handling."""
        import anthropic
        
        mock_client = mock_anthropic.return_value
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="Rate limit exceeded",
            request=MagicMock(),
            body=None
        )
        
        vision = ClaudeVision(api_key="test-key")
        
        with pytest.raises(anthropic.APIError):
            vision._call_api([{"role": "user", "content": "test"}])


# =============================================================================
# INFERENCE TESTS
# =============================================================================

class TestActionInferenceEngine:
    """Tests for inference.py"""
    
    def test_determine_action_type_click(self):
        """Test action type mapping for click."""
        with patch('showonce.analyze.inference.create_vision_client'):
            engine = ActionInferenceEngine()
            
            assert engine._determine_action_type("click") == ActionType.CLICK
            assert engine._determine_action_type("CLICK") == ActionType.CLICK
    
    def test_determine_action_type_type(self):
        """Test action type mapping for type/input."""
        with patch('showonce.analyze.inference.create_vision_client'):
            engine = ActionInferenceEngine()
            
            assert engine._determine_action_type("type") == ActionType.TYPE
            assert engine._determine_action_type("input") == ActionType.TYPE
            assert engine._determine_action_type("fill") == ActionType.TYPE
    
    def test_determine_action_type_unknown(self):
        """Test action type mapping for unknown types."""
        with patch('showonce.analyze.inference.create_vision_client'):
            engine = ActionInferenceEngine()
            
            assert engine._determine_action_type("something_random") == ActionType.UNKNOWN
    
    def test_create_element_target(self):
        """Test ElementTarget creation from analysis data."""
        with patch('showonce.analyze.inference.create_vision_client'):
            engine = ActionInferenceEngine()
            
            target_data = {
                "description": "Submit button",
                "visual_description": "Blue button at bottom",
                "element_type": "button",
                "selectors": [
                    {"strategy": "css", "value": "#submit", "confidence": 0.95},
                    {"strategy": "text", "value": "Submit", "confidence": 0.8}
                ]
            }
            
            target = engine._create_element_target(target_data)
            
            assert target.description == "Submit button"
            assert target.visual_description == "Blue button at bottom"
            assert len(target.selectors) == 2
            
            primary = target.get_primary_selector()
            assert primary.value == "#submit"
            assert primary.confidence == 0.95
    
    def test_parse_to_actions(self, sample_api_response):
        """Test parsing API response to Action objects."""
        with patch('showonce.analyze.inference.create_vision_client'):
            engine = ActionInferenceEngine()
            
            actions = engine._parse_to_actions(sample_api_response, sequence_start=1)
            
            assert len(actions) == 1
            action = actions[0]
            assert action.action_type == ActionType.CLICK
            assert action.sequence == 1
            assert action.confidence == 0.92
            assert action.target is not None
            assert action.target.description == "Login button"
    
    @patch('showonce.analyze.inference.create_vision_client')
    def test_analyze_workflow_empty(self, mock_create_client):
        """Test analyzing workflow with insufficient steps."""
        engine = ActionInferenceEngine()
        wf = Workflow(name="empty", description="test")
        wf.add_step(description="Only one step")
        
        result = engine.analyze_workflow(wf)
        
        assert result.workflow_name == "empty"
        assert len(result.actions) == 0
    
    @patch('showonce.analyze.inference.create_vision_client')
    def test_analyze_workflow_full(self, mock_create_client, mock_workflow, sample_api_response):
        """Test full workflow analysis with mocked vision."""
        mock_vision = MagicMock()
        mock_vision.analyze_transition.return_value = sample_api_response
        mock_create_client.return_value = mock_vision
        
        engine = ActionInferenceEngine(vision_client=mock_vision)
        result = engine.analyze_workflow(mock_workflow)
        
        assert result.workflow_name == "test_workflow"
        assert len(result.actions) >= 1
        assert result.total_transitions == 1
