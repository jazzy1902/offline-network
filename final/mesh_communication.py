import socket
import threading
import json
import time
import uuid
from datetime import datetime

class MeshNode:
    def __init__(self, node_id=None, ip=None, port=5555, broadcast_port=5556):
        self.node_id = node_id or str(uuid.uuid4())[:8]
        self.ip = ip
        self.port = port
        self.broadcast_port = broadcast_port
        self.peers = {}  # {node_id: {'ip': ip, 'last_seen': timestamp, 'active': bool}}
        self.messages = []  # Store messages for forwarding
        
        # Locks for thread safety
        self.peers_lock = threading.Lock()
        self.messages_lock = threading.Lock()
        
        # Sockets
        self.listener_socket = None
        self.broadcast_socket = None
        self.running = False
        
    def start(self, ip=None):
        """Start the mesh node services."""
        if ip:
            self.ip = ip
        
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
        
        print(f"Mesh node started with ID: {self.node_id}, IP: {self.ip}")
        
    def stop(self):
        """Stop the mesh node services."""
        self.running = False
        
        if self.listener_socket:
            self.listener_socket.close()
        
        if self.broadcast_socket:
            self.broadcast_socket.close()
            
        print("Mesh node stopped")
        
    def _start_listener(self):
        """Start listening for incoming messages."""
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener_socket.bind(('0.0.0.0', self.port))
        self.listener_socket.settimeout(1)  # 1 second timeout for clean shutdown
        
        print(f"Listening for messages on port {self.port}")
        
        while self.running:
            try:
                data, addr = self.listener_socket.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))
                self._handle_message(message, addr)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in listener: {e}")
                
    def _start_discovery(self):
        """Start broadcasting discovery messages."""
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_socket.settimeout(1)  # 1 second timeout for clean shutdown
        
        print("Starting network discovery")
        
        while self.running:
            try:
                # Send discovery broadcast
                discovery_message = {
                    'type': 'discovery',
                    'node_id': self.node_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Broadcast to subnet
                self.broadcast_socket.sendto(
                    json.dumps(discovery_message).encode('utf-8'),
                    ('<broadcast>', self.broadcast_port)
                )
                
                # Also listen for other discovery messages
                try:
                    self.broadcast_socket.bind(('0.0.0.0', self.broadcast_port))
                    while self.running:
                        try:
                            data, addr = self.broadcast_socket.recvfrom(4096)
                            message = json.loads(data.decode('utf-8'))
                            if message.get('type') == 'discovery':
                                sender_id = message.get('node_id')
                                sender_ip = addr[0]
                                
                                if sender_id != self.node_id:
                                    with self.peers_lock:
                                        if sender_id not in self.peers:
                                            print(f"Discovered new peer: {sender_id} at {sender_ip}")
                                        
                                        # Update peer information
                                        self.peers[sender_id] = {
                                            'ip': sender_ip,
                                            'last_seen': time.time(),
                                            'active': True
                                        }
                        except socket.timeout:
                            continue
                except:
                    # Socket might already be bound on restart
                    pass
                
                # Sleep for a while before next discovery
                time.sleep(10)
            except Exception as e:
                print(f"Error in discovery: {e}")
                time.sleep(5)
                
    def _send_heartbeats(self):
        """Send periodic heartbeats to known peers."""
        while self.running:
            try:
                with self.peers_lock:
                    # Create a copy of peers to avoid modification during iteration
                    peers_copy = dict(self.peers)
                
                for peer_id, peer_info in peers_copy.items():
                    if peer_info['active']:
                        heartbeat_message = {
                            'type': 'heartbeat',
                            'node_id': self.node_id,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            sock.sendto(
                                json.dumps(heartbeat_message).encode('utf-8'),
                                (peer_info['ip'], self.port)
                            )
                            sock.close()
                        except Exception as e:
                            print(f"Error sending heartbeat to {peer_id}: {e}")
                            
                # Check for inactive peers
                current_time = time.time()
                with self.peers_lock:
                    for peer_id, peer_info in self.peers.items():
                        # Mark peer as inactive if not seen for more than 30 seconds
                        if current_time - peer_info['last_seen'] > 30:
                            if peer_info['active']:
                                print(f"Peer {peer_id} is now inactive")
                                peer_info['active'] = False
                
                time.sleep(5)
            except Exception as e:
                print(f"Error in heartbeat: {e}")
                time.sleep(5)
                
    def _handle_message(self, message, addr):
        """Handle incoming message."""
        message_type = message.get('type')
        sender_id = message.get('node_id')
        sender_ip = addr[0]
        
        # Update peer information
        if sender_id and sender_id != self.node_id:
            with self.peers_lock:
                self.peers[sender_id] = {
                    'ip': sender_ip,
                    'last_seen': time.time(),
                    'active': True
                }
        
        # Process message based on type
        if message_type == 'heartbeat':
            # Heartbeat messages are handled above by updating peer info
            pass
        elif message_type == 'text':
            # Handle text message
            print(f"Received text message from {sender_id}: {message.get('content')}")
            # Store message for potential forwarding
            with self.messages_lock:
                if not any(m.get('message_id') == message.get('message_id') for m in self.messages):
                    self.messages.append(message)
        elif message_type == 'file_info':
            # Handle file transfer information (future implementation)
            print(f"Received file info from {sender_id}: {message.get('filename')}")
        
    def send_text_message(self, content, target_id=None):
        """Send a text message to a specific peer or broadcast to all peers."""
        message = {
            'type': 'text',
            'node_id': self.node_id,
            'content': content,
            'message_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'ttl': 5  # Time to live for multi-hop (future implementation)
        }
        
        # Store message for potential forwarding
        with self.messages_lock:
            self.messages.append(message)
        
        if target_id:
            # Send to specific peer
            with self.peers_lock:
                if target_id in self.peers and self.peers[target_id]['active']:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.sendto(
                            json.dumps(message).encode('utf-8'),
                            (self.peers[target_id]['ip'], self.port)
                        )
                        sock.close()
                        return True
                    except Exception as e:
                        print(f"Error sending message to {target_id}: {e}")
                        return False
                else:
                    print(f"Peer {target_id} not found or inactive")
                    return False
        else:
            # Broadcast to all active peers
            success = False
            with self.peers_lock:
                for peer_id, peer_info in self.peers.items():
                    if peer_info['active']:
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            sock.sendto(
                                json.dumps(message).encode('utf-8'),
                                (peer_info['ip'], self.port)
                            )
                            sock.close()
                            success = True
                        except Exception as e:
                            print(f"Error broadcasting message to {peer_id}: {e}")
            
            return success
            
    def get_active_peers(self):
        """Get a list of active peers."""
        with self.peers_lock:
            return {
                peer_id: peer_info 
                for peer_id, peer_info in self.peers.items() 
                if peer_info['active']
            } 