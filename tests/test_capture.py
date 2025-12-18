"""
Tests for the capture module.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
from PIL import Image
import base64
from datetime import datetime

from showonce.capture.screenshot import ScreenCapture
from showonce.capture.hotkeys import HotkeyListener
from showonce.capture.metadata import MetadataCollector, CaptureMetadata
from showonce.capture.recorder import RecordingSession
from showonce.models.workflow import Workflow


# --- ScreenCapture Tests ---

@pytest.fixture
def screen_capture():
    return ScreenCapture()

def test_screen_capture_image_conversions(screen_capture):
    """Test image conversion methods."""
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Test bytes conversion
    img_bytes = screen_capture.image_to_bytes(img, format="PNG")
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 0
    assert img_bytes.startswith(b'\x89PNG') # PNG magic number
    
    # Test base64 conversion
    b64 = screen_capture.image_to_base64(img, format="PNG")
    assert isinstance(b64, str)
    assert len(b64) > 0
    
    # helper validation
    decoded = base64.b64decode(b64)
    assert decoded == img_bytes

@patch('mss.mss')
def test_screen_capture_full_screen(mock_mss_cls, screen_capture):
    """Test full screen capture logic."""
    # Mock mss instance
    mock_sct = MagicMock()
    mock_mss_cls.return_value.__enter__.return_value = mock_sct
    
    # Mock monitors
    mock_sct.monitors = [
        {"top": 0, "left": 0, "width": 1920, "height": 1080}, # Monitor 0 (all)
        {"top": 0, "left": 0, "width": 1920, "height": 1080}  # Monitor 1
    ]
    
    # Mock grab return (screen shot object)
    mock_shot = MagicMock()
    mock_shot.size = (100, 100)
    mock_shot.bgra = b'\x00' * (100 * 100 * 4) # 4 bytes per pixel
    mock_shot.width = 100
    mock_shot.height = 100
    mock_sct.grab.return_value = mock_shot
    
    img = screen_capture.capture_full_screen()
    
    assert isinstance(img, Image.Image)
    mock_sct.grab.assert_called_with(mock_sct.monitors[0])

@patch('mss.mss')
def test_get_monitors(mock_mss_cls, screen_capture):
    """Test monitor retrieval."""
    mock_sct = MagicMock()
    mock_mss_cls.return_value.__enter__.return_value = mock_sct
    mock_sct.monitors = [{"id": 0}, {"id": 1}]
    
    monitors = screen_capture.get_monitors()
    assert len(monitors) == 2
    assert monitors == [{"id": 0}, {"id": 1}]


# --- HotkeyListener Tests ---

@pytest.fixture
def hotkey_listener():
    return HotkeyListener()

def test_parse_hotkey(hotkey_listener):
    """Test hotkey parsing."""
    # Test simple parse hook
    parsed = hotkey_listener.parse_hotkey("ctrl+s")
    assert parsed is not None
    
    # Test normalization fallback
    parsed_complex = hotkey_listener.parse_hotkey("ctrl+shift+alt+q")
    assert parsed_complex is not None

def test_register_unregister(hotkey_listener):
    """Test registration logic."""
    callback = MagicMock()
    
    # Register
    hotkey_listener.register("ctrl+s", callback)
    assert "ctrl+s" in hotkey_listener._hotkey_handlers
    
    # Unregister
    hotkey_listener.unregister("ctrl+s")
    assert "ctrl+s" not in hotkey_listener._hotkey_handlers

@patch('pynput.keyboard.Listener')
def test_listener_lifecycle(mock_listener_cls, hotkey_listener):
    """Test start/stop."""
    mock_listener = MagicMock()
    mock_listener_cls.return_value = mock_listener
    
    hotkey_listener.start()
    assert hotkey_listener.is_running()
    mock_listener.start.assert_called_once()
    
    hotkey_listener.stop()
    assert not hotkey_listener.is_running()
    mock_listener.stop.assert_called_once()


# --- MetadataCollector Tests ---

@pytest.fixture
def metadata_collector():
    return MetadataCollector()

def test_collect_structure(metadata_collector):
    """Test data structure validation."""
    meta = metadata_collector.collect()
    assert isinstance(meta, CaptureMetadata)
    assert isinstance(meta.timestamp, datetime)
    assert meta.platform in ["Windows", "Linux", "Darwin", "Java"]

@patch('showonce.capture.metadata.gw')
@patch('showonce.capture.metadata.pyautogui')
def test_collect_with_mocks(mock_pyautogui, mock_gw, metadata_collector):
    """Test collection with mocked dependencies."""
    # Mock window
    mock_window = MagicMock()
    mock_window.title = "Test Window"
    mock_gw.getActiveWindow.return_value = mock_window
    
    # Mock mouse
    mock_pyautogui.position.return_value = (100, 200)
    mock_pyautogui.size.return_value = (1920, 1080)
    
    meta = metadata_collector.collect()
    
    assert meta.window_title == "Test Window"
    assert meta.mouse_position == (100, 200)
    assert meta.screen_resolution == (1920, 1080)


# --- RecordingSession Tests ---

@pytest.fixture
def mock_components():
    with patch('showonce.capture.recorder.ScreenCapture') as MockSC, \
         patch('showonce.capture.recorder.HotkeyListener') as MockHL, \
         patch('showonce.capture.recorder.MetadataCollector') as MockMC, \
         patch('showonce.capture.recorder.Console') as MockConsole, \
         patch('showonce.capture.recorder.Prompt') as MockPrompt:
         
        # Setup specific mocks
        sc = MockSC.return_value
        # Mock image
        img = Image.new('RGB', (10, 10))
        sc.capture_full_screen.return_value = img
        sc.image_to_bytes.return_value = b'fake_image_bytes'
        
        mc = MockMC.return_value
        mc.collect.return_value = CaptureMetadata(
            timestamp=datetime.now(),
            active_window="Test",
            window_title="Test",
            application_name="TestApp",
            mouse_position=(0,0),
            screen_resolution=(1920,1080),
            platform="TestOS"
        )
        
        yield {
            'sc': sc,
            'hl': MockHL.return_value,
            'mc': mc,
            'console': MockConsole.return_value,
            'prompt': MockPrompt
        }

def test_recording_session_flow(mock_components, tmp_path):
    """Test full recording flow (simulated)."""
    # Override config to use tmp_path
    with patch('showonce.capture.recorder.get_config') as mock_conf:
        mock_conf.return_value.capture.capture_hotkey = "ctrl+s"
        mock_conf.return_value.capture.stop_hotkey = "ctrl+q"
        mock_conf.return_value.capture.screenshot_format = "png"
        mock_conf.return_value.paths.workflows_dir = tmp_path
        
        # Test Init
        session = RecordingSession("test_wf", "desc")
        assert session.workflow.name == "test_wf"
        
        # Test Capture Step
        # Mock user input
        mock_components['prompt'].ask.return_value = "User action description"
        
        session.capture_step()
        
        # Verify step added
        assert session.workflow.step_count == 1
        step = session.workflow.steps[0]
        assert step.description == "User action description"
        assert step.has_screenshot()
        
        # Verify calls
        mock_components['sc'].capture_full_screen.assert_called_once()
        mock_components['mc'].collect.assert_called_once()
        
        # Test Save
        session.save()
        
        # Verify file creation
        save_dir = tmp_path / "test_wf"
        assert save_dir.exists()
        assert (save_dir / "workflow.json").exists()
        assert (save_dir / "screenshots").exists()

