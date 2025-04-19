import socket
import threading
import time
import json
import os
import base64
from datetime import datetime

# Constants
PORT = 5555
MESSAGE_HISTORY_SIZE = 1000
BROADCAST_INTERVAL = 30  # seconds
MAX_MESSAGE_SIZE = 8192

class DisasterMeshNode:
    def __init__(self, node_id=None):
        self.node_id = node_id or f"node_{os.urandom(4).hex()}"
        self.peers = {}  # {peer_id: (ip, last_seen)}
        self.messages = []  # [{id, sender, timestamp, content, ttl}]
        self.message_ids = set()  # Track seen message IDs
        self.running = False
        self.logger = print  # Default logger function
        
    def set_logger(self, logger_func):
        """Set a custom logger function."""
        self.logger = logger_func
        
    def log(self, message):
        """Log a message using the current logger."""
        self.logger(f"[MESH] {message}")
        
    def start(self):
        """Start the mesh network node."""
        self.running = True
        
        # Start server to listen for connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(('0.0.0.0', PORT))
            self.server_socket.listen(5)
            
            # Start threads
            threading.Thread(target=self._accept_connections, daemon=True).start()
            threading.Thread(target=self._discover_peers, daemon=True).start()
            threading.Thread(target=self._cleanup_old_peers, daemon=True).start()
            threading.Thread(target=self._broadcast_presence, daemon=True).start()
            
            self.log(f"Node {self.node_id} started on port {PORT}")
            return True
        except Exception as e:
            self.log(f"Failed to start node: {e}")
            self.running = False
            return False
        
    def stop(self):
        """Stop the mesh network node."""
        self.running = False
        try:
            self.server_socket.close()
        except:
            pass
        self.log("Node stopped")
        
    def send_message(self, content, ttl=10):
        """Send a message to the mesh network."""
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
        self._add_message(message)
        
        # Propagate to all known peers
        self._propagate_message(message)
        
        return msg_id
        
    def get_messages(self, count=10):
        """Get the most recent messages."""
        return sorted(self.messages, key=lambda x: x["timestamp"], reverse=True)[:count]
    
    def _accept_connections(self):
        """Accept incoming connections from peers."""
        while self.running:
            try:
                client, address = self.server_socket.accept()
                threading.Thread(target=self._handle_client, 
                                 args=(client, address), daemon=True).start()
            except:
                if self.running:  # Only log if we're still supposed to be running
                    time.sleep(1)
    
    def _handle_client(self, client_socket, address):
        """Handle communication with a connected peer."""
        try:
            # Receive peer information
            data = client_socket.recv(1024)
            if not data:
                return
                
            peer_info = json.loads(data.decode('utf-8'))
            peer_id = peer_info.get('node_id')
            command = peer_info.get('command')
            
            if not peer_id:
                return
                
            # Update peer list
            self.peers[peer_id] = (address[0], time.time())
            
            # Handle commands
            if command == "hello":
                # Send our node info
                client_socket.send(json.dumps({
                    "node_id": self.node_id,
                    "command": "hello"
                }).encode('utf-8'))
                
                # Sync messages
                self._sync_messages(client_socket, peer_id)
                
            elif command == "new_message":
                # Add the new message
                message = peer_info.get('message')
                if message and message["id"] not in self.message_ids:
                    self._add_message(message)
                    self._propagate_message(message)
        
        except Exception as e:
            self.log(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
    
    def _discover_peers(self):
        """Actively discover peers on the local network."""
        while self.running:
            try:
                # Scan local subnet
                local_ip = self._get_local_ip()
                if local_ip:
                    subnet = '.'.join(local_ip.split('.')[:3])
                    for i in range(1, 255):
                        target_ip = f"{subnet}.{i}"
                        if target_ip != local_ip:
                            threading.Thread(target=self._try_connect, 
                                            args=(target_ip,), daemon=True).start()
            except Exception as e:
                self.log(f"Error discovering peers: {e}")
            
            time.sleep(300)  # Scan every 5 minutes
    
    def _try_connect(self, ip):
        """Try to connect to a potential peer."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((ip, PORT))
            
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
                    self._sync_messages(s, peer_id)
        except:
            pass  # Failed to connect - not a peer
        finally:
            try:
                s.close()
            except:
                pass
    
    def _sync_messages(self, socket_conn, peer_id):
        """Synchronize messages with a peer."""
        try:
            # Send our message IDs
            socket_conn.send(json.dumps({
                "command": "message_ids",
                "ids": list(self.message_ids)
            }).encode('utf-8'))
            
            # Receive their missing message IDs
            data = socket_conn.recv(MAX_MESSAGE_SIZE)
            if not data:
                return
                
            peer_data = json.loads(data.decode('utf-8'))
            if peer_data.get('command') == 'request_messages':
                requested_ids = peer_data.get('ids', [])
                
                # Send requested messages
                messages_to_send = [msg for msg in self.messages 
                                    if msg["id"] in requested_ids]
                
                if messages_to_send:
                    socket_conn.send(json.dumps({
                        "command": "messages",
                        "messages": messages_to_send
                    }).encode('utf-8'))
            
            # Receive their messages we don't have
            data = socket_conn.recv(MAX_MESSAGE_SIZE)
            if data:
                peer_data = json.loads(data.decode('utf-8'))
                if peer_data.get('command') == 'messages':
                    for message in peer_data.get('messages', []):
                        if message["id"] not in self.message_ids:
                            self._add_message(message)
        
        except Exception as e:
            self.log(f"Error syncing with peer {peer_id}: {e}")
    
    def _broadcast_presence(self):
        """Periodically broadcast presence to all peers."""
        while self.running:
            for peer_id, (ip, last_seen) in list(self.peers.items()):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect((ip, PORT))
                    
                    # Send hello message
                    s.send(json.dumps({
                        "node_id": self.node_id,
                        "command": "hello"
                    }).encode('utf-8'))
                    
                    # Update last seen
                    self.peers[peer_id] = (ip, time.time())
                    s.close()
                except:
                    pass  # Connection failed
            
            time.sleep(BROADCAST_INTERVAL)
    
    def _cleanup_old_peers(self):
        """Remove peers that haven't been seen recently."""
        while self.running:
            now = time.time()
            stale_peers = [pid for pid, (_, last_seen) in self.peers.items() 
                          if now - last_seen > 600]  # 10 minutes
            
            for pid in stale_peers:
                del self.peers[pid]
            
            time.sleep(60)  # Check every minute
    
    def _propagate_message(self, message):
        """Propagate a message to all known peers."""
        if message["ttl"] <= 0:
            return
            
        # Decrement TTL for forwarding
        message["ttl"] = message["ttl"] - 1
        
        for peer_id, (ip, _) in list(self.peers.items()):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((ip, PORT))
                
                s.send(json.dumps({
                    "node_id": self.node_id,
                    "command": "new_message",
                    "message": message
                }).encode('utf-8'))
                
                s.close()
            except:
                pass  # Connection failed
    
    def _add_message(self, message):
        """Add a message to the local store."""
        if message["id"] in self.message_ids:
            return
            
        self.message_ids.add(message["id"])
        self.messages.append(message)
        
        # Keep message history manageable
        if len(self.messages) > MESSAGE_HISTORY_SIZE:
            oldest = min(range(len(self.messages)), 
                        key=lambda i: self.messages[i]["timestamp"])
            oldest_id = self.messages[oldest]["id"]
            self.message_ids.remove(oldest_id)
            self.messages.pop(oldest)
    
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

# File handling functions
def encode_file(filepath):
    """Encode a file to a base64 string."""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def decode_file(b64data, output_path):
    """Decode a base64 string and save as a file."""
    with open(output_path, 'wb') as f:
        f.write(base64.b64decode(b64data)) 