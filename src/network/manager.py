import logging
import socket
import threading
import time
import uuid
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.network.message import (ChatMessage, FileTransfer, Message,
                               MessageHandler, MessageType)
from src.network.wifi_direct import WiFiDirect

logger = logging.getLogger("OfflineNetwork.NetworkManager")

class NetworkManager:
    """Manager for WiFi Direct network connections and message handling."""
    
    def __init__(self, user_id: str = None, user_name: str = None):
        """Initialize network manager.
        
        Args:
            user_id: Unique ID for this user
            user_name: Display name for this user
        """
        # Initialize user identity
        self.user_id = user_id or str(uuid.uuid4())
        self.user_name = user_name or socket.gethostname()
        
        # Initialize WiFi Direct
        self.wifi_direct = WiFiDirect()
        self.wifi_direct.on_new_connection = self._on_new_connection
        
        # Message callbacks
        self.message_handlers: Dict[MessageType, List[Callable[[Message], None]]] = {
            message_type: [] for message_type in MessageType
        }
        
        # File transfer state
        self.file_transfers: Dict[str, Dict] = {}
        
        # Network state
        self.is_running = False
        self.is_group_owner = False
        
        # Test mode flag (for simulating connections without actual WiFi Direct)
        self.test_mode = False
        self.test_mode_peers = {}

    def start(self, as_group_owner: bool = True, port: int = 8000, test_mode: bool = False) -> bool:
        """Start the network manager.
        
        Args:
            as_group_owner: Whether to create a new WiFi Direct group
            port: Port to listen on for connections
            test_mode: Run in test mode (simulated connections)
            
        Returns:
            bool: True if started successfully
        """
        if self.is_running:
            logger.warning("Network manager already running")
            return True
        
        # Set test mode flag
        self.test_mode = test_mode
        
        if test_mode:
            logger.info("Starting in TEST MODE - no actual WiFi connections will be made")
            self.is_running = True
            self.is_group_owner = as_group_owner
            
            # Simulate a loopback peer for testing
            if as_group_owner:
                self._simulate_peer("TestClient", "127.0.0.1:9001")
            else:
                self._simulate_peer("TestOwner", "127.0.0.1:9000")
                
            return True
        else:
            # Normal mode - use WiFi Direct
            # Start WiFi Direct
            if as_group_owner:
                if not self.wifi_direct.create_group():
                    logger.error("Failed to create WiFi Direct group")
                    return False
                self.is_group_owner = True
            else:
                if not self.wifi_direct.scan_and_connect():
                    logger.error("Failed to connect to WiFi Direct group")
                    return False
                self.is_group_owner = False
            
            # Start server
            if not self.wifi_direct.start_server(port):
                logger.error("Failed to start server")
                return False
            
            self.is_running = True
            logger.info(f"Network manager started as {'group owner' if self.is_group_owner else 'client'}")
            
            # If not group owner, discover peers
            if not self.is_group_owner:
                self.wifi_direct.discover_peers()
            
            return True

    def _simulate_peer(self, peer_name: str, peer_addr: str) -> None:
        """Simulate a peer connection for testing purposes.
        
        Args:
            peer_name: Name of the simulated peer
            peer_addr: Address of the simulated peer
        """
        # Create a pair of connected sockets
        client_sock, server_sock = socket.socketpair()
        
        # Add the peer to the test peers list
        self.test_mode_peers[peer_addr] = (peer_name, client_sock)
        
        # Simulate the WiFi Direct peers list
        self.wifi_direct.peers[peer_addr] = (peer_name, server_sock)
        
        # Start a thread to handle messages from this peer
        threading.Thread(target=self._handle_peer_messages, 
                        args=(peer_name, server_sock), 
                        daemon=True).start()
        
        logger.info(f"Simulated peer added: {peer_name} at {peer_addr}")

    def stop(self) -> None:
        """Stop the network manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.test_mode:
            # Close simulated peer connections
            for addr, (_, sock) in list(self.test_mode_peers.items()):
                try:
                    sock.close()
                except Exception:
                    pass
            self.test_mode_peers.clear()
            
            # Clear WiFi Direct simulated peers
            self.wifi_direct.peers.clear()
        else:
            # Normal mode - stop WiFi Direct
            self.wifi_direct.stop()
            
        logger.info("Network manager stopped")

    def register_handler(self, msg_type: MessageType, 
                        handler: Callable[[Message], None]) -> None:
        """Register a handler for a specific message type.
        
        Args:
            msg_type: Type of message to handle
            handler: Function to call when a message of this type is received
        """
        self.message_handlers[msg_type].append(handler)

    def unregister_handler(self, msg_type: MessageType, 
                          handler: Callable[[Message], None]) -> None:
        """Unregister a message handler.
        
        Args:
            msg_type: Type of message the handler was registered for
            handler: Handler function to remove
        """
        if handler in self.message_handlers[msg_type]:
            self.message_handlers[msg_type].remove(handler)

    def _on_new_connection(self, hostname: str, sock: socket.socket) -> None:
        """Callback for new WiFi Direct connections.
        
        Args:
            hostname: Hostname of the new peer
            sock: Socket connected to the peer
        """
        # Start a thread to handle messages from this peer
        threading.Thread(target=self._handle_peer_messages, 
                        args=(hostname, sock), 
                        daemon=True).start()
        
        logger.info(f"Started message handler for peer {hostname}")

    def _handle_peer_messages(self, hostname: str, sock: socket.socket) -> None:
        """Handle messages from a peer.
        
        Args:
            hostname: Hostname of the peer
            sock: Socket connected to the peer
        """
        try:
            while self.is_running:
                # In test mode, simulate message reception
                if self.test_mode:
                    # Just sleep and continue - no actual messages will be received
                    # This keeps the thread alive for testing
                    time.sleep(1)
                    continue
                
                # Normal mode - receive actual messages
                message = MessageHandler.receive_message(sock)
                if not message:
                    logger.info(f"Connection closed by peer {hostname}")
                    break
                
                # Process message
                logger.debug(f"Received {message.msg_type} message from {message.sender_name}")
                
                # Call registered handlers
                for handler in self.message_handlers[message.msg_type]:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
                
        except Exception as e:
            logger.error(f"Error handling messages from peer {hostname}: {e}")

    def send_message(self, message: Message) -> bool:
        """Send a message to all connected peers.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if message sent to at least one peer
        """
        if not self.is_running:
            logger.error("Cannot send message: network manager not running")
            return False
        
        if self.test_mode:
            # In test mode, just log the message
            logger.info(f"[TEST MODE] Sending {message.msg_type} message from {message.sender_name}")
            
            # Echo the message back to simulate receiving it (for testing UI)
            for handler in self.message_handlers[message.msg_type]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
            
            return True
        
        # Normal mode - send to actual peers
        if not self.wifi_direct.peers:
            logger.warning("No peers connected to send message to")
            return False
        
        success = False
        for peer_addr, (peer_name, sock) in list(self.wifi_direct.peers.items()):
            try:
                if MessageHandler.send_message(sock, message):
                    success = True
            except Exception as e:
                logger.error(f"Error sending message to peer {peer_name}: {e}")
        
        return success

    def send_chat_message(self, text: str) -> bool:
        """Send a chat message to all peers.
        
        Args:
            text: Message text
            
        Returns:
            bool: True if message sent successfully
        """
        message = ChatMessage.create(self.user_id, self.user_name, text)
        return self.send_message(message)

    def send_file(self, filepath: str, chunk_size: int = 65536) -> str:
        """Send a file to all peers.
        
        Args:
            filepath: Path to the file to send
            chunk_size: Size of each chunk in bytes
            
        Returns:
            str: ID of the file transfer
        """
        import os
        
        # Check file exists
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Get file info
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        file_id = str(uuid.uuid4())
        
        # Send file transfer request
        request = FileTransfer.request(
            self.user_id, self.user_name, 
            filename, file_size, file_id
        )
        
        if not self.send_message(request):
            raise RuntimeError("Failed to send file transfer request")
        
        # Store file transfer state
        self.file_transfers[file_id] = {
            'filepath': filepath,
            'filename': filename,
            'file_size': file_size,
            'chunk_size': chunk_size,
            'status': 'requested',
            'accepted_by': set()
        }
        
        return file_id

    def accept_file(self, file_id: str, save_path: str) -> None:
        """Accept a file transfer request.
        
        Args:
            file_id: ID of the file transfer
            save_path: Where to save the file
        """
        # Send acceptance message
        response = FileTransfer.response(
            self.user_id, self.user_name,
            file_id, True
        )
        
        self.send_message(response)
        
        # Store file transfer state
        self.file_transfers[file_id] = {
            'save_path': save_path,
            'status': 'accepted',
            'received_chunks': set(),
            'total_chunks': None
        }

    def reject_file(self, file_id: str) -> None:
        """Reject a file transfer request.
        
        Args:
            file_id: ID of the file transfer
        """
        # Send rejection message
        response = FileTransfer.response(
            self.user_id, self.user_name,
            file_id, False
        )
        
        self.send_message(response)
        
        # Clean up any stored state
        if file_id in self.file_transfers:
            del self.file_transfers[file_id]

    def get_connected_peers(self) -> List[Tuple[str, str]]:
        """Get a list of connected peers.
        
        Returns:
            List[Tuple[str, str]]: List of (peer_addr, peer_name) tuples
        """
        if self.test_mode:
            return [(addr, name) for addr, (name, _) in self.test_mode_peers.items()]
        else:
            return [(addr, name) for addr, (name, _) in self.wifi_direct.peers.items()]

    def discover_peers(self) -> None:
        """Start peer discovery."""
        if not self.test_mode:
            self.wifi_direct.discover_peers()
        else:
            logger.info("[TEST MODE] Simulating peer discovery")

    def get_connection_info(self) -> Dict[str, str]:
        """Get information about the current connection.
        
        Returns:
            Dict[str, str]: Connection information
        """
        if self.test_mode:
            return {
                'user_id': self.user_id,
                'user_name': self.user_name,
                'is_group_owner': self.is_group_owner,
                'network_name': 'TestNetwork' if self.is_group_owner else 'TestNetworkClient',
                'local_ip': '127.0.0.1',
                'peer_count': len(self.test_mode_peers)
            }
        else:
            return {
                'user_id': self.user_id,
                'user_name': self.user_name,
                'is_group_owner': self.is_group_owner,
                'network_name': self.wifi_direct.network_name,
                'local_ip': self.wifi_direct._get_local_ip(),
                'peer_count': len(self.wifi_direct.peers)
            } 