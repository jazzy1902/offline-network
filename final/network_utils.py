import os
import time
import socket
import subprocess
import win32com.client
import pywifi
from pywifi import const
import threading
import ipaddress
import random

# Network configuration
MESH_SSID_PREFIX = "DISASTER_MESH_"
MESH_PASSWORD = "disaster_mesh_1234"
MESH_PORT = 5555
BROADCAST_PORT = 5556
DEVICE_DISCOVERY_INTERVAL = 10  # seconds

class MeshNetworkManager:
    """Manages mesh network connectivity with minimal user intervention."""
    
    def __init__(self, callback=None):
        self.callback = callback  # Callback for status updates
        self.connected = False
        self.is_host = False
        self.current_ssid = None
        self.auto_connect_thread = None
        self.keep_running = True
        self.connection_attempts = 0
        self.max_attempts = 3
    
    def log(self, message):
        """Log a message and send it to the callback if available."""
        print(message)
        if self.callback:
            self.callback(message)
    
    def start(self):
        """Start automatic network management."""
        self.keep_running = True
        self.auto_connect_thread = threading.Thread(target=self._auto_connect)
        self.auto_connect_thread.daemon = True
        self.auto_connect_thread.start()
        self.log("Network manager started")
    
    def stop(self):
        """Stop automatic network management."""
        self.keep_running = False
        if self.auto_connect_thread and self.auto_connect_thread.is_alive():
            self.auto_connect_thread.join(2)  # Wait up to 2 seconds
        if self.is_host:
            self._stop_hotspot()
        self.log("Network manager stopped")
    
    def _auto_connect(self):
        """Automatically manage network connectivity."""
        while self.keep_running:
            try:
                # If we're already connected to a mesh network, stay connected
                if self.connected and self.current_ssid:
                    self.log(f"Currently connected to mesh network: {self.current_ssid}")
                    time.sleep(30)  # Check less frequently if already connected
                    continue
                
                # Try to find and connect to existing mesh networks
                self.log("Scanning for existing mesh networks...")
                mesh_networks = self._find_mesh_networks()
                
                if mesh_networks:
                    # Try to connect to the first mesh network
                    network = mesh_networks[0]
                    self.log(f"Found mesh network: {network.ssid}. Connecting...")
                    
                    if self._connect_to_network(network.ssid, MESH_PASSWORD):
                        self.connected = True
                        self.is_host = False
                        self.current_ssid = network.ssid
                        self.connection_attempts = 0
                        self.log(f"Successfully connected to {network.ssid}")
                        time.sleep(30)  # Wait before next check
                        continue
                    else:
                        self.log(f"Failed to connect to {network.ssid}")
                
                # If no networks found or connection failed, try to create a hotspot
                if not self.connected:
                    self.connection_attempts += 1
                    
                    # If we've tried multiple times recently, wait longer to avoid rapid switching
                    if self.connection_attempts > self.max_attempts:
                        self.log("Multiple connection attempts failed. Waiting before trying again...")
                        time.sleep(60)  # Wait longer between attempts
                        self.connection_attempts = 0
                        continue
                    
                    # Try to become a hotspot
                    self.log("No mesh networks found. Attempting to create a hotspot...")
                    created, ssid = self._create_hotspot()
                    
                    if created:
                        self.connected = True
                        self.is_host = True
                        self.current_ssid = ssid
                        self.log(f"Created hotspot: {ssid}")
                        time.sleep(30)  # Wait before next check
                    else:
                        self.log("Failed to create hotspot. Will try again shortly.")
                        time.sleep(10)  # Wait before next attempt
            
            except Exception as e:
                self.log(f"Error in auto-connect: {e}")
                time.sleep(15)  # Wait before next attempt
    
    def _find_mesh_networks(self):
        """Find available mesh networks."""
        try:
            wifi = pywifi.PyWiFi()
            iface = wifi.interfaces()[0]
            
            iface.scan()
            time.sleep(3)
            
            scan_results = iface.scan_results()
            mesh_networks = []
            
            for network in scan_results:
                if network.ssid and (network.ssid.startswith(MESH_SSID_PREFIX) or 
                                    any(keyword in network.ssid.lower() for keyword in ["disaster", "mesh", "emergency"])):
                    mesh_networks.append(network)
            
            # Sort by signal strength
            mesh_networks.sort(key=lambda x: x.signal, reverse=True)
            return mesh_networks
        
        except Exception as e:
            self.log(f"Error scanning for networks: {e}")
            return []
    
    def _connect_to_network(self, ssid, password):
        """Connect to a specific WiFi network."""
        try:
            wifi = pywifi.PyWiFi()
            iface = wifi.interfaces()[0]
            
            profile = pywifi.Profile()
            profile.ssid = ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)
            profile.cipher = const.CIPHER_TYPE_CCMP
            profile.key = password
            
            # Remove existing profiles to avoid conflicts
            iface.remove_all_network_profiles()
            tmp_profile = iface.add_network_profile(profile)
            
            # Connect to the network
            iface.connect(tmp_profile)
            
            # Wait for connection
            for _ in range(10):  # Try for up to 10 seconds
                time.sleep(1)
                if iface.status() == const.IFACE_CONNECTED:
                    return True
            
            return False
        
        except Exception as e:
            self.log(f"Error connecting to network: {e}")
            return False
    
    def _create_hotspot(self):
        """Create a WiFi hotspot with mesh network SSID."""
        try:
            # Generate a unique SSID with a random element to avoid conflicts
            machine_id = get_short_id()
            random_suffix = str(random.randint(100, 999))
            ssid = f"{MESH_SSID_PREFIX}{machine_id}_{random_suffix}"
            
            # First try the Windows 10+ Mobile Hotspot API
            try:
                # Using PowerShell to configure the hotspot
                commands = [
                    "powershell",
                    "-Command",
                    f'Add-Type -AssemblyName System.Runtime.WindowsRuntime; ' +
                    f'$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? ' +
                    f'{{$_.Name -eq \'AsTask\' -and $_.GetParameters().Count -eq 1 -and ' +
                    f'$_.GetParameters()[0].ParameterType.Name -eq \'IAsyncOperation`1\'}})' +
                    f'[0]; Function StartHotspot($ssid, $key) {{' +
                    f'$connectionProfile = [Windows.Networking.Connectivity.NetworkInformation,' +
                    f'Windows.Networking.Connectivity,ContentType=WindowsRuntime]::GetInternetConnectionProfile(); ' +
                    f'$tetheringManager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,' +
                    f'Windows.Networking.NetworkOperators,ContentType=WindowsRuntime]::CreateFromConnectionProfile(' +
                    f'$connectionProfile); $task = $tetheringManager.StartTetheringAsync().AsTask(); ' +
                    f'$task.Wait(-1); }}; StartHotspot -ssid \'{ssid}\' -key \'{MESH_PASSWORD}\''
                ]
                
                result = subprocess.run(commands, capture_output=True, text=True)
                
                # Check if the hotspot was started successfully
                if result.returncode == 0 and "error" not in result.stdout.lower():
                    return True, ssid
                else:
                    # Fall back to the netsh method for older Windows
                    return self._create_hotspot_netsh(ssid)
            
            except Exception as e:
                self.log(f"Error with PowerShell hotspot creation: {e}")
                # Fall back to the netsh method
                return self._create_hotspot_netsh(ssid)
        
        except Exception as e:
            self.log(f"Error creating hotspot: {e}")
            return False, None
    
    def _create_hotspot_netsh(self, ssid):
        """Create a hotspot using the netsh command (Windows legacy method)."""
        try:
            # Stop any existing hosted network
            subprocess.run(['netsh', 'wlan', 'stop', 'hostednetwork'], capture_output=True)
            time.sleep(1)
            
            # Set up new hosted network
            setup_result = subprocess.run(
                ['netsh', 'wlan', 'set', 'hostednetwork', 'mode=allow', f'ssid={ssid}', f'key={MESH_PASSWORD}'],
                capture_output=True
            )
            
            if setup_result.returncode != 0:
                self.log("Failed to set up hosted network")
                return False, None
            
            # Start the hosted network
            start_result = subprocess.run(['netsh', 'wlan', 'start', 'hostednetwork'], capture_output=True)
            output = start_result.stdout.decode() if start_result.stdout else ""
            
            if "hosted network started" in output.lower():
                return True, ssid
            else:
                # Final fallback: open the Mobile Hotspot settings for the user
                self._open_hotspot_settings()
                return True, ssid  # Return true even though we're not sure, to avoid constant retries
        
        except Exception as e:
            self.log(f"Error creating netsh hotspot: {e}")
            # Try to open the settings as a last resort
            self._open_hotspot_settings()
            return False, None
    
    def _open_hotspot_settings(self):
        """Open the Windows Mobile Hotspot settings."""
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.Run("ms-settings:network-mobilehotspot")
            self.log("Mobile hotspot settings opened. Please enable the hotspot manually.")
        except Exception as e:
            self.log(f"Error opening hotspot settings: {e}")
    
    def _stop_hotspot(self):
        """Stop the WiFi hotspot."""
        if not self.is_host:
            return
        
        try:
            # Try to stop the hotspot using netsh
            subprocess.run(['netsh', 'wlan', 'stop', 'hostednetwork'], capture_output=True)
            self.log("Hotspot stopped")
        except Exception as e:
            self.log(f"Error stopping hotspot: {e}")
            

def get_machine_id():
    """Get a unique identifier for this machine."""
    return socket.gethostname()

def get_short_id():
    """Get a shortened unique identifier for this machine."""
    return get_machine_id().replace('-', '')[:8]

def get_ip_addresses():
    """Get all IP addresses assigned to this machine using standard socket library."""
    addresses = []
    try:
        # Get hostname
        hostname = socket.gethostname()
        
        # Get all addresses associated with the hostname
        host_info = socket.getaddrinfo(hostname, None)
        
        # Extract IPv4 addresses
        for info in host_info:
            addr = info[4][0]
            # Filter out loopback addresses and IPv6
            if not addr.startswith('127.') and ':' not in addr:
                if addr not in addresses:
                    addresses.append(addr)
                    
        # If no addresses found, try another method
        if not addresses:
            # This is a somewhat hacky way to get the IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Doesn't need to be reachable
                s.connect(('10.255.255.255', 1))
                ip = s.getsockname()[0]
                if ip not in addresses and not ip.startswith('127.'):
                    addresses.append(ip)
            except:
                pass
            finally:
                s.close()
    except Exception as e:
        print(f"Error getting IP addresses: {e}")
        
    return addresses

def get_subnet_prefix():
    """Get the subnet prefix for broadcasting."""
    addresses = get_ip_addresses()
    if not addresses:
        return "255.255.255.255"  # Fallback to global broadcast
    
    try:
        # Get the first address and calculate its network
        ip = addresses[0]
        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        return str(network.broadcast_address)
    except:
        return "255.255.255.255"  # Fallback to global broadcast 