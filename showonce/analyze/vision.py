"""Claude Vision API integration for ShowOnce."""

import anthropic
import base64
import time
import json
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from showonce.config import get_config
from showonce.utils.logger import log

class ClaudeVision:
    """Interface to Claude Vision API for screenshot analysis."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude Vision client."""
        config = get_config()
        self.api_key = api_key or config.analyze.api_key
        
        if not self.api_key:
            log.warning("Anthropic API key not found. Analysis will fail.")
            
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            max_retries=3  # Handles rate limits and transient errors
        )
        self.model = config.analyze.model
        self.max_tokens = config.analyze.max_tokens
        
        log.debug(f"Initialized ClaudeVision with model: {self.model}")
    
    def analyze_image(
        self, 
        image: Union[bytes, str, Path],
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Analyze a single image with Claude Vision.
        
        Args:
            image: Image as bytes, base64 string, or file path
            prompt: User prompt describing what to analyze
            system_prompt: Optional system prompt
            
        Returns:
            Claude's analysis as string
        """
        try:
            image_data = self._prepare_image(image)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_data["media_type"],
                                "data": image_data["data"],
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ]
            
            return self._call_api(messages, system=system_prompt)
            
        except Exception as e:
            log.error(f"Error analyzing image: {e}")
            raise
    
    def analyze_transition(
        self,
        before_image: Union[bytes, str, Path],
        after_image: Union[bytes, str, Path],
        user_description: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze the transition between two screenshots.
        
        Args:
            before_image: Screenshot before action
            after_image: Screenshot after action
            user_description: User's description of what they did
            
        Returns:
            Structured analysis of the action performed (Action model fields)
        """
        try:
            before_data = self._prepare_image(before_image)
            after_data = self._prepare_image(after_image)
            
            # Construct a prompt that asks for structured JSON output
            analysis_prompt = f"""
            The user performed an action described as: "{user_description}"
            
            Compare the BEFORE and AFTER images to identify exactly what happened.
            
            Return a JSON object with the following fields:
            - action_type: The type of action (click, type, key_press, scroll, etc.)
            - target_element: Description of the UI element interacted with (e.g., "Submit button", "Username field")
            - value: Any value entered or typed (if applicable)
            - confidence: Confidence score (0.0 to 1.0)
            - reasoning: Brief explanation of why this action was inferred
            - selector_hint: A visual description that could help find the element selectors (text, color, position)
            
            Focus on the difference between the two images.
            """
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "BEFORE Image:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": before_data["media_type"],
                                "data": before_data["data"],
                            },
                        },
                        {
                            "type": "text",
                            "text": "AFTER Image:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": after_data["media_type"],
                                "data": after_data["data"],
                            },
                        },
                        {
                            "type": "text",
                            "text": analysis_prompt
                        }
                    ],
                }
            ]
            
            response_text = self._call_api(messages, system=system_prompt)
            
            # Parse JSON from response
            # Claude might wrap JSON in markdown blocks, so we clean it
            cleaned_text = self._clean_json_block(response_text)
            return json.loads(cleaned_text)
            
        except Exception as e:
            log.error(f"Error analyzing transition: {e}")
            # Return a fallback error dict rather than crashing flow?
            # Or raise to let caller handle? raising is better for now.
            raise

    def _prepare_image(self, image: Union[bytes, str, Path]) -> Dict[str, str]:
        """
        Prepare image for API request.
        
        Returns dict with keys: 'media_type', 'data' (base64 string)
        """
        media_type = "image/png" # Default, maybe detect later
        b64_data = ""
        
        if isinstance(image, bytes):
            b64_data = base64.b64encode(image).decode("utf-8")
        elif isinstance(image, (str, Path)):
            path = Path(image)
            if path.exists():
                # Detect type from extension
                suffix = path.suffix.lower()
                if suffix in ['.jpg', '.jpeg']:
                    media_type = "image/jpeg"
                elif suffix == '.webp':
                    media_type = "image/webp"
                
                with open(path, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")
            else:
                # Assume it's a base64 string if not a file
                # Basic validation
                if len(image) > 100: # Heuristic
                    b64_data = str(image)
                else:
                    raise FileNotFoundError(f"Image path not found: {image}")
        
        return {
            "media_type": media_type,
            "data": b64_data
        }
    
    def _call_api(
        self, 
        messages: List[dict],
        system: Optional[str] = None
    ) -> str:
        """Make API call with retry logic."""
        if not self.api_key:
            raise ValueError("Anthropic API key is missing")
            
        log.debug("Calling Claude Vision API...")
        start_time = time.time()
        
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
                
            response = self.client.messages.create(**kwargs)
            
            duration = time.time() - start_time
            log.info(f"Claude API success ({duration:.2f}s)")
            
            return response.content[0].text
            
        except anthropic.APIError as e:
            log.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error calling Claude: {e}")
            raise

    def _clean_json_block(self, text: str) -> str:
        """Extract JSON from markdown code blocks if present."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()


def create_vision_client() -> ClaudeVision:
    """Factory function to create ClaudeVision instance."""
    config = get_config()
    return ClaudeVision(api_key=config.analyze.api_key)
