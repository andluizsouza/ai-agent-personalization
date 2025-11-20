"""
Chat Session Manager

Manages conversational state for the CLI interface.
Handles message history, context persistence, and session lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Message:
    """Represents a single message in the conversation."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class ChatSession:
    """
    Manages a conversational session with the planner agent.

    Features:
    - Message history tracking
    - Context persistence
    - Session metadata
    - Clear/reset functionality
    """

    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize chat session.

        Args:
            client_id: Optional client ID for the session
        """
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.client_id = client_id
        self.messages: List[Message] = []
        self.created_at = datetime.now()
        self.metadata: Dict = {}

    def add_message(self, role: str, content: str) -> Message:
        """
        Add a message to the session.

        Args:
            role: 'user' or 'assistant'
            content: Message content

        Returns:
            Created message
        """
        message = Message(role=role, content=content)
        self.messages.append(message)
        return message

    def get_history(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get message history.

        Args:
            limit: Maximum number of messages to return (most recent)

        Returns:
            List of messages
        """
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear_history(self):
        """Clear all messages from the session."""
        self.messages.clear()

    def get_context_for_agent(self) -> List[Dict]:
        """
        Get conversation history formatted for the agent.

        Returns:
            List of message dictionaries for LangChain
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def set_client_id(self, client_id: str):
        """Set the client ID for this session."""
        self.client_id = client_id

    def get_stats(self) -> Dict:
        """
        Get session statistics.

        Returns:
            Dictionary with session stats
        """
        user_messages = sum(1 for m in self.messages if m.role == "user")
        assistant_messages = sum(1 for m in self.messages if m.role == "assistant")

        duration = datetime.now() - self.created_at

        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "duration_seconds": duration.total_seconds(),
            "total_messages": len(self.messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "created_at": self.created_at.isoformat(),
        }
