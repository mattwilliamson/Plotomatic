"""Configuration settings for Plotomatic."""
import os
from pathlib import Path
import yaml
from typing import Dict, Any

# Base paths
ROOT_DIR = Path(__file__).parent.parent.parent.parent
STORY_DIR = Path(os.getenv("STORY_DIR", ROOT_DIR / "stories"))

# Debug mode
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# CrewAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Ensure directories exist
STORY_DIR.mkdir(parents=True, exist_ok=True) 

def load_config(config_path: str | Path) -> Dict[Any, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing the configuration
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config