import logging
import socket
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

try:
    import pywifi
    from pywifi import const
except ImportError:
    raise ImportError("pywifi module not found. Please install it using: pip install pywifi")

logger = logging.getLogger("OfflineNetwork.WiFiDirect")

class WiFiDirect:
    """WiFi Direct network manager for establishing P2P connections."""
    
    def __init__(self, network_name: str = "OfflineNetwork", passphrase: str = "12345678"):
        """Initialize WiFi Direct manager.
        
        Args:
            network_name: SSID for the WiFi Direct group
            passphrase: Password for the WiFi Direct group
        """
        self.network_name = network_name
        self.passphrase = passphrase
        self.wifi = pywifi.PyWiFi()
        
        # Get the first wireless interface
        if len(self.wifi.interfaces()) == 0:
            raise RuntimeError("No wireless interfaces found")
        
        self.iface = self.wifi.interfaces()[0]
        logger.info(f"Using wireless interface: {self.iface.name()}")
        
        # Dictionary of connected peers (address -> (hostname, connection))
        self.peers: Dict[str, Tuple[str, socket.socket]] = {}
        
        # Callback for new connections
        self.on_new_connection: Optional[Callable[[str, socket.socket], None]] = None
        
        # Server socket
        self.server_socket: Optional[socket.socket] = None
        self.is_group_owner = False
        self.is_running = False
        self.server_thread: Optional[threading.Thread] = None
        self.discovery_thread: Optional[threading.Thread] = None

    def create_group(self) -> bool:
        """Create a WiFi Direct group (act as group owner).
        
        Returns:
            bool: True if group created successfully
        """
        try:
            # Disconnect if connected to any network
            if self.iface.status() == const.IFACE_CONNECTED:
                self.iface.disconnect()
                time.sleep(1)
            
            # Configure the interface to create a WiFi Direct group
            profile = pywifi.Profile()
            profile.ssid = self.network_name
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)
            profile.cipher = const.CIPHER_TYPE_CCMP
            profile.key = self.passphrase
            
            # Remove existing profiles and add the new one
            self.iface.remove_all_network_profiles()
            tmp_profile = self.iface.add_network_profile(profile)
            
            # Start the group
            logger.info(f"Creating WiFi Direct group: {self.network_name}")
            self.iface.connect(tmp_profile)
            
            # Wait for connection to establish
            for _ in range(10):
                if self.iface.status() == const.IFACE_CONNECTED:
                    logger.info("WiFi Direct group created successfully")
                    self.is_group_owner = True
                    return True
                time.sleep(1)
            
            logger.error("Failed to create WiFi Direct group")
            return False
            
        except Exception as e:
            logger.error(f"Error creating WiFi Direct group: {e}")
            return False

    def scan_and_connect(self) -> bool:
        """Scan for WiFi Direct groups and connect to the first match.
        
        Returns:
            bool: True if connected successfully
        """
        try:
            # Disconnect if connected to any network
            if self.iface.status() == const.IFACE_CONNECTED:
                self.iface.disconnect()
                time.sleep(1)
            
            # Scan for available networks
            logger.info("Scanning for WiFi Direct groups...")
            self.iface.scan()
            time.sleep(5)  # Wait for scan to complete
            
            # Get scan results
            scan_results = self.iface.scan_results()
            logger.info(f"Found {len(scan_results)} networks")
            
            # Look for our network
            for network in scan_results:
                if network.ssid == self.network_name:
                    # Create a profile for this network
                    profile = pywifi.Profile()
                    profile.ssid = network.ssid
                    profile.auth = const.AUTH_ALG_OPEN
                    profile.akm.append(const.AKM_TYPE_WPA2PSK)
                    profile.cipher = const.CIPHER_TYPE_CCMP
                    profile.key = self.passphrase
                    
                    # Connect to the network
                    self.iface.remove_all_network_profiles()
                    tmp_profile = self.iface.add_network_profile(profile)
                    self.iface.connect(tmp_profile)
                    
                    # Wait for connection to establish
                    for _ in range(10):
                        if self.iface.status() == const.IFACE_CONNECTED:
                            logger.info(f"Connected to WiFi Direct group: {network.ssid}")
                            return True
                        time.sleep(1)
            
            logger.info("No matching WiFi Direct groups found")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to WiFi Direct group: {e}")
            return False

    def start_server(self, port: int = 8000) -> bool:
        """Start a server socket to accept connections from peers.
        
        Args:
            port: Port number to listen on
            
        Returns:
            bool: True if server started successfully
        """
        if self.server_socket:
            logger.warning("Server already running")
            return False
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            self.is_running = True
            
            logger.info(f"Server started on port {port}")
            
            # Start a thread to accept connections
            self.server_thread = threading.Thread(target=self._accept_connections)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            self.server_socket = None
            return False

    def _accept_connections(self) -> None:
        """Accept incoming connections from peers."""
        while self.is_running and self.server_socket:
            try:
                client_sock, addr = self.server_socket.accept()
                addr_str = f"{addr[0]}:{addr[1]}"
                logger.info(f"New connection from {addr_str}")
                
                # Get the client's hostname
                try:
                    # First message should be the hostname
                    hostname = client_sock.recv(1024).decode('utf-8')
                    logger.info(f"Client {addr_str} identified as {hostname}")
                    
                    # Add to peers
                    self.peers[addr_str] = (hostname, client_sock)
                    
                    # Start a thread to handle communication with this peer
                    threading.Thread(target=self._handle_peer, 
                                    args=(addr_str, client_sock), 
                                    daemon=True).start()
                    
                    # Notify callback if registered
                    if self.on_new_connection:
                        self.on_new_connection(hostname, client_sock)
                        
                except Exception as e:
                    logger.error(f"Error during handshake with {addr_str}: {e}")
                    client_sock.close()
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error accepting connection: {e}")
                    
    def _handle_peer(self, addr_str: str, sock: socket.socket) -> None:
        """Handle communication with a peer.
        
        Args:
            addr_str: String representation of peer's address
            sock: Socket connected to the peer
        """
        try:
            while self.is_running:
                data = sock.recv(4096)
                if not data:
                    logger.info(f"Connection closed by peer {addr_str}")
                    break
                
                # Process received data here
                # This would typically involve invoking callbacks or handlers
                
        except Exception as e:
            logger.error(f"Error communicating with peer {addr_str}: {e}")
        finally:
            sock.close()
            if addr_str in self.peers:
                del self.peers[addr_str]
            logger.info(f"Disconnected from peer {addr_str}")

    def connect_to_peer(self, host: str, port: int = 8000) -> Optional[socket.socket]:
        """Connect to a peer in the network.
        
        Args:
            host: Hostname or IP address of the peer
            port: Port number the peer is listening on
            
        Returns:
            Optional[socket.socket]: Socket object if connected, None otherwise
        """
        try:
            # Create socket and connect
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            
            # Send hostname
            hostname = socket.gethostname()
            client_socket.sendall(hostname.encode('utf-8'))
            
            # Add to peers
            addr_str = f"{host}:{port}"
            self.peers[addr_str] = (host, client_socket)
            
            # Start a thread to handle communication
            threading.Thread(target=self._handle_peer, 
                            args=(addr_str, client_socket), 
                            daemon=True).start()
            
            logger.info(f"Connected to peer {host}:{port}")
            return client_socket
            
        except Exception as e:
            logger.error(f"Error connecting to peer {host}:{port}: {e}")
            return None

    def discover_peers(self) -> None:
        """Start a thread to discover peers on the network."""
        if self.discovery_thread and self.discovery_thread.is_alive():
            logger.warning("Discovery already running")
            return
        
        self.discovery_thread = threading.Thread(target=self._discover_peers_thread)
        self.discovery_thread.daemon = True
        self.discovery_thread.start()
        logger.info("Started peer discovery")

    def _discover_peers_thread(self) -> None:
        """Thread function to discover peers using socket broadcasting."""
        try:
            # Get local IP address
            local_ip = self._get_local_ip()
            if not local_ip:
                logger.error("Could not determine local IP address")
                return
            
            # Extract network prefix
            ip_parts = local_ip.split('.')
            network_prefix = '.'.join(ip_parts[:3])
            
            logger.info(f"Scanning network {network_prefix}.0/24 for peers")
            
            # Scan all IPs in the subnet
            for i in range(1, 255):
                if not self.is_running:
                    break
                
                target_ip = f"{network_prefix}.{i}"
                if target_ip != local_ip:
                    try:
                        # Try to connect with a short timeout
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.settimeout(0.1)
                        result = client_socket.connect_ex((target_ip, 8000))
                        
                        if result == 0:
                            logger.info(f"Found peer at {target_ip}, attempting to connect")
                            client_socket.close()
                            self.connect_to_peer(target_ip)
                        else:
                            client_socket.close()
                            
                    except Exception:
                        pass
            
            logger.info("Peer discovery completed")
            
        except Exception as e:
            logger.error(f"Error in peer discovery: {e}")

    def _get_local_ip(self) -> Optional[str]:
        """Get the local IP address of the WiFi interface.
        
        Returns:
            Optional[str]: IP address as string or None if not found
        """
        try:
            # Create a temporary socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Doesn't actually send data
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            # Alternative method if the above fails
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except Exception:
                return None

    def send_to_peer(self, peer_addr: str, data: bytes) -> bool:
        """Send data to a specific peer.
        
        Args:
            peer_addr: Address of the peer (as stored in self.peers)
            data: Data to send
            
        Returns:
            bool: True if data sent successfully
        """
        if peer_addr not in self.peers:
            logger.error(f"Peer {peer_addr} not found")
            return False
        
        try:
            _, sock = self.peers[peer_addr]
            sock.sendall(data)
            return True
        except Exception as e:
            logger.error(f"Error sending data to peer {peer_addr}: {e}")
            return False

    def broadcast(self, data: bytes) -> None:
        """Broadcast data to all connected peers.
        
        Args:
            data: Data to broadcast
        """
        for peer_addr, (_, sock) in list(self.peers.items()):
            try:
                sock.sendall(data)
            except Exception as e:
                logger.error(f"Error broadcasting to peer {peer_addr}: {e}")
                # Remove failed peer
                sock.close()
                del self.peers[peer_addr]

    def stop(self) -> None:
        """Stop the network manager and close all connections."""
        self.is_running = False
        
        # Close all peer connections
        for _, (_, sock) in list(self.peers.items()):
            try:
                sock.close()
            except Exception:
                pass
        self.peers.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
        
        # Disconnect from WiFi
        if self.iface.status() == const.IFACE_CONNECTED:
            self.iface.disconnect()
        
        logger.info("WiFi Direct network manager stopped") 