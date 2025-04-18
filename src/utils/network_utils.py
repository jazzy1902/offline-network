import logging
import socket
import subprocess
import platform
from typing import List, Optional, Tuple

logger = logging.getLogger("OfflineNetwork.NetworkUtils")

def get_local_ip() -> Optional[str]:
    """Get the local IP address of the device.
    
    Returns:
        Optional[str]: IP address as string or None if not found
    """
    try:
        # Create a socket to determine local IP
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
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            return None

def scan_network(network_prefix: str) -> List[str]:
    """Scan a network for active hosts.
    
    Args:
        network_prefix: Network prefix (e.g., '192.168.1')
        
    Returns:
        List[str]: List of active IP addresses
    """
    active_hosts = []
    
    for i in range(1, 255):
        ip = f"{network_prefix}.{i}"
        if is_host_alive(ip):
            active_hosts.append(ip)
    
    return active_hosts

def is_host_alive(ip: str, timeout: int = 1) -> bool:
    """Check if a host is alive using ping.
    
    Args:
        ip: IP address to check
        timeout: Timeout in seconds
        
    Returns:
        bool: True if host is alive
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    
    command = ['ping', param, '1', timeout_param, str(timeout), ip]
    
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except Exception:
        return False

def get_subnet_info() -> Tuple[str, str]:
    """Get subnet information based on local IP.
    
    Returns:
        Tuple[str, str]: Network prefix and subnet mask
    """
    local_ip = get_local_ip()
    if not local_ip:
        return '', ''
    
    # Assuming a typical class C subnet
    ip_parts = local_ip.split('.')
    network_prefix = '.'.join(ip_parts[:3])
    subnet_mask = '255.255.255.0'
    
    return network_prefix, subnet_mask

def is_valid_ip(ip: str) -> bool:
    """Check if a string is a valid IP address.
    
    Args:
        ip: String to check
        
    Returns:
        bool: True if valid IP address
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def get_hostname() -> str:
    """Get the hostname of the current device.
    
    Returns:
        str: Hostname
    """
    return socket.gethostname()

def get_host_by_name(hostname: str) -> Optional[str]:
    """Get IP address for a hostname.
    
    Args:
        hostname: Hostname to resolve
        
    Returns:
        Optional[str]: IP address or None if not resolved
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.error:
        return None 