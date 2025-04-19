import socket
import threading
import json
import time
import uuid
import pickle
import hashlib
from datetime import datetime
from collections import deque

class MeshMessage:
    """Represents a message in the mesh network."""
    
    def __init__(self, content, msg_type="text", sender_id=None, target_id=None, hop_count=0, msg_id=None):
        self.msg_id = msg_id or str(uuid.uuid4())
        self.sender_id = sender_id
        self.target_id = target_id  # None means broadcast to all
        self.content = content
        self.msg_type = msg_type
        self.timestamp = datetime.now().isoformat()
        self.hop_count = hop_count
        self.ttl = 10  # Time to live (max hops)
        
    def to_dict(self):
        """Convert message to dictionary for serialization."""
        return {
            'msg_id': self.msg_id,
            'sender_id': self.sender_id,
            'target_id': self.target_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'timestamp': self.timestamp,
            'hop_count': self.hop_count,
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a message from dictionary."""
        msg = cls(
            content=data['content'],
            msg_type=data['msg_type'],
            sender_id=data['sender_id'],
            target_id=data['target_id'],
            hop_count=data['hop_count'],
            msg_id=data['msg_id']
        )
        msg.timestamp = data['timestamp']
        msg.ttl = data['ttl']
        return msg

class MeshNode:
    """A node in the mesh network that can send, receive, and relay messages."""
    
    def __init__(self, node_id=None, ip=None, port=5555, broadcast_port=5556):
        # Node identity
        self.node_id = node_id or str(uuid.uuid4())[:8]
        self.ip = ip
        self.port = port
        self.broadcast_port = broadcast_port
        
        # Network state
        self.peers = {}  # {node_id: {'ip': ip, 'last_seen': timestamp, 'active': bool}}
        self.message_cache = {}  # {msg_id: timestamp} - Used to prevent message loops
        self.pending_messages = deque()  # Messages to be processed
        self.message_handlers = {}  # {msg_type: handler_function}
        self.network_manager = None
        
        # Locks for thread safety
        self.peers_lock = threading.Lock()
        self.cache_lock = threading.Lock()
        self.message_lock = threading.Lock()
        
        # Sockets and state
        self.listener_socket = None
        self.broadcaster_socket = None
        self.running = False
        
        # Register default message handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default message handlers."""
        self.register_handler("text", self._handle_text_message)
        self.register_handler("heartbeat", self._handle_heartbeat)
        self.register_handler("discovery", self._handle_discovery)
        self.register_handler("file_info", self._handle_file_info)
        self.register_handler("file_chunk", self._handle_file_chunk)
    
    def register_handler(self, msg_type, handler_func):
        """Register a handler for a specific message type."""
        self.message_handlers[msg_type] = handler_func
    
    def set_network_manager(self, network_manager):
        """Set the network manager for this node."""
        self.network_manager = network_manager
        
    def start(self, ip=None):
        """Start the mesh node services."""
        if ip:
            self.ip = ip
        
        if not self.ip:
            print("ERROR: Cannot start mesh node without an IP address.")
            return False
        
        self.running = True
        
        # Start listener thread
        self.listener_thread = threading.Thread(target=self._start_listener)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        
        # Start discovery thread
        self.discovery_thread = threading.Thread(target=self._start_discovery)
        self.discovery_thread.daemon = True
        self.discovery_thread.start()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeats)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        # Start message processor thread
        self.processor_thread = threading.Thread(target=self._process_messages)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        print(f"Mesh node started with ID: {self.node_id}, IP: {self.ip}")
        return True
        
    def stop(self):
        """Stop the mesh node services."""
        self.running = False
        
        if self.listener_socket:
            self.listener_socket.close()
        
        if self.broadcaster_socket:
            self.broadcaster_socket.close()
            
        print("Mesh node stopped")
        
    def _start_listener(self):
        """Start listening for incoming messages."""
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener_socket.bind(('0.0.0.0', self.port))
        self.listener_socket.settimeout(1)  # 1 second timeout for clean shutdown
        
        print(f"Listening for messages on port {self.port}")
        
        while self.running:
            try:
                data, addr = self.listener_socket.recvfrom(8192)  # Increased buffer size for larger messages
                self._enqueue_message(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in listener: {e}")
    
    def _enqueue_message(self, data, addr):
        """Parse message and add to processing queue."""
        try:
            try:
                # Try to parse as JSON first (text messages)
                message_dict = json.loads(data.decode('utf-8'))
                message = MeshMessage.from_dict(message_dict)
            except:
                # If that fails, try pickle (binary messages like file chunks)
                message = pickle.loads(data)
            
            with self.message_lock:
                self.pending_messages.append((message, addr))
        except Exception as e:
            print(f"Error parsing message: {e}")
    
    def _process_messages(self):
        """Process queued messages."""
        while self.running:
            try:
                # Get a message from the queue
                with self.message_lock:
                    if not self.pending_messages:
                        time.sleep(0.1)
                        continue
                    message, addr = self.pending_messages.popleft()
                
                # Process the message
                self._handle_message(message, addr)
            except Exception as e:
                print(f"Error processing message: {e}")
                time.sleep(1)
                
    def _start_discovery(self):
        """Start broadcasting discovery messages."""
        self.broadcaster_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcaster_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcaster_socket.settimeout(1)  # 1 second timeout for clean shutdown
        
        print("Starting network discovery")
        
        while self.running:
            try:
                # Create discovery message
                discovery_message = MeshMessage(
                    content={
                        'ip': self.ip,
                        'port': self.port
                    },
                    msg_type="discovery",
                    sender_id=self.node_id
                )
                
                # Broadcast to subnet
                message_data = json.dumps(discovery_message.to_dict()).encode('utf-8')
                
                # Try to get the subnet prefix for more efficient broadcasting
                from network_utils import get_subnet_prefix
                broadcast_addr = get_subnet_prefix()
                
                try:
                    self.broadcaster_socket.sendto(message_data, (broadcast_addr, self.broadcast_port))
                except:
                    # If that fails, fall back to global broadcast
                    self.broadcaster_socket.sendto(message_data, ('<broadcast>', self.broadcast_port))
                
                # Sleep for a while before next discovery
                time.sleep(15)  # Reduced frequency to avoid network congestion
            except Exception as e:
                print(f"Error in discovery: {e}")
                time.sleep(5)
                
    def _send_heartbeats(self):
        """Send periodic heartbeats to known peers."""
        while self.running:
            try:
                # Create heartbeat message
                heartbeat_message = MeshMessage(
                    content={
                        'ip': self.ip,
                        'port': self.port
                    },
                    msg_type="heartbeat",
                    sender_id=self.node_id
                )
                
                message_data = json.dumps(heartbeat_message.to_dict()).encode('utf-8')
                
                with self.peers_lock:
                    # Create a copy of peers to avoid modification during iteration
                    peers_copy = dict(self.peers)
                
                for peer_id, peer_info in peers_copy.items():
                    if peer_info['active']:
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            sock.sendto(message_data, (peer_info['ip'], self.port))
                            sock.close()
                        except Exception as e:
                            print(f"Error sending heartbeat to {peer_id}: {e}")
                            
                # Check for inactive peers
                current_time = time.time()
                with self.peers_lock:
                    for peer_id, peer_info in self.peers.items():
                        # Mark peer as inactive if not seen for more than 30 seconds
                        if current_time - peer_info['last_seen'] > 60:  # Increased timeout
                            if peer_info['active']:
                                print(f"Peer {peer_id} is now inactive")
                                peer_info['active'] = False
                
                time.sleep(10)
            except Exception as e:
                print(f"Error in heartbeat: {e}")
                time.sleep(5)
                
    def _handle_message(self, message, addr):
        """Handle incoming message based on type."""
        # Check if we've already seen this message (to prevent loops)
        with self.cache_lock:
            if message.msg_id in self.message_cache:
                # Already processed this message, ignore it
                return
            
            # Add to cache to prevent processing duplicates
            self.message_cache[message.msg_id] = time.time()
            
            # Clean up old cached messages
            current_time = time.time()
            expired_msgs = [msg_id for msg_id, timestamp in self.message_cache.items() 
                          if current_time - timestamp > 300]  # 5 minutes
            for msg_id in expired_msgs:
                del self.message_cache[msg_id]
        
        # Update peer information
        sender_id = message.sender_id
        sender_ip = addr[0]
        
        if sender_id and sender_id != self.node_id:
            with self.peers_lock:
                if sender_id not in self.peers:
                    print(f"New peer discovered: {sender_id} at {sender_ip}")
                    
                self.peers[sender_id] = {
                    'ip': sender_ip,
                    'last_seen': time.time(),
                    'active': True
                }
        
        # Handle message based on type using registered handlers
        if message.msg_type in self.message_handlers:
            self.message_handlers[message.msg_type](message, addr)
        else:
            print(f"Unknown message type: {message.msg_type}")
        
        # Forward message if needed
        self._relay_message_if_needed(message)
    
    def _relay_message_if_needed(self, message):
        """Relay message to other peers if it hasn't reached TTL and needs forwarding."""
        # Don't relay if message is at TTL
        if message.hop_count >= message.ttl:
            return
        
        # Don't relay our own messages
        if message.sender_id == self.node_id:
            return
        
        # Increment hop count for relaying
        message.hop_count += 1
        
        # If this message has a specific target, only relay if we're not the target
        if message.target_id and message.target_id != self.node_id:
            # Try to send directly to target if we know it
            with self.peers_lock:
                if message.target_id in self.peers and self.peers[message.target_id]['active']:
                    peer_info = self.peers[message.target_id]
                    self._send_message_to_peer(message, peer_info['ip'], self.port)
                    return
            
            # If we don't know the target or it's not active, relay to all peers
            self._broadcast_to_peers(message, exclude_sender=True)
        else:
            # For broadcast messages, relay to all peers except the sender
            self._broadcast_to_peers(message, exclude_sender=True)
    
    def _broadcast_to_peers(self, message, exclude_sender=False):
        """Broadcast a message to all active peers."""
        with self.peers_lock:
            peers_copy = dict(self.peers)
        
        for peer_id, peer_info in peers_copy.items():
            # Skip inactive peers
            if not peer_info['active']:
                continue
                
            # Skip original sender to avoid loops
            if exclude_sender and peer_id == message.sender_id:
                continue
                
            self._send_message_to_peer(message, peer_info['ip'], self.port)
    
    def _send_message_to_peer(self, message, ip, port):
        """Send a message to a specific peer."""
        try:
            # Serialize the message
            if isinstance(message.content, (dict, list)) or message.msg_type in ["text", "heartbeat", "discovery"]:
                # Use JSON for text messages
                message_data = json.dumps(message.to_dict()).encode('utf-8')
            else:
                # Use pickle for binary data
                message_data = pickle.dumps(message)
                
            # Send the message
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message_data, (ip, port))
            sock.close()
            return True
        except Exception as e:
            print(f"Error sending message to {ip}: {e}")
            return False
    
    # Default message handlers
    def _handle_text_message(self, message, addr):
        """Handle a text message."""
        print(f"Received text message from {message.sender_id}: {message.content}")
        
        # Notify UI or application layer
        if hasattr(self, 'on_message_received') and callable(self.on_message_received):
            self.on_message_received(message)
    
    def _handle_heartbeat(self, message, addr):
        """Handle a heartbeat message (just updates peer status)."""
        pass  # Peer status is already updated in _handle_message
    
    def _handle_discovery(self, message, addr):
        """Handle a discovery message."""
        # Already updated peer info in _handle_message
        pass
    
    def _handle_file_info(self, message, addr):
        """Handle information about a file transfer."""
        print(f"Received file info from {message.sender_id}: {message.content.get('filename')}")
        
        # Notify UI or application layer
        if hasattr(self, 'on_file_info_received') and callable(self.on_file_info_received):
            self.on_file_info_received(message)
    
    def _handle_file_chunk(self, message, addr):
        """Handle a chunk of file data."""
        file_id = message.content.get('file_id')
        chunk_num = message.content.get('chunk_num')
        print(f"Received file chunk {chunk_num} for file {file_id} from {message.sender_id}")
        
        # Notify UI or application layer
        if hasattr(self, 'on_file_chunk_received') and callable(self.on_file_chunk_received):
            self.on_file_chunk_received(message)
    
    # Public API
    def send_text_message(self, content, target_id=None):
        """Send a text message to a specific peer or broadcast to all peers."""
        message = MeshMessage(
            content=content,
            msg_type="text",
            sender_id=self.node_id,
            target_id=target_id
        )
        
        if target_id:
            # Send to specific peer
            with self.peers_lock:
                if target_id in self.peers and self.peers[target_id]['active']:
                    peer_info = self.peers[target_id]
                    return self._send_message_to_peer(message, peer_info['ip'], self.port)
                else:
                    print(f"Peer {target_id} not found or inactive, broadcasting instead")
                    # If target is not directly connected, broadcast to all peers
                    # (mesh routing will handle delivery)
                    return self._broadcast_to_peers(message)
        else:
            # Broadcast to all active peers
            return self._broadcast_to_peers(message)
    
    def send_file(self, file_path, target_id=None, chunk_size=8192):
        """Send a file to a specific peer or broadcast to all peers."""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
            file_id = hashlib.md5(file_data).hexdigest()
            file_size = len(file_data)
            
            # Send file info first
            info_message = MeshMessage(
                content={
                    'file_id': file_id,
                    'filename': file_name,
                    'size': file_size,
                    'chunks': (file_size + chunk_size - 1) // chunk_size
                },
                msg_type="file_info",
                sender_id=self.node_id,
                target_id=target_id
            )
            
            if not self._broadcast_to_peers(info_message):
                print("Failed to send file info")
                return False
                
            # Split file into chunks and send
            chunks = (file_size + chunk_size - 1) // chunk_size
            success = True
            
            for i in range(chunks):
                chunk_start = i * chunk_size
                chunk_end = min((i + 1) * chunk_size, file_size)
                chunk_data = file_data[chunk_start:chunk_end]
                
                chunk_message = MeshMessage(
                    content={
                        'file_id': file_id,
                        'chunk_num': i,
                        'total_chunks': chunks,
                        'data': chunk_data
                    },
                    msg_type="file_chunk",
                    sender_id=self.node_id,
                    target_id=target_id
                )
                
                if not self._broadcast_to_peers(chunk_message):
                    print(f"Failed to send chunk {i}")
                    success = False
                    
                # Slight delay to avoid overwhelming the network
                time.sleep(0.1)
                
            return success
        except Exception as e:
            print(f"Error sending file: {e}")
            return False
    
    def get_active_peers(self):
        """Get a list of active peers."""
        with self.peers_lock:
            return {
                peer_id: peer_info 
                for peer_id, peer_info in self.peers.items() 
                if peer_info['active']
            }
        
    def get_routing_table(self):
        """Get a routing table of known peers."""
        # In a future implementation, this would include multi-hop route information
        return self.get_active_peers() 