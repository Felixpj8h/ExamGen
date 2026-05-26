"""Shared Gemini client helpers.

The concrete client helpers currently live with the question extractor for
backward compatibility. New code should import them from here.
"""

from exam_parser.ai.question_extractor import (  # noqa: F401
    GeminiExtractionError,
    _create_gemini_client,
    _generate_content_config,
    _parse_gemini_json_response,
)

__all__ = [
    "GeminiExtractionError",
    "_create_gemini_client",
    "_generate_content_config",
    "_parse_gemini_json_response",
]
