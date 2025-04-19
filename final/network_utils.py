import os
import time
import socket
import subprocess
import win32com.client
import pywifi
from pywifi import const

# Network configuration
MESH_SSID_PREFIX = "DISASTER_MESH_"
MESH_PASSWORD = "disaster_mesh_1234"
MESH_PORT = 5555
BROADCAST_PORT = 5556
DEVICE_DISCOVERY_INTERVAL = 10  # seconds

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

def scan_wifi_networks():
    """Scan for available WiFi networks."""
    print("Starting WiFi scan...")
    try:
        wifi = pywifi.PyWiFi()
        if not wifi.interfaces():
            print("ERROR: No wireless interfaces found!")
            return []
            
        iface = wifi.interfaces()[0]  # Use the first wireless interface
        print(f"Using wireless interface: {iface.name()}")
        
        # Get current connection status
        current_status = iface.status()
        status_names = {
            0: "DISCONNECTED",
            1: "SCANNING",
            2: "INACTIVE",
            3: "CONNECTING",
            4: "CONNECTED"
        }
        print(f"Current interface status: {status_names.get(current_status, current_status)}")
        
        print("Scanning for networks...")
        iface.scan()
        
        # Wait longer for scan to complete
        print("Waiting for scan to complete...")
        time.sleep(5)  # Increased from 2 to 5 seconds
        
        scan_results = iface.scan_results()
        print(f"Found {len(scan_results)} networks:")
        
        # Print details of all networks found
        for i, network in enumerate(scan_results):
            print(f"  {i+1}. SSID: {network.ssid}, Signal: {network.signal}, Auth: {network.akm}")
        
        return scan_results
    except Exception as e:
        print(f"ERROR during WiFi scan: {e}")
        import traceback
        traceback.print_exc()
        return []

def is_mesh_network(ssid):
    """Check if a network SSID belongs to our mesh network."""
    # Make sure ssid is not None
    if not ssid:
        return False
        
    # Primary check: starts with our prefix
    if ssid.startswith(MESH_SSID_PREFIX):
        print(f"Found mesh network (by prefix): {ssid}")
        return True
    
    # Secondary check: contains keywords for manually created hotspots
    keywords = ["disaster", "mesh", "emergency", "offline"]
    ssid_lower = ssid.lower()
    for keyword in keywords:
        if keyword in ssid_lower:
            print(f"Found mesh network (by keyword '{keyword}'): {ssid}")
            return True
    
    return False

def find_mesh_networks():
    """Find all available mesh networks."""
    networks = scan_wifi_networks()
    mesh_networks = [network for network in networks if is_mesh_network(network.ssid)]
    return mesh_networks

def connect_to_wifi(ssid, password):
    """Connect to a specific WiFi network."""
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    
    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPA2PSK)
    profile.cipher = const.CIPHER_TYPE_CCMP
    profile.key = password
    
    iface.remove_all_network_profiles()
    tmp_profile = iface.add_network_profile(profile)
    
    iface.connect(tmp_profile)
    time.sleep(5)  # Wait for connection
    
    if iface.status() == const.IFACE_CONNECTED:
        return True
    else:
        return False

def create_hotspot():
    """Create a WiFi hotspot with mesh network SSID."""
    # Generate a unique SSID based on hostname
    machine_id = get_short_id()
    ssid = f"{MESH_SSID_PREFIX}{machine_id}"
    
    # Use Windows netsh command to create a hotspot
    try:
        # First stop any existing hosted network
        subprocess.run(['netsh', 'wlan', 'stop', 'hostednetwork'], capture_output=True)
        time.sleep(1)
        
        # Set up new hosted network
        subprocess.run(['netsh', 'wlan', 'set', 'hostednetwork', 'mode=allow', f'ssid={ssid}', f'key={MESH_PASSWORD}'], capture_output=True)
        time.sleep(1)
        
        # Start the hosted network
        result = subprocess.run(['netsh', 'wlan', 'start', 'hostednetwork'], capture_output=True)
        result_text = result.stdout.decode() if result.stdout else result.stderr.decode()
        
        if "The hosted network started." in result_text:
            print(f"Successfully created hotspot with SSID: {ssid}")
            return True, ssid
        else:
            print("Automatic hotspot creation failed. Trying alternative method...")
            print(f"Please manually create a mobile hotspot with name: {ssid}")
            print(f"Password should be: {MESH_PASSWORD}")
            
            # Alternative approach using mobile hotspot feature in Windows 10
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("^{ESC}")  # Press Windows key
            time.sleep(0.5)
            shell.SendKeys("mobile hotspot settings")
            time.sleep(0.5)
            shell.SendKeys("{ENTER}")
            time.sleep(2)
            
            print("Mobile hotspot settings should now be open.")
            print(f"1. Set the Network name to: {ssid}")
            print(f"2. Set the Network password to: {MESH_PASSWORD}")
            print("3. Turn on the hotspot")
            
            return True, ssid
    except Exception as e:
        print(f"Error creating hotspot: {e}")
        print(f"Please manually create a mobile hotspot with name: {ssid}")
        print(f"Password should be: {MESH_PASSWORD}")
        return False, None

def stop_hotspot():
    """Stop the WiFi hotspot."""
    try:
        subprocess.run(['netsh', 'wlan', 'stop', 'hostednetwork'], capture_output=True)
        return True
    except Exception as e:
        print(f"Error stopping hotspot: {e}")
        return False

def is_connected_to_mesh():
    """Check if currently connected to a mesh network."""
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    
    if iface.status() == const.IFACE_CONNECTED:
        profile = iface.network_profiles()[0]
        return is_mesh_network(profile.ssid)
    return False

def can_create_hotspot():
    """Check if this device can create a WiFi hotspot."""
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'drivers'], capture_output=True)
        output = result.stdout.decode()
        return "Hosted network supported : Yes" in output
    except:
        return False 