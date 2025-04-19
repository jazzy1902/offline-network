"""Message module for Bluetooth chat application."""

import time
from typing import Optional

from .config import ENCODING, MSG_PREFIX, NAME_PREFIX, FILE_PREFIX, DISCONNECT_MSG


class Message:
    """Represents a message that can be sent or received."""
    
    # Message types
    TYPE_TEXT = "text"
    TYPE_NAME = "name"
    TYPE_FILE = "file"
    TYPE_DISCONNECT = "disconnect"
    
    def __init__(self, message_type: str, content: str = ""):
        """Initialize a new message.
        
        Args:
            message_type: Type of message
            content: Message content
        """
        self.type = message_type
        self.content = content
        self.timestamp = time.time()
        self.sender = None  # Set by the receiver
    
    def encode(self) -> bytes:
        """Encode the message for transmission.
        
        Returns:
            bytes: Encoded message
        """
        # Format the message according to type
        if self.type == self.TYPE_TEXT:
            data = f"{MSG_PREFIX}{self.content}"
        elif self.type == self.TYPE_NAME:
            data = f"{NAME_PREFIX}{self.content}"
        elif self.type == self.TYPE_FILE:
            data = f"{FILE_PREFIX}{self.content}"
        elif self.type == self.TYPE_DISCONNECT:
            data = DISCONNECT_MSG
        else:
            # Unknown type, use text format
            data = f"{MSG_PREFIX}{self.content}"
        
        # Encode to bytes
        return data.encode(ENCODING)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Message':
        """Create a Message object from received data.
        
        Args:
            data: Received bytes
            
        Returns:
            Message: Parsed message object
        """
        # Decode from bytes
        text = data.decode(ENCODING)
        
        # Parse according to format
        if text.startswith(MSG_PREFIX):
            return cls(cls.TYPE_TEXT, text[len(MSG_PREFIX):])
        elif text.startswith(NAME_PREFIX):
            return cls(cls.TYPE_NAME, text[len(NAME_PREFIX):])
        elif text.startswith(FILE_PREFIX):
            return cls(cls.TYPE_FILE, text[len(FILE_PREFIX):])
        elif text == DISCONNECT_MSG:
            return cls(cls.TYPE_DISCONNECT)
        else:
            # Unknown format, treat as text
            return cls(cls.TYPE_TEXT, text)
    
    def __str__(self) -> str:
        """Get string representation of the message.
        
        Returns:
            str: String representation
        """
        return f"Message({self.type}, {self.content})" 