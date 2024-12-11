from plotomatic.config import settings
from typing import Iterator, Optional
import httpx
from streamlit.logger import get_logger
from json_repair import repair_json
import json
import time
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import JsonLexer
import logging

logger = get_logger('plotomatic')

if settings.DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.info("Debug mode enabled")
    logger.debug("Debug mode enabled")
else:
    logger.setLevel(logging.INFO)

class LoggingTransport(httpx.HTTPTransport):
    def __init__(self, *args, colorize: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.colorize = colorize

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request while logging details, preserving streaming functionality."""
        # Start timing
        start_time = time.time()
        
        # Log request details
        logger.debug("\n\n\n\n")
        logger.debug("#" * 40 + " START OLLAMA REQUEST " + "#" * 40)
        logger.debug(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {request.headers}")
        
        if request.content:
            try:
                # Try to parse and format JSON content
                content_str = request.content.decode('utf-8')
                repaired_json = repair_json(content_str)
                formatted_json = json.dumps(json.loads(repaired_json), indent=2)
                if self.colorize:
                    formatted_json = highlight(
                        formatted_json,
                        JsonLexer(),
                        Terminal256Formatter(style='monokai')
                    )
                logger.debug(f"Body: {formatted_json}")
            except Exception:
                # Fallback to raw content if not valid JSON
                logger.debug(f"Body: {request.content}")
        
        # Get the original response
        response = super().handle_request(request)
        
        # Log response headers immediately
        logger.debug(f"Response: {response.status_code}")
        logger.debug(f"Headers: {response.headers}")

        logger.debug("\n\n\n\n")

        # Create a wrapper response that will log the body after it's consumed
        return LoggingResponse(response, request, start_time, self.colorize)

class LoggingResponse(httpx.Response):
    def __init__(self, original_response: httpx.Response, request: httpx.Request, start_time: float, colorize: bool = True):
        self._original_response = original_response
        self._content: Optional[bytes] = None
        self._content_logged = False
        self._start_time = start_time
        self._colorize = colorize
        
        # Initialize with the original response's attributes
        super().__init__(
            status_code=original_response.status_code,
            headers=original_response.headers,
            content=None,  # We'll handle content separately
            request=request
        )

    def _format_json(self, json_str: str) -> str:
        """Helper method to format JSON with optional coloring"""
        formatted_json = json.dumps(json.loads(json_str), indent=2)
        if self._colorize:
            return highlight(
                formatted_json,
                JsonLexer(),
                Terminal256Formatter(style='monokai')
            )
        return formatted_json

    def _log_end_request(self):
        """Helper method to log the end of request with elapsed time"""
        if not self._content_logged:
            elapsed_time = time.time() - self._start_time
            logger.debug(f"Time elapsed: {elapsed_time:.2f} seconds")
            logger.debug("#" * 40 + " END OLLAMA REQUEST " + "#" * 40 + "\n\n\n\n")
            self._content_logged = True

    @property
    def content(self) -> bytes:
        """Override content property to ensure proper logging."""
        if self._content is None:
            self._content = self._original_response.read()
            if not self._content_logged:
                try:
                    content_str = self._content.decode('utf-8', errors='replace')
                    try:
                        # Try to parse and format JSON content
                        repaired_json = repair_json(content_str)
                        formatted_json = self._format_json(repaired_json)
                        logger.debug(f"Response Body: {formatted_json}")
                    except Exception:
                        # Fallback to raw content if not valid JSON
                        logger.debug(f"Response Body: {content_str}")
                except Exception as e:
                    logger.error(f"Failed to decode response body: {e}")
                self._log_end_request()
        return self._content

    def iter_bytes(self) -> Iterator[bytes]:
        """Iterate over response bytes while collecting for logging."""
        if self._content is not None:
            yield self._content
            return

        chunks = []
        for chunk in self._original_response.iter_bytes():
            chunks.append(chunk)
            yield chunk
        
        if not self._content_logged:
            self._content = b''.join(chunks)
            try:
                content_str = self._content.decode('utf-8', errors='replace')
                try:
                    # Try to parse and format JSON content
                    repaired_json = repair_json(content_str)
                    formatted_json = json.dumps(json.loads(repaired_json), indent=2)
                    if self._colorize:
                        formatted_json = highlight(
                            formatted_json,
                            JsonLexer(),
                            Terminal256Formatter(style='monokai')
                        )
                    logger.debug(f"Response Body (iter_bytes): {formatted_json}")
                except Exception:
                    # Fallback to raw content if not valid JSON
                    logger.debug(f"Response Body (iter_bytes): {content_str}")
            except Exception as e:
                logger.error(f"Failed to decode response body: {e}")
            self._log_end_request()

    def iter_text(self) -> Iterator[str]:
        """Iterate over response text while collecting for logging."""
        if self._content is not None:
            yield self._content.decode('utf-8', errors='replace')
            return

        message_contents = []
        for chunk in self._original_response.iter_text():
            try:
                # Parse the JSON chunk
                chunk_data = json.loads(chunk)
                # Extract the message content
                content = chunk_data.get('message', {}).get('content', '')
                message_contents.append(content)
                # Pass the original chunk to the caller
                yield chunk
            except json.JSONDecodeError:
                # If chunk isn't valid JSON, just pass it through
                message_contents.append(chunk)
                yield chunk
        
        if not self._content_logged:
            # Join all message contents for logging
            content = ''.join(message_contents)
            logger.debug(f"Response Body (iter_text): {content}")
            
            # Store the original concatenated chunks
            self._content = ''.join(message_contents).encode('utf-8')
            self._log_end_request()

    def close(self):
        """Close the original response."""
        self._original_response.close() 