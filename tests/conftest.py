import pytest
from pathlib import Path
from unittest.mock import patch
import logging
from tests.mocks.caching_ollama_client import CachingOllamaClient

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
    logging.info(f"Created Ollama cache directory: {cache_dir}")
    return cache_dir

@pytest.fixture
def mock_ollama_client(ollama_cache_dir):
    """Create a mock Ollama client that caches responses"""
    with patch('plotomatic.assistant.base_assistant.ollama.Client') as mock_client:
        caching_client = CachingOllamaClient(ollama_cache_dir)
        mock_client.return_value = caching_client
        logging.info("Initialized mock Ollama client with caching")
        yield mock_client