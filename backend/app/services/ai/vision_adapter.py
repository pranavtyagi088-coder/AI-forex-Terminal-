"""
Vision Adapter for AI Forex Terminal.
Handles image loading, base64 encoding, magic bytes validation, and payload security.
"""

import base64
import os
from typing import Optional, Tuple

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB Max


def validate_base64_image(image_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates base64 encoded image string for size and valid image headers (Magic Bytes).
    
    Returns:
        (is_valid: bool, mime_type: Optional[str], error_message: Optional[str])
    """
    if not image_input or not isinstance(image_input, str):
        return False, None, "Empty or invalid image string"

    clean_b64 = image_input
    if "," in image_input:
        clean_b64 = image_input.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(clean_b64, validate=True)
    except Exception:
        return False, None, "Invalid base64 payload"

    if len(raw_bytes) > MAX_IMAGE_SIZE_BYTES:
        size_mb = len(raw_bytes) / (1024 * 1024)
        return False, None, f"Image size ({size_mb:.2f}MB) exceeds max allowed 5MB"

    # Magic byte checks
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return True, "image/png", None
    elif raw_bytes.startswith(b"\xff\xd8\xff"):
        return True, "image/jpeg", None
    elif raw_bytes.startswith(b"RIFF") and len(raw_bytes) > 12 and raw_bytes[8:12] == b"WEBP":
        return True, "image/webp", None
    else:
        return False, None, "Unsupported image format. Allowed: PNG, JPEG, WEBP"


class VisionAdapter:
    """Helper adapter to sanitize and prepare chart images for AI models."""

    @staticmethod
    def encode_file_to_base64(file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Reads a local file, validates size, and returns (base64_str, mime_type)."""
        if not os.path.exists(file_path):
            return None, "File does not exist"

        file_size = os.path.getsize(file_path)
        if file_size > MAX_IMAGE_SIZE_BYTES:
            return None, "File exceeds 5MB size limit"

        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            encoded = base64.b64encode(raw_bytes).decode("utf-8")
            is_valid, mime_type, err = validate_base64_image(encoded)
            if not is_valid:
                return None, err
            return encoded, mime_type
        except Exception as e:
            return None, str(e)
