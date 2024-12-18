from plotomatic.config import settings
from typing import Iterator, Optional, AsyncIterator
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

class LoggingTransport(httpx.AsyncHTTPTransport):
    def __init__(self, *args, colorize: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.colorize = colorize

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle async request while logging details, preserving streaming functionality."""
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
        response = await super().handle_async_request(request)
        
        # Log response headers immediately
        logger.debug(f"Response: {response.status_code}")
        logger.debug(f"Headers: {response.headers}")

        logger.debug("\n\n\n\n")

        # Create a wrapper response that will log the body after it's consumed
        return LoggingResponse(response, request, start_time, self.colorize)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle synchronous request (delegates to async version)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.handle_async_request(request))

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

    async def aread(self) -> bytes:
        """Async read of response content."""
        if self._content is None:
            self._content = await self._original_response.aread()
            if not self._content_logged:
                try:
                    content_str = self._content.decode('utf-8', errors='replace')
                    try:
                        repaired_json = repair_json(content_str)
                        formatted_json = self._format_json(repaired_json)
                        logger.debug(f"Response Body: {formatted_json}")
                    except Exception:
                        logger.debug(f"Response Body: {content_str}")
                except Exception as e:
                    logger.error(f"Failed to decode response body: {e}")
                self._log_end_request()
        return self._content

    @property
    def content(self) -> bytes:
        """Sync read of response content."""
        if self._content is None:
            import asyncio
            loop = asyncio.get_event_loop()
            self._content = loop.run_until_complete(self.aread())
        return self._content

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        """Async iteration over response bytes."""
        if self._content is not None:
            yield self._content
            return

        chunks = []
        async for chunk in self._original_response.aiter_bytes():
            chunks.append(chunk)
            yield chunk
        
        if not self._content_logged:
            self._content = b''.join(chunks)
            try:
                content_str = self._content.decode('utf-8', errors='replace')
                try:
                    repaired_json = repair_json(content_str)
                    formatted_json = self._format_json(repaired_json)
                    logger.debug(f"Response Body (aiter_bytes): {formatted_json}")
                except Exception:
                    logger.debug(f"Response Body (aiter_bytes): {content_str}")
            except Exception as e:
                logger.error(f"Failed to decode response body: {e}")
            self._log_end_request()

    async def aiter_text(self) -> AsyncIterator[str]:
        """Async iteration over response text."""
        if self._content is not None:
            yield self._content.decode('utf-8', errors='replace')
            return

        message_contents = []
        async for chunk in self._original_response.aiter_text():
            try:
                chunk_data = json.loads(chunk)
                content = chunk_data.get('message', {}).get('content', '')
                message_contents.append(content)
                yield chunk
            except json.JSONDecodeError:
                message_contents.append(chunk)
                yield chunk
        
        if not self._content_logged:
            content = ''.join(message_contents)
            logger.debug(f"Response Body (aiter_text): {content}")
            self._content = content.encode('utf-8')
            self._log_end_request()

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

    async def aclose(self):
        """Asynchronously close the original response."""
        await self._original_response.aclose()

    def close(self):
        """Synchronously close the original response."""
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.aclose())

    def iter_bytes(self, chunk_size: Optional[int] = None) -> Iterator[bytes]:
        """Sync iteration over response bytes."""
        if self._content is None:
            self._content = b''  # Initialize empty content if None
            import asyncio
            loop = asyncio.get_event_loop()
            async def collect_bytes():
                async for chunk in self._original_response.aiter_bytes():
                    self._content += chunk
                return self._content
            self._content = loop.run_until_complete(collect_bytes())
        
        if chunk_size is None:
            chunk_size = len(self._content)
            
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size] 