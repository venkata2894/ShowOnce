"""Screenshot capture utilities for ShowOnce."""
import mss
import mss.tools
from PIL import Image
from typing import Optional, Tuple, List, Dict, Any
import base64
import io
from datetime import datetime
from showonce.utils.logger import log

class ScreenCapture:
    """Handle screenshot capture operations."""

    def __init__(self):
        """Initialize screen capture."""
        log.debug("Initializing ScreenCapture")

    def _to_image(self, sct_img: mss.screenshot.ScreenShot) -> Image.Image:
        """
        Convert mss ScreenShot to PIL Image.
        
        Args:
            sct_img: The mss screenshot object.
            
        Returns:
            PIL Image object.
        """
        # Create PIL Image from bytes
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Add metadata
        timestamp = datetime.now().isoformat()
        img.info['timestamp'] = timestamp
        
        return img

    def capture_full_screen(self) -> Image.Image:
        """
        Capture the entire screen (all monitors).
        
        Returns:
            PIL Image of the full screen capture.
        """
        try:
            with mss.mss() as sct:
                # Monitor 0 is the "All in One" monitor
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                log.debug(f"Captured full screen: {sct_img.width}x{sct_img.height}")
                return self._to_image(sct_img)
        except Exception as e:
            log.error(f"Failed to capture full screen: {str(e)}")
            raise

    def capture_monitor(self, monitor: int = 1) -> Image.Image:
        """
        Capture a specific monitor.
        
        Args:
            monitor: The monitor index (1-based). Default is 1 (primary).
            
        Returns:
            PIL Image of the monitor capture.
            
        Raises:
            ValueError: If monitor index is invalid.
        """
        try:
            with mss.mss() as sct:
                if monitor >= len(sct.monitors):
                    raise ValueError(f"Monitor {monitor} not found. Available: {len(sct.monitors)-1}")
                
                mon_dict = sct.monitors[monitor]
                sct_img = sct.grab(mon_dict)
                log.debug(f"Captured monitor {monitor}: {sct_img.width}x{sct_img.height}")
                return self._to_image(sct_img)
        except Exception as e:
            log.error(f"Failed to capture monitor {monitor}: {str(e)}")
            raise

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """
        Capture a specific region.
        
        Args:
            x: Top-left x coordinate.
            y: Top-left y coordinate.
            width: Width of region.
            height: Height of region.
            
        Returns:
            PIL Image of the region.
        """
        region = {"top": y, "left": x, "width": width, "height": height}
        try:
            with mss.mss() as sct:
                sct_img = sct.grab(region)
                log.debug(f"Captured region: {region}")
                return self._to_image(sct_img)
        except Exception as e:
            log.error(f"Failed to capture region {region}: {str(e)}")
            raise

    def get_monitors(self) -> List[Dict[str, Any]]:
        """
        Get list of available monitors.
        
        Returns:
            List of dictionaries containing monitor details (left, top, width, height).
            Index 0 is the combined virtual monitor.
        """
        with mss.mss() as sct:
            return list(sct.monitors)

    def image_to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """
        Convert PIL Image to bytes.
        
        Args:
            image: PIL Image object.
            format: Image format (default "PNG").
            
        Returns:
            Bytes containing the image data.
        """
        with io.BytesIO() as bio:
            image.save(bio, format=format)
            return bio.getvalue()

    def image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object.
            format: Image format (default "PNG").
            
        Returns:
            Base64 encoded string of the image.
        """
        img_bytes = self.image_to_bytes(image, format)
        return base64.b64encode(img_bytes).decode('utf-8')

    def get_screen_resolution(self) -> Tuple[int, int]:
        """
        Get primary screen resolution.
        
        Returns:
            Tuple of (width, height) for the primary monitor (index 1).
        """
        with mss.mss() as sct:
            if len(sct.monitors) > 1:
                primary = sct.monitors[1]
                return primary["width"], primary["height"]
            else:
                # Fallback if somehow only monitor 0 exists (headless?)
                combined = sct.monitors[0]
                return combined["width"], combined["height"]
