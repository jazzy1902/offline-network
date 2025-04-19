"""
Network utilities for the Disaster Mesh Network application.

This module provides utilities for network management, including:
- Creating and managing WiFi hotspots
- Connecting to existing networks
- Getting network information
"""

import os
import re
import uuid
import socket
import logging
import subprocess
import time
import ipaddress
from typing import List, Optional, Dict, Any, Union
import platform

logger = logging.getLogger(__name__)

# Constants
MESH_NETWORK_PREFIX = "DISASTER_MESH_"
DEFAULT_PASSWORD = "disaster12345"  # Default password for hotspots

class NetworkManager:
    """
    Manages network connections and hotspot creation for the mesh network.
    
    This class handles:
    - Scanning for existing mesh networks
    - Connecting to mesh networks
    - Creating a hotspot when no existing networks are found
    """
    
    def __init__(self):
        """Initialize a new NetworkManager."""
        self.running = False
        self.auto_mode = False
        self.is_hotspot_active = False
        self.current_network = None
        self.os_type = platform.system()
        
    def start(self):
        """Start the network manager."""
        if self.running:
            return
            
        self.running = True
        logger.info("Network manager started")
        
    def start_auto(self):
        """
        Start automatic network management.
        
        This will scan for existing mesh networks, connect to one if found,
        or create a hotspot if no networks are found.
        """
        if not self.running:
            self.start()
            
        self.auto_mode = True
        
        # Start auto-connect process
        try:
            self._auto_connect()
            return True
        except Exception as e:
            logger.error(f"Failed to start auto mode: {e}")
            return False
            
    def stop(self):
        """Stop the network manager."""
        if not self.running:
            return
            
        # Stop any active hotspot
        if self.is_hotspot_active:
            self._stop_hotspot()
            
        self.running = False
        self.auto_mode = False
        logger.info("Network manager stopped")
        
    def _auto_connect(self):
        """
        Automatically connect to a mesh network or create a hotspot.
        
        This method:
        1. Scans for existing mesh networks
        2. If found, connects to the strongest one
        3. If not found, creates a hotspot
        """
        # Find existing mesh networks
        networks = self._find_mesh_networks()
        
        if networks:
            # Sort by signal strength
            networks.sort(key=lambda x: x.get('signal_strength', 0), reverse=True)
            best_network = networks[0]
            
            logger.info(f"Found mesh network: {best_network['ssid']}")
            
            # Try to connect
            if self._connect_to_network(best_network['ssid'], DEFAULT_PASSWORD):
                self.current_network = best_network
                return
                
        # No networks found or connection failed, create a hotspot
        logger.info("No mesh networks found, creating hotspot")
        self._create_hotspot()
        
    def _find_mesh_networks(self) -> List[Dict[str, Any]]:
        """
        Scan for available mesh networks.
        
        Returns:
            A list of dictionaries containing network info
        """
        networks = []
        
        try:
            if self.os_type == "Windows":
                # Use netsh to get network list on Windows
                output = subprocess.check_output(
                    ["netsh", "wlan", "show", "networks"], 
                    universal_newlines=True
                )
                
                # Parse the output
                current_network = {}
                for line in output.split('\n'):
                    line = line.strip()
                    
                    if line.startswith("SSID"):
                        if current_network and current_network.get('ssid', '').startswith(MESH_NETWORK_PREFIX):
                            networks.append(current_network)
                        ssid = line.split(':', 1)[1].strip().strip('"')
                        current_network = {'ssid': ssid}
                    
                    elif line.startswith("Signal"):
                        signal_str = line.split(':', 1)[1].strip().rstrip('%')
                        current_network['signal_strength'] = int(signal_str)
                
                # Add the last network if it's a mesh network
                if current_network and current_network.get('ssid', '').startswith(MESH_NETWORK_PREFIX):
                    networks.append(current_network)
                    
            elif self.os_type == "Linux":
                # Use nmcli on Linux
                output = subprocess.check_output(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list"],
                    universal_newlines=True
                )
                
                for line in output.split('\n'):
                    if not line:
                        continue
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        ssid, signal = parts
                        if ssid.startswith(MESH_NETWORK_PREFIX):
                            networks.append({
                                'ssid': ssid,
                                'signal_strength': int(signal)
                            })
            
            elif self.os_type == "Darwin":  # macOS
                # Use airport on macOS
                output = subprocess.check_output(
                    ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                    universal_newlines=True
                )
                
                for line in output.split('\n')[1:]:  # Skip header line
                    parts = line.split()
                    if len(parts) >= 3:
                        ssid = parts[0]
                        signal = parts[2]
                        if ssid.startswith(MESH_NETWORK_PREFIX):
                            networks.append({
                                'ssid': ssid,
                                'signal_strength': int(signal)
                            })
                            
        except Exception as e:
            logger.error(f"Error scanning for networks: {e}")
            
        return networks
        
    def _connect_to_network(self, ssid: str, password: str) -> bool:
        """
        Connect to a specified WiFi network.
        
        Args:
            ssid: The network SSID
            password: The network password
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to network: {ssid}")
            
            if self.os_type == "Windows":
                # Create a temporary profile XML
                profile_path = os.path.join(os.environ['TEMP'], f"{ssid}.xml")
                profile_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
                
                with open(profile_path, 'w') as f:
                    f.write(profile_content)
                
                # Add the profile
                subprocess.check_call(
                    ["netsh", "wlan", "add", "profile", f"filename={profile_path}"]
                )
                
                # Connect using the profile
                subprocess.check_call(
                    ["netsh", "wlan", "connect", f"name={ssid}"]
                )
                
                # Clean up
                os.remove(profile_path)
                
                # Wait for connection
                time.sleep(5)
                return True
                
            elif self.os_type == "Linux":
                # Use nmcli on Linux
                subprocess.check_call([
                    "nmcli", "device", "wifi", "connect", ssid,
                    "password", password
                ])
                return True
                
            elif self.os_type == "Darwin":  # macOS
                # Use networksetup on macOS
                subprocess.check_call([
                    "networksetup", "-setairportnetwork", "en0", ssid, password
                ])
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to network {ssid}: {e}")
            return False
            
    def _create_hotspot(self) -> bool:
        """
        Create a WiFi hotspot for the mesh network.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate a unique SSID with the mesh network prefix
            machine_id = get_short_id()
            ssid = f"{MESH_NETWORK_PREFIX}{machine_id}"
            
            logger.info(f"Creating hotspot: {ssid}")
            
            if self.os_type == "Windows":
                # Check Windows version for different methods
                win_ver = platform.version()
                
                if int(win_ver.split('.')[0]) >= 10:
                    # Windows 10+ - Use modern method
                    subprocess.check_call([
                        "powershell", "-Command",
                        f"New-NetNat -Name SharedNat -InternalIPInterfaceAddressPrefix 192.168.137.0/24; "
                        f"netsh wlan set hostednetwork mode=allow ssid={ssid} key={DEFAULT_PASSWORD}; "
                        f"netsh wlan start hostednetwork"
                    ])
                else:
                    # Older Windows - Use legacy method
                    subprocess.check_call([
                        "netsh", "wlan", "set", "hostednetwork",
                        f"mode=allow", f"ssid={ssid}", f"key={DEFAULT_PASSWORD}"
                    ])
                    subprocess.check_call(["netsh", "wlan", "start", "hostednetwork"])
                
                self.is_hotspot_active = True
                return True
                
            elif self.os_type == "Linux":
                # Use nmcli on Linux
                subprocess.check_call([
                    "nmcli", "device", "wifi", "hotspot",
                    "ifname", "wlan0", "ssid", ssid, "password", DEFAULT_PASSWORD
                ])
                
                self.is_hotspot_active = True
                return True
                
            elif self.os_type == "Darwin":  # macOS
                # macOS requires additional tools, show instructions
                logger.warning("Hotspot creation on macOS requires additional setup.")
                self._open_hotspot_settings()
                return False
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to create hotspot: {e}")
            return False
            
    def _stop_hotspot(self) -> bool:
        """
        Stop the active WiFi hotspot.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_hotspot_active:
            return True
            
        try:
            logger.info("Stopping hotspot")
            
            if self.os_type == "Windows":
                subprocess.check_call(["netsh", "wlan", "stop", "hostednetwork"])
                
            elif self.os_type == "Linux":
                # Find the connection and stop it
                output = subprocess.check_output(
                    ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                    universal_newlines=True
                )
                
                for line in output.split('\n'):
                    if not line:
                        continue
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        name, conn_type = parts
                        if conn_type == "wifi" and name.startswith(MESH_NETWORK_PREFIX):
                            subprocess.check_call(["nmcli", "connection", "down", name])
                            break
                            
            self.is_hotspot_active = False
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop hotspot: {e}")
            return False
            
    def _open_hotspot_settings(self):
        """Open system settings for hotspot configuration."""
        try:
            if self.os_type == "Windows":
                os.system("start ms-settings:network-mobilehotspot")
                
            elif self.os_type == "Linux":
                os.system("nm-connection-editor")
                
            elif self.os_type == "Darwin":  # macOS
                os.system("open /System/Library/PreferencePanes/Network.prefPane")
                
        except Exception as e:
            logger.error(f"Failed to open hotspot settings: {e}")

# Utility functions

def get_machine_id() -> str:
    """
    Get a unique identifier for this machine.
    
    Returns:
        A UUID string based on the machine's hardware
    """
    try:
        # Try to get a stable machine ID
        if os.path.exists('/etc/machine-id'):
            with open('/etc/machine-id', 'r') as f:
                return f.read().strip()
        elif os.path.exists('/var/lib/dbus/machine-id'):
            with open('/var/lib/dbus/machine-id', 'r') as f:
                return f.read().strip()
        else:
            # Fall back to MAC address based UUID
            mac = uuid.getnode()
            return str(uuid.UUID(int=mac))
    except:
        # Last resort - random UUID
        return str(uuid.uuid4())

def get_short_id() -> str:
    """
    Get a shortened version of the machine ID for display purposes.
    
    Returns:
        A short (6 character) ID
    """
    machine_id = get_machine_id()
    # Take first 6 characters of the hex representation
    return machine_id.replace('-', '')[:6].upper()

def get_ip_addresses() -> List[str]:
    """
    Get all IP addresses for this machine.
    
    Returns:
        A list of IP address strings
    """
    addresses = []
    
    try:
        # Get all network interfaces
        interfaces = socket.getaddrinfo(socket.gethostname(), None)
        
        for interface in interfaces:
            ip = interface[4][0]
            # Filter out localhost and IPv6
            if ip != '127.0.0.1' and not ':' in ip:
                addresses.append(ip)
                
        # If no addresses found, try a different method
        if not addresses:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            addresses.append(s.getsockname()[0])
            s.close()
            
    except Exception as e:
        logger.error(f"Error getting IP addresses: {e}")
        
    return addresses

def get_subnet_prefix(ip_address: str) -> Optional[ipaddress.IPv4Network]:
    """
    Get the subnet prefix for an IP address.
    
    Args:
        ip_address: The IP address to get the subnet for
        
    Returns:
        An IPv4Network object representing the subnet, or None if not found
    """
    try:
        # Default to a /24 network for simplicity
        return ipaddress.IPv4Network(f"{ip_address.rsplit('.', 1)[0]}.0/24", strict=False)
    except Exception as e:
        logger.error(f"Error getting subnet for {ip_address}: {e}")
        return None 