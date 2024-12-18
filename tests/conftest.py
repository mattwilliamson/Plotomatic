import pytest
import hashlib
from pathlib import Path
import httpx
import json
from typing import Dict, Any

class CachingTransport(httpx.HTTPTransport):
    """HTTP transport that caches responses for deterministic testing"""
    def __init__(self, cache_dir: Path):
        super().__init__()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def _create_cache_key(self, request: httpx.Request) -> str:
        """Create a unique cache key from request details"""
        # Parse request body to get stable representation
        try:
            body = json.loads(request.content)
            # Sort any lists in messages to ensure stable cache key
            if 'messages' in body:
                for msg in body['messages']:
                    if 'content' in msg and isinstance(msg['content'], list):
                        msg['content'].sort()
            # Convert back to string for hashing
            content = json.dumps(body, sort_keys=True)
        except (json.JSONDecodeError, AttributeError):
            content = request.content.decode() if request.content else ""

        # Create hash from request details
        key_parts = [
            request.method,
            str(request.url),
            content
        ]
        return hashlib.md5("".join(key_parts).encode()).hexdigest()

    def _save_response(self, cache_file: Path, response_data: Dict[str, Any]):
        """Save response data to cache file"""
        with open(cache_file, 'w') as f:
            json.dump(response_data, f, indent=2)

    def _load_response(self, cache_file: Path) -> Dict[str, Any]:
        """Load response data from cache file"""
        with open(cache_file, 'r') as f:
            return json.load(f)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request with caching"""
        cache_key = self._create_cache_key(request)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check cache first
        if cache_file.exists():
            cached_data = self._load_response(cache_file)
            return httpx.Response(
                status_code=200,
                content=json.dumps(cached_data).encode(),
                headers={"content-type": "application/json"}
            )

        # If not in cache, make real request
        response = super().handle_request(request)
        
        # Cache the response
        try:
            response_data = json.loads(response.content)
            self._save_response(cache_file, response_data)
        except json.JSONDecodeError:
            # If response isn't JSON, store raw content
            self._save_response(cache_file, {
                "raw_content": response.content.decode()
            })

        return response

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory for testing"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir

@pytest.fixture
def ollama_cache_dir(tmp_path):
    """Create a temporary directory for Ollama response caching"""
    cache_dir = tmp_path / "ollama_cache"
    cache_dir.mkdir()
    return cache_dir 