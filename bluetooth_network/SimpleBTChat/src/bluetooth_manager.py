"""Bluetooth connectivity manager for the chat application."""

import random
import socket
import subprocess
import threading
import time
from typing import Callable, List, Optional, Tuple

from .config import BT_PORT, BUFFER_SIZE, ENCODING
from .message import Message


class BluetoothManager:
    """Manages Bluetooth connections and communication."""
    
    def __init__(self):
        """Initialize the Bluetooth manager."""
        self.device_name = socket.gethostname()
        self.server_socket = None
        self.client_socket = None
        self.connected = False
        self.peer_name = None
        self.is_server = False
        
        # Callbacks for events
        self.on_connected = None
        self.on_disconnected = None
        self.on_connection_error = None
        self.on_message_received = None
        self.on_status_changed = None
        
        # Receiving thread
        self.receiving_thread = None
    
    def start_server(self) -> None:
        """Start the application in server mode."""
        self._update_status("Starting server...")
        
        try:
            # Create a Bluetooth server socket
            self.server_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.server_socket.bind(("", BT_PORT))
            self.server_socket.listen(1)
            
            self.is_server = True
            self._update_status("Waiting for connection...")
            
            # Accept connection in a separate thread
            threading.Thread(target=self._accept_connection, daemon=True).start()
            
        except Exception as e:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            
            if self.on_connection_error:
                self.on_connection_error(f"Failed to start server: {str(e)}")
            self._update_status("Server start failed")
    
    def _accept_connection(self) -> None:
        """Accept incoming Bluetooth connection."""
        try:
            # Set a timeout for accept() to allow checking if we should stop
            self.server_socket.settimeout(1.0)
            
            while not self.connected:
                try:
                    # Accept a connection
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Connection established
                    self.client_socket = client_socket
                    self.peer_name = client_address[0]  # Use address as name initially
                    
                    # Set up the connection
                    self._setup_connection()
                    break
                    
                except socket.timeout:
                    # Check if user canceled the connection
                    if self.server_socket is None:
                        break
                    continue
                    
        except Exception as e:
            if self.on_connection_error:
                self.on_connection_error(f"Failed to accept connection: {str(e)}")
            self._update_status("Connection failed")
            self.disconnect()
    
    def connect_to_device(self, target_mac: str) -> None:
        """Connect to a Bluetooth device.
        
        Args:
            target_mac: MAC address of the target device
        """
        self._update_status(f"Connecting to {target_mac}...")
        
        try:
            # Create a Bluetooth client socket
            self.client_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.client_socket.connect((target_mac, BT_PORT))
            
            self.is_server = False
            self.peer_name = target_mac  # Use address as initial name
            
            # Set up the connection
            self._setup_connection()
            
        except Exception as e:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            
            if self.on_connection_error:
                self.on_connection_error(f"Failed to connect: {str(e)}")
            self._update_status("Connection failed")
    
    def _setup_connection(self) -> None:
        """Set up the connection after it's established."""
        self.connected = True
        self._update_status("Connected")
        
        # Send our device name
        self.send_message(Message(Message.TYPE_NAME, self.device_name))
        
        # Start message receiving thread
        self.receiving_thread = threading.Thread(target=self._receive_data, daemon=True)
        self.receiving_thread.start()
        
        # Call the connected callback
        if self.on_connected:
            self.on_connected(self.peer_name)
    
    def disconnect(self) -> None:
        """Disconnect from the current Bluetooth connection."""
        # Check if actually connected or server running
        if not self.connected and not self.server_socket:
            return
        
        # Send disconnect message if connected
        if self.connected:
            try:
                self.send_message(Message(Message.TYPE_DISCONNECT))
            except:
                pass
        
        # Store peer name for the callback
        peer = self.peer_name
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        # Update state
        self.connected = False
        self.is_server = False
        self.peer_name = None
        
        self._update_status("Disconnected")
        
        # Call the disconnected callback
        if self.on_disconnected and peer:
            self.on_disconnected(peer)
    
    def send_message(self, message: 'Message') -> None:
        """Send a message over the Bluetooth connection.
        
        Args:
            message: Message to send
        """
        if not self.connected or not self.client_socket:
            raise ConnectionError("Not connected to any device")
        
        try:
            # Send the message
            data = message.encode()
            self.client_socket.send(data)
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {str(e)}")
    
    def _receive_data(self) -> None:
        """Receive and process data from the Bluetooth connection."""
        while self.connected and self.client_socket:
            try:
                # Set a timeout to avoid blocking indefinitely
                self.client_socket.settimeout(1.0)
                
                # Receive data
                data = self.client_socket.recv(BUFFER_SIZE)
                
                # Check if connection closed
                if not data:
                    # Use threading to avoid deadlocks
                    threading.Thread(target=self.disconnect, daemon=True).start()
                    break
                
                # Decode and process the data
                try:
                    # Convert bytes to Message object
                    message = Message.from_bytes(data)
                    
                    # Handle special message types
                    if message.type == Message.TYPE_NAME:
                        # Name exchange
                        self.peer_name = message.content
                    elif message.type == Message.TYPE_DISCONNECT:
                        # Peer requested disconnect
                        threading.Thread(target=self.disconnect, daemon=True).start()
                        break
                    
                    # Call the message received callback
                    if self.on_message_received:
                        self.on_message_received(message)
                        
                except Exception as e:
                    print(f"Error processing message: {str(e)}")
                
            except socket.timeout:
                # This is normal, just try again
                continue
            except Exception as e:
                # Handle other errors
                print(f"Error receiving data: {str(e)}")
                threading.Thread(target=self.disconnect, daemon=True).start()
                break
    
    def discover_devices(self) -> List[Tuple[str, str]]:
        """Discover nearby Bluetooth devices.
        
        Returns:
            List[Tuple[str, str]]: List of (name, address) tuples of discovered devices
        """
        # First, create some simulated devices for demo purposes
        devices = [
            ("Phone", "12:34:56:78:90:AB"),
            ("Laptop", "AB:CD:EF:12:34:56"),
            ("Tablet", "98:76:54:32:10:EF")
        ]
        
        # Try to get real devices if possible
        try:
            real_devices = self._get_real_devices()
            if real_devices:
                devices = real_devices
        except Exception as e:
            print(f"Error discovering real devices: {str(e)}")
        
        return devices
    
    def _get_real_devices(self) -> List[Tuple[str, str]]:
        """Get list of real Bluetooth devices.
        
        Returns:
            List[Tuple[str, str]]: List of (name, address) tuples
        """
        try:
            # Windows-specific discovery using PowerShell
            cmd = "powershell \"Get-PnpDevice | Where-Object {$_.FriendlyName -like '*bluetooth*' -and $_.Status -eq 'OK'} | Select-Object FriendlyName, DeviceID\""
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse the output
            devices = []
            for line in result.stdout.splitlines():
                if ":" in line:  # Simple way to check for device entries
                    parts = line.strip().split("  ")
                    parts = [p for p in parts if p.strip()]
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        # Generate a fake MAC since we don't have real ones
                        addr = ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])
                        devices.append((name, addr))
            
            return devices
        except:
            return []
    
    def _update_status(self, status: str) -> None:
        """Update the connection status.
        
        Args:
            status: Status string
        """
        if self.on_status_changed:
            self.on_status_changed(status) 