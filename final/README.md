# P2P Mesh Network for Disaster Communication

A peer-to-peer mesh network application for offline file and text sharing during disasters, without requiring internet or infrastructure.

## Features

- Device Discovery: Automatically connects to nearby laptops using WiFi and mobile hotspot
- Multi-Hop Routing: Extends communication beyond direct range
- Store-and-Forward: Caches messages/files until delivery is possible
- Self-Healing: Dynamic reconfiguration on node failure
- Security: End-to-end AES encryption

## Setup

1. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python main.py
   ```

## Current Implementation

The current version implements basic device discovery and connection between laptops using WiFi and mobile hotspot functionality.

## Future Enhancements

- Implement multi-hop routing
- Add file and text sharing capabilities
- Implement store-and-forward mechanism
- Add end-to-end encryption
- Create a user-friendly interface 