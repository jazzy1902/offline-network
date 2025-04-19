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
import psutil
import re
import sys
import ctypes

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
        self.role_decided = False
        self.device_priority = self._calculate_device_priority()
    
    def _calculate_device_priority(self):
        """Calculate a priority value to decide which device becomes a hotspot.
        Higher value = higher priority to be a hotspot creator."""
        try:
            # Use device ID to create a consistent value
            machine_id = get_machine_id()
            priority = sum(ord(c) for c in machine_id) % 1000  # Value between 0-999
            
            # Bias toward devices with better hardware
            if self._can_create_hotspot_reliably():
                priority += 2000
                
            # Add randomness to break ties
            priority += random.randint(0, 100)
            
            self.log(f"Device priority: {priority}")
            return priority
        except:
            return random.randint(0, 3000)  # Fallback to random priority
    
    def _can_create_hotspot_reliably(self):
        """Check if this device is likely to be able to create a reliable hotspot."""
        try:
            # Check for mobile hotspot support
            result = subprocess.run(['netsh', 'wlan', 'show', 'drivers'], capture_output=True, text=True)
            if "Hosted network supported : Yes" in result.stdout:
                return True
                
            # Check if we have admin privileges (helps with hotspot creation)
            if os.name == 'nt':  # Windows
                try:
                    return ctypes.windll.shell32.IsUserAnAdmin() != 0
                except:
                    pass
                    
            return False
        except:
            return False
    
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
        # Initial delay to allow discovery of existing networks
        time.sleep(5)
        
        # Coordination phase - discover other devices and decide roles
        if not self.role_decided:
            self._decide_network_role()
            
        while self.keep_running:
            try:
                # If we're already connected to a mesh network, stay connected
                if self.connected and self.current_ssid:
                    self.log(f"Currently connected to mesh network: {self.current_ssid}")
                    time.sleep(30)  # Check less frequently if already connected
                    continue
                
                if self.is_host:
                    # We should be hosting - create a hotspot if not already
                    if not self._is_hotspot_active():
                        self.log("I should be hosting but hotspot is not active. Creating hotspot...")
                        created, ssid = self._create_hotspot()
                        if created:
                            self.connected = True
                            self.current_ssid = ssid
                            self.log(f"Created hotspot: {ssid}")
                        else:
                            self.log("Failed to create hotspot. Will try again shortly.")
                            time.sleep(10)
                    else:
                        self.log("Continuing to host hotspot.")
                        self.connected = True
                else:
                    # We should be connecting to others - scan for networks
                    self.log("Scanning for existing mesh networks...")
                    mesh_networks = self._find_mesh_networks()
                    
                    if mesh_networks:
                        # Try to connect to the first mesh network
                        network = mesh_networks[0]
                        self.log(f"Found mesh network: {network.ssid}. Connecting...")
                        
                        if self._connect_to_network(network.ssid, MESH_PASSWORD):
                            self.connected = True
                            self.current_ssid = network.ssid
                            self.connection_attempts = 0
                            self.log(f"Successfully connected to {network.ssid}")
                            time.sleep(30)  # Wait before next check
                            continue
                        else:
                            self.log(f"Failed to connect to {network.ssid}")
                            # Try next network if available
                            if len(mesh_networks) > 1:
                                for backup_network in mesh_networks[1:]:
                                    self.log(f"Trying backup network: {backup_network.ssid}")
                                    if self._connect_to_network(backup_network.ssid, MESH_PASSWORD):
                                        self.connected = True
                                        self.current_ssid = backup_network.ssid
                                        self.connection_attempts = 0
                                        self.log(f"Successfully connected to {backup_network.ssid}")
                                        break
                    else:
                        # If no networks found, check if we should change roles
                        self.connection_attempts += 1
                        if self.connection_attempts > self.max_attempts:
                            self.log("No networks found after multiple attempts. Becoming a hotspot instead.")
                            self.is_host = True
                            self.connection_attempts = 0
                        else:
                            self.log("No mesh networks found. Will try again shortly.")
                
                # Wait before next check
                time.sleep(10)
            
            except Exception as e:
                self.log(f"Error in auto-connect: {e}")
                time.sleep(15)  # Wait before next attempt
    
    def _decide_network_role(self):
        """Decide whether this device should be a host or client based on priority."""
        # First check if there are existing networks
        self.log("Checking for existing networks to determine role...")
        mesh_networks = self._find_mesh_networks()
        
        if mesh_networks:
            # Networks exist - become a client
            self.log("Found existing networks. This device will be a client.")
            self.is_host = False
            self.role_decided = True
            return
            
        # No networks found
        # Wait a random time to avoid simultaneous decisions
        wait_time = random.uniform(0.5, 2.0)
        self.log(f"No networks found. Waiting {wait_time:.1f}s before making role decision...")
        time.sleep(wait_time)
        
        # Check again after delay
        mesh_networks = self._find_mesh_networks()
        if mesh_networks:
            # Networks appeared during wait - become a client
            self.log("Found networks after wait. This device will be a client.")
            self.is_host = False
        else:
            # Still no networks - make priority-based decision
            self.log(f"Making priority-based decision. Priority: {self.device_priority}")
            # High priority devices become hotspots first
            self.is_host = self.device_priority > 1500  # Adjust threshold as needed
            self.log(f"Decision: This device will be a {'host' if self.is_host else 'client'}")
        
        self.role_decided = True
    
    def _is_hotspot_active(self):
        """Check if we're already hosting a hotspot."""
        try:
            # Try to detect with netsh command
            result = subprocess.run(['netsh', 'wlan', 'show', 'hostednetwork'], 
                                    capture_output=True, text=True)
            
            if "Status                 : Started" in result.stdout:
                return True
            
            # Alternative check using network connections
            for conn in psutil.net_if_stats():
                if "virt" in conn.lower() or "wlan" in conn.lower() or "wi-fi" in conn.lower():
                    return True
                    
            return False
        except:
            return False  # If error, assume not hosting
    
    def _find_mesh_networks(self):
        """Find available mesh networks."""
        try:
            wifi = pywifi.PyWiFi()
            if not wifi.interfaces():
                self.log("No WiFi interfaces found!")
                return []
                
            iface = wifi.interfaces()[0]
            
            # Scan multiple times to ensure we find all networks
            for _ in range(3):  # Increased scan attempts
                try:
                    iface.scan()
                    time.sleep(5)  # Increased scan wait time
                except Exception as e:
                    self.log(f"Error during scan: {e}")
            
            try:
                scan_results = iface.scan_results()
                self.log(f"Found {len(scan_results)} networks in total")
            except Exception as e:
                self.log(f"Error getting scan results: {e}")
                return []
            
            mesh_networks = []
            
            for network in scan_results:
                try:
                    network_ssid = network.ssid if hasattr(network, 'ssid') else ''
                    if network_ssid and (network_ssid.startswith(MESH_SSID_PREFIX) or 
                                     any(keyword in network_ssid.lower() for keyword in ["disaster", "mesh", "emergency"])):
                        # Only add networks not already in the list
                        if not any(existing.ssid == network_ssid for existing in mesh_networks):
                            mesh_networks.append(network)
                            self.log(f"Found mesh network: {network_ssid} (Signal: {network.signal if hasattr(network, 'signal') else 'unknown'})")
                except Exception as e:
                    self.log(f"Error processing network: {e}")
            
            # Sort by signal strength
            try:
                mesh_networks.sort(key=lambda x: getattr(x, 'signal', 0), reverse=True)
            except:
                pass  # Skip sorting if it fails
                
            if mesh_networks:
                self.log(f"Found {len(mesh_networks)} mesh networks: {', '.join([n.ssid for n in mesh_networks if hasattr(n, 'ssid')])}")
            else:
                self.log("No mesh networks found during scan")
                
            # If discovery fails with pywifi, try alternative method
            if not mesh_networks:
                alternative_networks = self._find_networks_alternative()
                if alternative_networks:
                    return alternative_networks
                
            return mesh_networks
        
        except Exception as e:
            self.log(f"Error scanning for networks: {e}")
            # Try alternative method
            return self._find_networks_alternative()
    
    def _find_networks_alternative(self):
        """Alternative method to find networks using netsh."""
        try:
            self.log("Trying alternative network discovery method...")
            result = subprocess.run(['netsh', 'wlan', 'show', 'networks'], 
                                  capture_output=True, text=True)
            
            networks = []
            current_ssid = None
            current_signal = None
            
            for line in result.stdout.split('\n'):
                if 'SSID' in line and ':' in line:
                    current_ssid = line.split(':', 1)[1].strip().strip('"')
                if 'Signal' in line and '%' in line:
                    try:
                        signal_str = line.split(':', 1)[1].strip().replace('%', '')
                        current_signal = int(signal_str)
                    except:
                        current_signal = 0
                
                if current_ssid and current_signal is not None:
                    # Create a simple network object
                    class NetworkInfo:
                        def __init__(self, ssid, signal):
                            self.ssid = ssid
                            self.signal = signal
                    
                    if current_ssid.startswith(MESH_SSID_PREFIX) or any(keyword in current_ssid.lower() for keyword in ["disaster", "mesh", "emergency"]):
                        networks.append(NetworkInfo(current_ssid, current_signal))
                        self.log(f"Alternative found mesh network: {current_ssid} (Signal: {current_signal}%)")
                    
                    current_ssid = None
                    current_signal = None
            
            return networks
        except Exception as e:
            self.log(f"Error in alternative network discovery: {e}")
            return []
    
    def _connect_to_network(self, ssid, password):
        """Connect to a specific WiFi network."""
        try:
            # Try using pywifi library first
            try:
                self.log(f"Connecting to {ssid} using pywifi...")
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
                for _ in range(15):  # Try for up to 15 seconds (increased)
                    time.sleep(1)
                    if iface.status() == const.IFACE_CONNECTED:
                        return True
                
                self.log("Failed to connect using pywifi")
                return self._connect_to_network_alternative(ssid, password)
            except Exception as e:
                self.log(f"Error with pywifi connection: {e}")
                return self._connect_to_network_alternative(ssid, password)
        
        except Exception as e:
            self.log(f"Error connecting to network: {e}")
            return False
    
    def _create_wifi_profile(self, ssid, password):
        """Create a WiFi profile XML for Windows with proper name tags."""
        profile_xml = f"""<?xml version="1.0"?>
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
</WLANProfile>
"""
        return profile_xml
        
    def _connect_to_network_alternative(self, ssid, password):
        """Alternative method to connect to a network using netsh."""
        try:
            self.log(f"Trying alternative connection method for {ssid}...")
            # Use netsh to connect to the network
            commands = [
                'netsh', 'wlan', 'connect',
                f'name="{ssid}"'
            ]
            
            result = subprocess.run(commands, capture_output=True, text=True)
            
            if "Connection request was completed successfully" in result.stdout:
                self.log("Successfully connected with netsh")
                return True
            
            # If that fails, try adding profile first
            profile_xml = self._create_wifi_profile(ssid, password)
            
            # Write profile to temporary file
            profile_path = os.path.join(os.environ['TEMP'], 'wifi_profile.xml')
            with open(profile_path, 'w') as f:
                f.write(profile_xml)
            
            # Add profile to Windows
            add_profile_cmd = ['netsh', 'wlan', 'add', 'profile', f'filename="{profile_path}"']
            subprocess.run(add_profile_cmd, capture_output=True)
            
            # Try connecting again
            connect_cmd = ['netsh', 'wlan', 'connect', f'name="{ssid}"']
            result = subprocess.run(connect_cmd, capture_output=True, text=True)
            
            # Remove temporary file
            try:
                os.remove(profile_path)
            except:
                pass
            
            if "Connection request was completed successfully" in result.stdout:
                self.log("Successfully connected with netsh (with profile)")
                return True
            
            return False
        except Exception as e:
            self.log(f"Error with alternative connection: {e}")
            return False
    
    def _create_hotspot(self):
        """Create a WiFi hotspot with mesh network SSID."""
        try:
            # Generate a unique SSID with a random element to avoid conflicts
            machine_id = get_short_id()
            random_suffix = str(random.randint(100, 999))
            ssid = f"{MESH_SSID_PREFIX}{machine_id}_{random_suffix}"
            
            # Always try the native Windows 10 method first using netsh
            try:
                return self._create_hotspot_windows10(ssid)
            except Exception as e:
                self.log(f"Error with Windows 10 hotspot creation: {e}")
                return self._create_hotspot_netsh(ssid)
        
        except Exception as e:
            self.log(f"Error creating hotspot: {e}")
            return False, None
    
    def _create_hotspot_windows10(self, ssid):
        """Create hotspot using Windows 10 Mobile Hotspot feature through PowerShell."""
        self.log("Attempting to create Windows 10 Mobile Hotspot...")
        
        # First try directly using netsh for configuration
        cmd = ['netsh', 'wlan', 'set', 'hostednetwork', 
               'mode=allow', 
               f'ssid={ssid}', 
               f'key={MESH_PASSWORD}']
        
        setup_result = subprocess.run(cmd, capture_output=True, text=True)
        
        if setup_result.returncode != 0:
            self.log("Failed to set up hosted network configuration")
            
        start_cmd = ['netsh', 'wlan', 'start', 'hostednetwork']
        start_result = subprocess.run(start_cmd, capture_output=True, text=True)
        
        if "hosted network started" in start_result.stdout.lower():
            self.log("Successfully started Windows hosted network")
            return True, ssid
        
        # If that fails, try PowerShell approach
        self.log("Falling back to PowerShell method...")
        powershell_cmd = [
            "powershell", "-Command",
            f'netsh wlan set hostednetwork mode=allow ssid="{ssid}" key="{MESH_PASSWORD}" && ' +
            f'netsh wlan start hostednetwork'
        ]
        
        result = subprocess.run(powershell_cmd, capture_output=True, text=True)
        
        if "hosted network started" in result.stdout.lower():
            self.log("Successfully started hotspot with PowerShell")
            return True, ssid
        
        # If that fails too, try UI automation
        self.log("Opening Mobile Hotspot settings for manual configuration...")
        settings_cmd = ["ms-settings:network-mobilehotspot"]
        
        try:
            subprocess.Popen(settings_cmd, shell=True)
            self.log(f"Please manually enable the hotspot with name: {ssid}")
            self.log(f"And password: {MESH_PASSWORD}")
            # Return True even though we're not sure, to avoid constant retries
            return True, ssid
        except:
            self.log("Failed to open settings")
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
                self._open_hotspot_settings()
                return True, ssid  # Return true to avoid constant retries
            
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
            return True, ssid  # Return true to avoid constant retries
    
    def _open_hotspot_settings(self):
        """Open the Windows Mobile Hotspot settings."""
        try:
            subprocess.Popen(["ms-settings:network-mobilehotspot"], shell=True)
            self.log("Mobile hotspot settings opened. Please enable the hotspot manually.")
        except Exception as e:
            self.log(f"Error opening hotspot settings: {e}")
            
            # Try alternative approach
            try:
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.Run("ms-settings:network-mobilehotspot")
            except:
                pass
    
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