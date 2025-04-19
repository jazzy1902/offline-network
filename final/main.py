import sys
import socket
import time
from mesh_communication import MeshNode
from mesh_ui import MeshNetworkUI
from network_utils import get_ip_addresses, get_machine_id, can_create_hotspot

def main():
    print("Starting Disaster Mesh Network Application...")
    print(f"Node ID: {get_machine_id()}")
    
    # Check if we can create a hotspot
    hotspot_supported = can_create_hotspot()
    print(f"Hotspot capability: {'Supported' if hotspot_supported else 'Not supported'}")
    
    # Get IP addresses
    ip_addresses = get_ip_addresses()
    if ip_addresses:
        print(f"Available IP addresses: {', '.join(ip_addresses)}")
        ip = ip_addresses[0]  # Use first available IP
    else:
        print("No IP addresses found. Will wait for connection.")
        ip = None
    
    # Create mesh node (but don't start it yet)
    mesh_node = MeshNode(ip=ip)
    
    # Create and run the UI
    ui = MeshNetworkUI(mesh_node)
    ui.run()

if __name__ == "__main__":
    main() 