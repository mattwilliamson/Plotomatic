from functools import wraps
from typing import Callable, Dict
from .tool_metadata import ToolMetadata

class ToolManager:
    """Manages tool metadata and registration for assistant tools."""
    
    def __init__(self):
        self.tool_metadata: Dict[str, ToolMetadata] = {}

    def tool(self, 
             emoji: str = "🔧", 
             description: str = "",
             show_output: bool = True) -> Callable:
        """
        Decorator to store metadata for assistant tools.
        
        Args:
            emoji (str): Emoji icon for the tool
            description (str): Tool description for documentation
            show_output (bool): Whether to show the tool output in chat
        """
        def decorator(func: Callable) -> Callable:
            func_name = func.__name__
            
            # Store metadata
            self.tool_metadata[func_name] = ToolMetadata(
                name=func_name,
                emoji=emoji,
                description=description or func.__doc__,
                show_output=show_output
            )
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
                
            return wrapper
            
        return decorator

    def get_metadata(self, name: str) -> ToolMetadata:
        """Get metadata for a tool."""
        return self.tool_metadata.get(name, ToolMetadata(name=name))