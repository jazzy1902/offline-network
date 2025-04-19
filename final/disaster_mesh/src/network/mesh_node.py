"""
DisasterMeshNode module containing the main peer-to-peer communication class.

This module implements the core networking functionality for the disaster mesh network,
handling discovery, connection, and communication between nodes.
"""

import logging
import socket
import threading
import time
import json
import os
from typing import Dict, List, Optional, Callable
from datetime import datetime
import uuid

try:
    # When running as a module
    from disaster_mesh.src.network.network_utils import NetworkManager, get_ip_addresses, get_subnet_prefix, get_short_id
except ImportError:
    # When running directly
    from src.network.network_utils import NetworkManager, get_ip_addresses, get_subnet_prefix, get_short_id

logger = logging.getLogger(__name__)

class DisasterMeshNode:
    """
    Implements a peer-to-peer node for the disaster mesh network.
    
    This class handles:
    - Automatic discovery of other nodes on the network
    - Establishing connections with other nodes
    - Sending and receiving messages
    - Maintaining the network topology
    """
    
    def __init__(self, port: int = 5555, auto_connect: bool = True):
        """
        Initialize a new DisasterMeshNode.
        
        Args:
            port: The port to use for communication
            auto_connect: Whether to automatically connect to the network
        """
        self.port = port
        self.node_id = get_short_id()
        
        # Ensure we have a valid node_id - if get_short_id() returns None or empty string
        if not self.node_id:
            self.node_id = uuid.uuid4().hex[:8].upper()
            
        self.peers = {}  # {peer_id: (ip, last_seen)} format for UI compatibility
        self.messages = []  # [{id, sender, timestamp, content, ttl}]
        self.running = False
        self.network_manager = NetworkManager()
        self.logger = logger.info  # Default logger function
        
        # Callbacks
        self.on_message_received: Optional[Callable] = None
        self.on_peer_connected: Optional[Callable] = None
        self.on_peer_disconnected: Optional[Callable] = None
        
        # Create sockets
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.message_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.message_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Start the network manager if auto_connect is enabled
        if auto_connect:
            self.network_manager.start()
    
    def start(self):
        """Start the mesh node and begin broadcasting and listening."""
        if self.running:
            self.log("Node already running")
            return False
        
        self.running = True
        
        # Try with the configured port, then fall back to other ports if needed
        ports_to_try = [self.port]
        if self.port == 5555:  # Only add fallbacks for the default port
            ports_to_try.extend([5556, 5557, 5558, 5559])
        
        success = False
        for port in ports_to_try:
            try:
                # Create new sockets for each attempt
                self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                self.message_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.message_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Bind the discovery socket
                self.discovery_socket.bind(('', port))
                
                # Bind the message socket
                self.message_socket.bind(('', port))
                self.message_socket.listen(5)
                
                # Update the port
                self.port = port
                success = True
                break
            except Exception as e:
                self.log(f"Failed to bind to port {port}: {e}")
                
                # Close the sockets before trying another port
                try:
                    self.discovery_socket.close()
                    self.message_socket.close()
                except:
                    pass
        
        if not success:
            self.running = False
            self.log("Failed to start node: Could not bind to any port")
            return False
        
        # Start threads
        threading.Thread(target=self._discovery_broadcast, daemon=True).start()
        threading.Thread(target=self._discovery_listen, daemon=True).start()
        threading.Thread(target=self._message_listen, daemon=True).start()
        
        self.log(f"Node {self.node_id} started on port {self.port}")
        return True
    
    def stop(self):
        """Stop the mesh node and close all connections."""
        if not self.running:
            return
        
        self.running = False
        
        # Close sockets
        try:
            self.discovery_socket.close()
            self.message_socket.close()
        except Exception as e:
            self.log(f"Error closing sockets: {e}")
        
        # Stop the network manager
        self.network_manager.stop()
        
        self.log(f"Node {self.node_id} stopped")
    
    def send_message(self, content, ttl=10):
        """
        Send a message to the mesh network.
        
        Args:
            content: The message content
            ttl: Time-to-live for the message
        """
        if not self.running:
            self.log("Cannot send message: node not running")
            return False
        
        msg_id = f"{self.node_id}_{int(time.time())}_{os.urandom(4).hex()}"
        timestamp = datetime.now().isoformat()
        
        message = {
            "id": msg_id,
            "sender": self.node_id,
            "timestamp": timestamp,
            "content": content,
            "ttl": ttl
        }
        
        # Add to local messages
        self.messages.append(message)
        
        # Propagate to all known peers
        message_json = json.dumps({
            "node_id": self.node_id,
            "command": "new_message",
            "message": message
        })
        
        # Broadcast to all peers
        success = True
        for peer_id, (ip, _) in list(self.peers.items()):
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.settimeout(2)
                peer_socket.connect((ip, self.port))
                peer_socket.sendall(message_json.encode("utf-8"))
                peer_socket.close()
                self.log(f"Broadcast message to {peer_id}")
            except Exception as e:
                self.log(f"Failed to broadcast message to {peer_id}: {e}")
                success = False
        
        return msg_id
    
    def _discovery_broadcast(self):
        """Periodically broadcast node information to discover peers."""
        while self.running:
            try:
                # Get current IP addresses
                ip_addresses = get_ip_addresses()
                
                # Create discovery packet
                discovery_packet = {
                    "type": "discovery",
                    "node_id": self.node_id,
                    "addresses": ip_addresses,
                    "timestamp": time.time()
                }
                
                # Send broadcast on all available interfaces
                for ip in ip_addresses:
                    try:
                        # Calculate broadcast address
                        subnet = get_subnet_prefix(ip)
                        if subnet:
                            broadcast_addr = subnet.broadcast_address.compressed
                            self.discovery_socket.sendto(
                                json.dumps(discovery_packet).encode("utf-8"),
                                (broadcast_addr, self.port)
                            )
                    except Exception as e:
                        self.log(f"Broadcast error on {ip}: {e}")
                
                time.sleep(5)  # Send discovery packet every 5 seconds
            except Exception as e:
                self.log(f"Discovery broadcast error: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _discovery_listen(self):
        """Listen for discovery broadcasts from other nodes."""
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                packet = json.loads(data.decode("utf-8"))
                
                if packet["type"] == "discovery" and packet["node_id"] != self.node_id:
                    node_id = packet["node_id"]
                    
                    # Add or update peer - store as tuple for UI compatibility
                    self.peers[node_id] = (addr[0], time.time())
                    
                    self.log(f"Discovered peer: {node_id} at {addr[0]}")
                    
                    # Trigger callback if set
                    if self.on_peer_connected and node_id not in self.peers:
                        self.on_peer_connected(node_id, addr[0])
            except Exception as e:
                self.log(f"Discovery listen error: {e}")
    
    def _message_listen(self):
        """Listen for incoming messages from other nodes."""
        while self.running:
            try:
                client_socket, addr = self.message_socket.accept()
                client_handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_handler.start()
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    self.log(f"Message listen error: {e}")
                    time.sleep(1)
    
    def _handle_client(self, client_socket, addr):
        """Handle an incoming client connection."""
        try:
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            if data:
                packet = json.loads(data.decode("utf-8"))
                
                # Extract node ID and command
                node_id = packet.get('node_id')
                command = packet.get('command')
                
                if not node_id:
                    return
                    
                # Update peer list
                self.peers[node_id] = (addr[0], time.time())
                
                # Handle commands
                if command == "hello":
                    # Hello response already sent by accepting socket
                    pass
                elif command == "new_message":
                    # Store message
                    message = packet.get('message')
                    if message:
                        self.messages.append(message)
                        self.log(f"Received message from {message.get('sender', 'unknown')}")
                        
                        # Trigger callback if set
                        if self.on_message_received:
                            self.on_message_received(message)
                
        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
    
    def get_peers(self):
        """Get the current list of peers."""
        # Remove stale peers (not seen in the last 30 seconds)
        current_time = time.time()
        stale_peers = []
        
        for peer_id, (ip, last_seen) in self.peers.items():
            if current_time - last_seen > 30:
                stale_peers.append(peer_id)
        
        for peer_id in stale_peers:
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer_id)
            del self.peers[peer_id]
        
        return self.peers
    
    def get_messages(self):
        """Get the message history."""
        return self.messages
    
    def set_logger(self, logger_func):
        """Set a custom logger function."""
        self.logger = logger_func
        
    def log(self, message):
        """Log a message using the current logger."""
        self.logger(f"[MESH] {message}")
        
    def _get_local_ip(self):
        """Get the local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Doesn't actually send traffic
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None
    
    def _try_connect(self, ip):
        """Try to connect to a potential peer."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((ip, self.port))  # Use self.port instead of PORT constant
            
            # Send node info
            s.send(json.dumps({
                "node_id": self.node_id,
                "command": "hello"
            }).encode('utf-8'))
            
            # Get peer info
            data = s.recv(1024)
            if data:
                peer_info = json.loads(data.decode('utf-8'))
                peer_id = peer_info.get('node_id')
                if peer_id and peer_id != self.node_id:
                    self.peers[peer_id] = (ip, time.time())
                    self.log(f"Connected to peer: {peer_id} at {ip}")
        except Exception as e:
            # Failed to connect - not a peer or connection error
            pass
        finally:
            try:
                s.close()
            except:
                pass 