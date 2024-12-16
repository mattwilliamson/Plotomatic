from functools import wraps
from typing import Callable, List, Optional, Dict, Any
import inspect

class ToolManager:
    """Manages function decorators and registries for AI assistant tools."""
    
    def __init__(self):
        self.available_functions: Dict[str, Callable] = {}
        self.tool_emojis: Dict[str, str] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}

    def tool(self, 
             emoji: str = "🔧", 
             aliases: Optional[List[str]] = None,
             show_output: bool = True,
             description: Optional[str] = None,
             pretty_name: Optional[str] = None) -> Callable:
        """
        Decorator to register a function as an AI assistant tool.
        
        Args:
            emoji (str): Emoji icon for the tool
            aliases (List[str], optional): Alternative names for the tool
            show_output (bool): Whether to show the tool output in chat
            description (str, optional): Tool description for documentation
            pretty_name (str, optional): Human-readable name for display purposes
        """
        def decorator(func: Callable) -> Callable:
            # Get function signature for documentation
            sig = inspect.signature(func)
            
            # Register the main function name
            func_name = func.__name__
            self.available_functions[func_name] = func
            self.tool_emojis[func_name] = emoji
            
            # Store metadata
            self.tool_metadata[func_name] = {
                'emoji': emoji,
                'show_output': show_output,
                'description': description or func.__doc__,
                'signature': str(sig),
                'aliases': aliases or [],
                'pretty_name': pretty_name or func_name.replace('_', ' ').title()
            }
            
            # Register aliases if provided
            if aliases:
                for alias in aliases:
                    self.available_functions[alias] = func
                    self.tool_emojis[alias] = emoji
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
                
            return wrapper
            
        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool function by name."""
        return self.available_functions.get(name)
    
    def get_emoji(self, name: str) -> str:
        """Get the emoji for a tool."""
        return self.tool_emojis.get(name, "🔧")
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a tool."""
        return self.tool_metadata.get(name)
    
    def should_show_output(self, name: str) -> bool:
        """Check if tool output should be shown in chat."""
        metadata = self.get_metadata(name)
        return metadata.get('show_output', True) if metadata else True 