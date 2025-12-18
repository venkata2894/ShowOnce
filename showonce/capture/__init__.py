"""
Capture module for ShowOnce.

This module handles:
- Screenshot capture (ScreenCapture)
- Hotkey listening (HotkeyListener)
- System metadata collection (MetadataCollector)
- Session recording orchestration (RecordingSession)
"""

from showonce.capture.screenshot import ScreenCapture
from showonce.capture.hotkeys import HotkeyListener
from showonce.capture.metadata import MetadataCollector, CaptureMetadata
from showonce.capture.recorder import RecordingSession, record_workflow

__all__ = [
    "ScreenCapture",
    "HotkeyListener",
    "MetadataCollector",
    "CaptureMetadata",
    "RecordingSession",
    "record_workflow",
]
