from typing import Dict, Any, List, Optional
from datetime import datetime
import streamlit as st

class DebugLogger:
    """Handles debug logging for the application."""
    
    def __init__(self):
        """Initialize the debug logger."""
        if "debug_logs" not in st.session_state:
            st.session_state.debug_logs = []
    
    def log(self, 
            log_type: str, 
            data: Dict[str, Any], 
            context: Optional[str] = None) -> None:
        """
        Add a log entry with timestamp and optional context.
        
        Args:
            log_type: Type of log entry (e.g., 'agent_input', 'tool_call')
            data: Dictionary of data to log
            context: Optional context string for the log entry
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": log_type,
            **data
        }
        
        if context:
            log_entry["context"] = context
            
        st.session_state.debug_logs.append(log_entry)
    
    def log_agent_input(self, 
                       model: str, 
                       messages: List[Dict[str, Any]], 
                       context: Optional[str] = None) -> None:
        """Log an agent input event."""
        self.log("agent_input", {
            "model": model,
            "messages": messages
        }, context)
    
    def log_agent_output(self, 
                        model: str, 
                        response: Dict[str, Any], 
                        context: Optional[str] = None) -> None:
        """Log an agent output event."""
        self.log("agent_output", {
            "model": model,
            "response": response
        }, context)
    
    def log_tool_call(self, 
                      tool: str, 
                      arguments: Dict[str, Any]) -> None:
        """Log a tool call event."""
        self.log("tool_call", {
            "tool": tool,
            "arguments": arguments
        })
    
    def log_tool_output(self, 
                       tool: str, 
                       output: Any, 
                       error: Optional[str] = None) -> None:
        """Log a tool output event."""
        self.log("tool_output", {
            "tool": tool,
            "output": output,
            "error": error
        })
    
    def log_creative_input(self, 
                          model: str, 
                          messages: List[Dict[str, Any]]) -> None:
        """Log a creative model input event."""
        self.log("creative_input", {
            "model": model,
            "messages": messages
        })
    
    def log_creative_output(self, 
                           model: str, 
                           response: str) -> None:
        """Log a creative model output event."""
        self.log("creative_output", {
            "model": model,
            "response": response
        })
    
    def clear_logs(self) -> None:
        """Clear all debug logs."""
        st.session_state.debug_logs = []
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all debug logs."""
        return st.session_state.debug_logs
    
    def render_debug_tab(self) -> None:
        """Render the debug tab UI."""
        st.markdown("### Debug Logs")
        
        # Add buttons to clear logs and copy to clipboard
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Clear Logs", use_container_width=True):
                self.clear_logs()
                st.rerun()
        
        # Display logs in an expandable container with syntax highlighting
        if self.get_logs():
            for log in reversed(self.get_logs()):
                # Format the title based on log type
                title = f"{log['type']} - {log['timestamp']}"
                if log['type'] == "tool_call":
                    title = f"🔧 Tool Call: {log['tool']} - {log['timestamp']}"
                elif log['type'] == "tool_output":
                    title = f"📤 Tool Output: {log['tool']} - {log['timestamp']}"
                elif log['type'] == "agent_input":
                    title = f"🤖 Agent Input - {log['timestamp']}"
                    if "context" in log:
                        title += f" ({log['context']})"
                elif log['type'] == "agent_output":
                    title = f"💬 Agent Output - {log['timestamp']}"
                    if "context" in log:
                        title += f" ({log['context']})"
                elif log['type'] == "creative_input":
                    title = f"✍️ Creative Input - {log['timestamp']}"
                elif log['type'] == "creative_output":
                    title = f"📝 Creative Output - {log['timestamp']}"
                
                with st.expander(title, expanded=False):
                    st.code(str(log), language="json")
        else:
            st.info("No debug logs available yet. Start a conversation to see the interactions.") 