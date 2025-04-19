import subprocess
import time
import os
try:
    import pywifi
    from pywifi import const
    PYWIFI_AVAILABLE = True
except ImportError:
    PYWIFI_AVAILABLE = False
    print("pywifi module not available - using netsh commands only")

# Network configuration
MESH_SSID_PREFIX = "DISASTER_MESH_"

def scan_with_pywifi():
    """Scan for WiFi networks using pywifi library."""
    print("\n=== Scanning with pywifi library ===")
    
    if not PYWIFI_AVAILABLE:
        print("pywifi library not available")
        return []
    
    try:
        wifi = pywifi.PyWiFi()
        if not wifi.interfaces():
            print("No WiFi interfaces found!")
            return []
        
        iface = wifi.interfaces()[0]
        print(f"Using interface: {iface.name()}")
        
        # Current status
        status_codes = {
            const.IFACE_DISCONNECTED: "DISCONNECTED",
            const.IFACE_SCANNING: "SCANNING",
            const.IFACE_INACTIVE: "INACTIVE", 
            const.IFACE_CONNECTING: "CONNECTING",
            const.IFACE_CONNECTED: "CONNECTED"
        }
        current_status = iface.status()
        print(f"Current interface status: {status_codes.get(current_status, current_status)}")
        
        # Scan for networks
        print("Scanning for networks (this may take 5-10 seconds)...")
        iface.scan()
        time.sleep(8)  # Give plenty of time for scan to complete
        
        # Get scan results
        scan_results = iface.scan_results()
        print(f"Found {len(scan_results)} networks total")
        
        # Process networks
        networks = []
        mesh_networks = []
        
        for i, network in enumerate(scan_results):
            try:
                ssid = network.ssid if hasattr(network, 'ssid') else 'Unknown'
                bssid = network.bssid if hasattr(network, 'bssid') else 'Unknown'
                signal = network.signal if hasattr(network, 'signal') else 'Unknown'
                
                is_mesh = False
                if ssid.startswith(MESH_SSID_PREFIX) or any(keyword in ssid.lower() for keyword in ["disaster", "mesh", "emergency"]):
                    is_mesh = True
                    mesh_networks.append(network)
                
                networks.append({
                    'ssid': ssid,
                    'bssid': bssid,
                    'signal': signal,
                    'is_mesh': is_mesh
                })
                
                print(f"{i+1}. {ssid} | Signal: {signal} | BSSID: {bssid} | MESH: {'Yes' if is_mesh else 'No'}")
            except Exception as e:
                print(f"Error processing network: {e}")
        
        if mesh_networks:
            print(f"\nFound {len(mesh_networks)} mesh networks:")
            for i, network in enumerate(mesh_networks):
                print(f"{i+1}. {network.ssid} | Signal: {network.signal}")
        else:
            print("\nNo mesh networks found with pywifi")
            
        return networks
    
    except Exception as e:
        print(f"Error using pywifi: {e}")
        return []

def scan_with_netsh():
    """Scan for WiFi networks using Windows netsh command."""
    print("\n=== Scanning with netsh command ===")
    
    try:
        # Run the netsh command to list available networks
        result = subprocess.run(['netsh', 'wlan', 'show', 'networks'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error running netsh command: {result.stderr}")
            return []
        
        print("Raw netsh output:")
        print("-----------------------------------")
        print(result.stdout)
        print("-----------------------------------")
        
        # Process output to extract networks
        networks = []
        mesh_networks = []
        
        current_ssid = None
        current_auth = None
        current_signal = None
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            if 'SSID' in line and ':' in line:
                current_ssid = line.split(':', 1)[1].strip().strip('"')
            elif 'Authentication' in line and ':' in line:
                current_auth = line.split(':', 1)[1].strip()
            elif 'Signal' in line and ':' in line:
                try:
                    signal_str = line.split(':', 1)[1].strip().replace('%', '')
                    current_signal = int(signal_str)
                except:
                    current_signal = 0
            
            # If we have all the info for a network, record it
            if current_ssid and current_auth is not None and current_signal is not None:
                is_mesh = False
                if current_ssid.startswith(MESH_SSID_PREFIX) or any(keyword in current_ssid.lower() for keyword in ["disaster", "mesh", "emergency"]):
                    is_mesh = True
                    mesh_networks.append({
                        'ssid': current_ssid,
                        'signal': current_signal
                    })
                
                networks.append({
                    'ssid': current_ssid,
                    'auth': current_auth,
                    'signal': current_signal,
                    'is_mesh': is_mesh
                })
                
                # Reset for next network
                current_ssid = None
                current_auth = None
                current_signal = None
        
        # Display found networks
        print(f"\nProcessed {len(networks)} networks:")
        for i, network in enumerate(networks):
            print(f"{i+1}. {network['ssid']} | Signal: {network['signal']}% | Auth: {network['auth']} | MESH: {'Yes' if network['is_mesh'] else 'No'}")
        
        if mesh_networks:
            print(f"\nFound {len(mesh_networks)} mesh networks:")
            for i, network in enumerate(mesh_networks):
                print(f"{i+1}. {network['ssid']} | Signal: {network['signal']}%")
        else:
            print("\nNo mesh networks found with netsh")
            
        return networks
    
    except Exception as e:
        print(f"Error scanning with netsh: {e}")
        return []

def check_hotspot_status():
    """Check if a hotspot is currently active."""
    print("\n=== Checking hotspot status ===")
    
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'hostednetwork'], 
                              capture_output=True, text=True)
        
        print(result.stdout)
        
        if "Status                 : Started" in result.stdout:
            print("A hotspot is currently ACTIVE")
            
            # Extract SSID
            for line in result.stdout.split('\n'):
                if "SSID name" in line and ":" in line:
                    ssid = line.split(':', 1)[1].strip().strip('"')
                    print(f"Active hotspot SSID: {ssid}")
                    break
            
            return True
        else:
            print("No active hotspot found")
            return False
    
    except Exception as e:
        print(f"Error checking hotspot status: {e}")
        return False

def main():
    print("=== NETWORK SCANNING TOOL ===")
    print("This tool will help you identify mesh networks for Disaster Mesh Network")
    print("It will use multiple methods to ensure networks are detected\n")
    
    # Check if any hotspot is active
    check_hotspot_status()
    
    # Try both scanning methods
    pywifi_networks = scan_with_pywifi()
    netsh_networks = scan_with_netsh()
    
    print("\n=== SUMMARY ===")
    print(f"Found {len(pywifi_networks)} networks with pywifi")
    print(f"Found {len(netsh_networks)} networks with netsh")
    
    # Check for mesh networks
    pywifi_mesh = [n for n in pywifi_networks if n.get('is_mesh')]
    netsh_mesh = [n for n in netsh_networks if n.get('is_mesh')]
    
    print(f"Found {len(pywifi_mesh)} mesh networks with pywifi")
    print(f"Found {len(netsh_mesh)} mesh networks with netsh")
    
    if not pywifi_mesh and not netsh_mesh:
        print("\nNo mesh networks were found with either method.")
        print("Make sure a hotspot is properly created and active on another device.")
    else:
        print("\nMesh networks detected! You can now run the main application to connect.")

if __name__ == "__main__":
    main() 