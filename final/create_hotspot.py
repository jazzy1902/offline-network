import os
import subprocess
import time
import random
import socket

# Network configuration
MESH_SSID_PREFIX = "DISASTER_MESH_"
MESH_PASSWORD = "disaster_mesh_1234"

def get_machine_id():
    """Get a unique identifier for this machine."""
    return socket.gethostname()

def get_short_id():
    """Get a shortened unique identifier for this machine."""
    return get_machine_id().replace('-', '')[:8]

def create_hotspot():
    """Create a WiFi hotspot with a simple approach that works on Windows."""
    print("Starting hotspot creation...")
    
    # Generate a unique SSID
    machine_id = get_short_id()
    random_suffix = str(random.randint(100, 999))
    ssid = f"{MESH_SSID_PREFIX}{machine_id}_{random_suffix}"
    
    # Use the simple netsh command approach
    print(f"Creating hotspot with SSID: {ssid} and password: {MESH_PASSWORD}")
    
    # First stop any existing hosted network
    subprocess.run(['netsh', 'wlan', 'stop', 'hostednetwork'], capture_output=True)
    time.sleep(1)
    
    # Set up the hosted network
    setup_cmd = ['netsh', 'wlan', 'set', 'hostednetwork', 'mode=allow', f'ssid={ssid}', f'key={MESH_PASSWORD}']
    setup_result = subprocess.run(setup_cmd, capture_output=True, text=True)
    
    print("Setup command output:")
    print(setup_result.stdout)
    
    if setup_result.stderr:
        print("Error output:")
        print(setup_result.stderr)
    
    # Start the hosted network
    start_cmd = ['netsh', 'wlan', 'start', 'hostednetwork']
    start_result = subprocess.run(start_cmd, capture_output=True, text=True)
    
    print("\nStart command output:")
    print(start_result.stdout)
    
    if start_result.stderr:
        print("Error output:")
        print(start_result.stderr)
    
    # Check if started successfully
    if "hosted network started" in start_result.stdout.lower():
        print(f"\nHotspot created successfully with SSID: {ssid}")
        print(f"Password: {MESH_PASSWORD}")
        return True
    else:
        print("\nFailed to create hotspot using netsh command.")
        print("Trying alternative method: Opening Mobile Hotspot settings...")
        
        # Try to open Mobile Hotspot settings
        try:
            subprocess.Popen(["ms-settings:network-mobilehotspot"], shell=True)
            print(f"Please manually enable the hotspot with name: {ssid}")
            print(f"And password: {MESH_PASSWORD}")
        except Exception as e:
            print(f"Error opening hotspot settings: {e}")
        
        return False

def check_hotspot_status():
    """Check if hotspot is currently active."""
    print("\nChecking hotspot status...")
    
    result = subprocess.run(['netsh', 'wlan', 'show', 'hostednetwork'], 
                           capture_output=True, text=True)
    
    print(result.stdout)
    
    if "Status                 : Started" in result.stdout:
        print("Hotspot is ACTIVE")
        return True
    else:
        print("Hotspot is NOT ACTIVE")
        return False

def main():
    print("=== MANUAL HOTSPOT CREATION TOOL ===")
    print("This tool will help you create a hotspot for the Disaster Mesh Network")
    print("Ensure you're running this script as administrator for best results\n")
    
    # Create the hotspot
    create_hotspot()
    
    # Check status
    time.sleep(2)
    check_hotspot_status()
    
    print("\nKeeping the hotspot active. Press Ctrl+C to stop...")
    try:
        while True:
            time.sleep(10)
            check_hotspot_status()
    except KeyboardInterrupt:
        print("\nStopping hotspot...")
        subprocess.run(['netsh', 'wlan', 'stop', 'hostednetwork'], capture_output=True)
        print("Hotspot stopped.")

if __name__ == "__main__":
    main() 