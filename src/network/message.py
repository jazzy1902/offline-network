import json
import logging
import socket
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("OfflineNetwork.Message")

class MessageType(Enum):
    """Types of messages that can be sent over the network."""
    CHAT = auto()
    FILE_TRANSFER_REQUEST = auto()
    FILE_TRANSFER_RESPONSE = auto()
    FILE_DATA = auto()
    FILE_COMPLETE = auto()
    DISCOVERY = auto()
    DISCOVERY_RESPONSE = auto()
    HEARTBEAT = auto()
    USER_LIST_REQUEST = auto()
    USER_LIST_RESPONSE = auto()

@dataclass
class Message:
    """Message object for network communication."""
    msg_type: MessageType
    sender_id: str
    sender_name: str
    content: Any
    msg_id: str = None
    timestamp: float = None
    
    def __post_init__(self):
        """Initialize message ID and timestamp if not provided."""
        if self.msg_id is None:
            self.msg_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_json(self) -> str:
        """Convert message to JSON string.
        
        Returns:
            str: JSON representation of the message
        """
        data = asdict(self)
        # Convert enum to string
        data['msg_type'] = self.msg_type.name
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create a Message object from JSON string.
        
        Args:
            json_str: JSON string representation of a message
            
        Returns:
            Message: Message object
        """
        data = json.loads(json_str)
        # Convert string to enum
        data['msg_type'] = MessageType[data['msg_type']]
        return cls(**data)

class MessageHandler:
    """Handle message encoding, decoding, and sending over sockets."""
    
    @staticmethod
    def send_message(sock: socket.socket, message: Message) -> bool:
        """Send a message over a socket.
        
        Args:
            sock: Socket to send the message over
            message: Message to send
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            # Convert message to JSON
            json_str = message.to_json()
            
            # Encode message length as 4-byte integer
            msg_len = len(json_str)
            length_bytes = msg_len.to_bytes(4, byteorder='big')
            
            # Send message length followed by message
            sock.sendall(length_bytes + json_str.encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    @staticmethod
    def receive_message(sock: socket.socket) -> Optional[Message]:
        """Receive a message from a socket.
        
        Args:
            sock: Socket to receive the message from
            
        Returns:
            Optional[Message]: Received message or None if error
        """
        try:
            # Receive message length (4 bytes)
            length_bytes = sock.recv(4)
            if not length_bytes or len(length_bytes) < 4:
                return None
            
            msg_len = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive message data
            data = b''
            remaining = msg_len
            while remaining > 0:
                chunk = sock.recv(min(4096, remaining))
                if not chunk:
                    return None
                data += chunk
                remaining -= len(chunk)
            
            # Parse message
            json_str = data.decode('utf-8')
            return Message.from_json(json_str)
            
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

class ChatMessage:
    """Helper for creating chat messages."""
    
    @staticmethod
    def create(sender_id: str, sender_name: str, text: str) -> Message:
        """Create a chat message.
        
        Args:
            sender_id: ID of the sender
            sender_name: Name of the sender
            text: Message text
            
        Returns:
            Message: Chat message
        """
        return Message(
            msg_type=MessageType.CHAT,
            sender_id=sender_id,
            sender_name=sender_name,
            content=text
        )

class FileTransfer:
    """Helper for file transfer messages."""
    
    @staticmethod
    def request(sender_id: str, sender_name: str, 
                filename: str, file_size: int, file_id: str = None) -> Message:
        """Create a file transfer request message.
        
        Args:
            sender_id: ID of the sender
            sender_name: Name of the sender
            filename: Name of the file
            file_size: Size of the file in bytes
            file_id: Optional ID for the file
            
        Returns:
            Message: File transfer request message
        """
        if file_id is None:
            file_id = str(uuid.uuid4())
            
        return Message(
            msg_type=MessageType.FILE_TRANSFER_REQUEST,
            sender_id=sender_id,
            sender_name=sender_name,
            content={
                'filename': filename,
                'file_size': file_size,
                'file_id': file_id
            }
        )
    
    @staticmethod
    def response(sender_id: str, sender_name: str, 
                file_id: str, accepted: bool) -> Message:
        """Create a file transfer response message.
        
        Args:
            sender_id: ID of the sender
            sender_name: Name of the sender
            file_id: ID of the file
            accepted: Whether the transfer was accepted
            
        Returns:
            Message: File transfer response message
        """
        return Message(
            msg_type=MessageType.FILE_TRANSFER_RESPONSE,
            sender_id=sender_id,
            sender_name=sender_name,
            content={
                'file_id': file_id,
                'accepted': accepted
            }
        )
    
    @staticmethod
    def data(sender_id: str, sender_name: str, 
            file_id: str, chunk_number: int, 
            total_chunks: int, data: bytes) -> Message:
        """Create a file data message.
        
        Args:
            sender_id: ID of the sender
            sender_name: Name of the sender
            file_id: ID of the file
            chunk_number: Chunk number
            total_chunks: Total number of chunks
            data: Chunk data (base64 encoded)
            
        Returns:
            Message: File data message
        """
        import base64
        encoded_data = base64.b64encode(data).decode('ascii')
        
        return Message(
            msg_type=MessageType.FILE_DATA,
            sender_id=sender_id,
            sender_name=sender_name,
            content={
                'file_id': file_id,
                'chunk_number': chunk_number,
                'total_chunks': total_chunks,
                'data': encoded_data
            }
        )
    
    @staticmethod
    def complete(sender_id: str, sender_name: str, 
                file_id: str, success: bool) -> Message:
        """Create a file transfer complete message.
        
        Args:
            sender_id: ID of the sender
            sender_name: Name of the sender
            file_id: ID of the file
            success: Whether the transfer was successful
            
        Returns:
            Message: File transfer complete message
        """
        return Message(
            msg_type=MessageType.FILE_COMPLETE,
            sender_id=sender_id,
            sender_name=sender_name,
            content={
                'file_id': file_id,
                'success': success
            }
        ) 