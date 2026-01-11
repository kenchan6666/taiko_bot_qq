"""
LLM service for OpenRouter API integration.

This module provides the OpenRouter API client for invoking gpt-4o
for AI responses with multi-modal support.

Per FR-006: Support multi-modal image processing.
Per FR-009: Gracefully degrade when external services are unavailable.
"""

import base64
import json
from typing import Optional

import httpx
import structlog

from src.config import settings

# Performance optimization: Enable HTTP/2 for faster connections (if supported)
# httpx.AsyncClient will automatically use HTTP/2 if the server supports it

logger = structlog.get_logger()


class LLMService:
    """
    OpenRouter API client for gpt-4o.

    Handles API calls to OpenRouter for LLM responses with support for
    text and multi-modal (image) inputs.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize LLM service.

        Args:
            api_key: OpenRouter API key (defaults to settings.openrouter_api_key).
        """
        self.api_key = api_key or settings.openrouter_api_key
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable."
            )

        # OpenRouter API endpoint
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        # Model: Configurable via OPENROUTER_MODEL environment variable
        # Default: anthropic/claude-3.5-sonnet (recommended, most human-like, better emotion understanding)
        # Alternative: openai/gpt-4o (fast, multimodal, but less human-like)
        # Alternative: xai/grok-2 (witty and lively, but higher hallucination rate ~4.8%)
        # 
        # Switch model by setting OPENROUTER_MODEL in .env file or environment variable
        self.model = settings.openrouter_model if hasattr(settings, 'openrouter_model') else "anthropic/claude-3.5-sonnet"

        # HTTP client with optimized timeout and connection pooling
        # Performance optimization: Configure connection limits and timeouts for better performance
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,  # Connection timeout: 10s (faster connection establishment)
                read=25.0,     # Read timeout: 25s (reduced from 30s for faster failure detection)
                write=10.0,    # Write timeout: 10s
                pool=5.0,      # Pool timeout: 5s (waiting for connection from pool)
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,  # Keep connections alive for reuse (performance optimization)
                max_connections=20,            # Max concurrent connections
                keepalive_expiry=30.0,         # Keep connections alive for 30s
            ),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate_response(
        self,
        prompt: str,
        images: Optional[list[str]] = None,
        temperature: float = 0.8,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate LLM response using OpenRouter (Claude 3.5 Sonnet by default).

        Supports both text-only and multi-modal (text + images) requests.

        Per FR-006: Support multi-modal image processing.
        Per FR-009: Gracefully degrade when external services are unavailable.

        Args:
            prompt: Text prompt for LLM.
            images: Optional list of base64-encoded images (for multi-modal).
            temperature: Sampling temperature (0.0-2.0, default: 0.8).
                - 0.0-0.5: More focused, consistent (may be repetitive)
                - 0.6-0.8: Balanced creativity and consistency (recommended for Claude)
                - 0.9-1.5: More creative/diverse (good for friends/regular users)
                - 1.5-2.0: Very random (not recommended)
                Claude models are more sensitive to temperature than GPT-4o, so slightly higher values (0.8-0.95) work better.
            max_tokens: Maximum tokens in response (default: 500).

        Returns:
            Generated response text from LLM.

        Raises:
            httpx.HTTPError: If API request fails.
            ValueError: If API response is invalid.

        Example:
            >>> service = LLMService(api_key="sk-...")
            >>> response = await service.generate_response(
            ...     prompt="Hello, I'm Mika!",
            ...     temperature=0.8
            ... )
            >>> print(response)
            "Hello! Nice to meet you! 🥁"
        """
        # Build messages array
        messages = []

        # User message with optional images
        user_message: dict[str, any] = {
            "role": "user",
            "content": [],
        }

        # Add text content
        user_message["content"].append(
            {
                "type": "text",
                "text": prompt,
            }
        )

        # Add images if provided (multi-modal support)
        # Per FR-006: Support image processing
        # Note: Images are already validated in step1.py (size and format)
        if images:
            for image_base64 in images:
                # Detect image format for proper MIME type
                # OpenRouter/gpt-4o supports: image/jpeg, image/png, image/webp
                image_format = _detect_image_mime_type(image_base64)
                user_message["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_format};base64,{image_base64}",
                        },
                    }
                )

        messages.append(user_message)

        # Build request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            # Log API request (without sensitive data)
            logger.info(
                "llm_api_request_starting",
                model=self.model,
                has_images=bool(images),
                prompt_length=len(prompt),
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Make API request
            response = await self.client.post(
                self.api_url,
                json=payload,
            )

            # Log response status
            logger.debug(
                "llm_api_response_received",
                status_code=response.status_code,
                response_length=len(response.content) if response.content else 0,
            )

            response.raise_for_status()

            # Parse response
            response_data = response.json()

            # Extract generated text
            if "choices" not in response_data or not response_data["choices"]:
                raise ValueError("Invalid API response: no choices found")

            choice = response_data["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                raise ValueError("Invalid API response: no content found")

            generated_text = choice["message"]["content"]

            # Log successful response
            logger.info(
                "llm_api_request_success",
                response_length=len(generated_text),
                response_preview=generated_text[:100],
                usage=response_data.get("usage", {}),
            )

            return generated_text.strip()

        except httpx.HTTPStatusError as e:
            # HTTP error with status code (4xx, 5xx)
            error_detail = None
            try:
                error_detail = e.response.json() if e.response.content else None
            except Exception:
                error_detail = e.response.text[:500] if e.response.text else None

            logger.error(
                "llm_api_request_failed",
                status_code=e.response.status_code,
                error=str(e),
                error_detail=error_detail,
                model=self.model,
            )
            # Per FR-009: Graceful degradation
            # Log error and raise for caller to handle
            raise RuntimeError(f"OpenRouter API request failed: {e}") from e

        except httpx.HTTPError as e:
            # Network/connection errors
            logger.error(
                "llm_api_request_network_error",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model,
            )
            # Per FR-009: Graceful degradation
            # Log error and raise for caller to handle
            raise RuntimeError(f"OpenRouter API request failed: {e}") from e

        except ValueError as e:
            # Response parsing errors
            logger.error(
                "llm_api_response_parse_error",
                error=str(e),
                model=self.model,
            )
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


def _detect_image_mime_type(image_base64: str) -> str:
    """
    Detect image MIME type from base64-encoded image data.

    Per FR-006: Support JPEG, PNG, WebP formats.
    OpenRouter/gpt-4o requires proper MIME types: image/jpeg, image/png, image/webp.

    Args:
        image_base64: Base64-encoded image string.

    Returns:
        MIME type string (e.g., "image/jpeg", "image/png", "image/webp").
        Defaults to "image/jpeg" if format cannot be detected.

    Example:
        >>> jpeg_base64 = "/9j/4AAQSkZJRg..."
        >>> _detect_image_mime_type(jpeg_base64)
        'image/jpeg'
    """
    try:
        # Decode base64 to get binary data
        image_data = base64.b64decode(image_base64, validate=True)

        if not image_data or len(image_data) < 4:
            return "image/jpeg"  # Default fallback

        # Check JPEG: Starts with FF D8 FF
        if image_data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"

        # Check PNG: Starts with 89 50 4E 47
        if image_data[:4] == b"\x89PNG":
            return "image/png"

        # Check WebP: Starts with RIFF...WEBP
        if len(image_data) >= 12:
            if image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
                return "image/webp"

        # Format not recognized - default to JPEG
        return "image/jpeg"

    except Exception:
        # Decoding failed - default to JPEG
        return "image/jpeg"


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get global LLM service instance.

    Creates instance on first call if not already initialized.

    Returns:
        Global LLMService instance.

    Raises:
        ValueError: If OpenRouter API key is not configured.
    """
    global _llm_service

    if _llm_service is None:
        _llm_service = LLMService()

    return _llm_service


async def close_llm_service() -> None:
    """Close global LLM service instance."""
    global _llm_service

    if _llm_service:
        await _llm_service.close()
        _llm_service = None
