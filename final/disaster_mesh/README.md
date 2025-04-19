# Disaster Mesh Network

A peer-to-peer mesh networking application designed for disaster scenarios when traditional communication infrastructure is unavailable.

## Overview

The Disaster Mesh Network creates a resilient communication network between devices by:

1. Automatically discovering other mesh nodes on the local network
2. Creating WiFi hotspots when no existing network is found
3. Connecting to existing mesh hotspots when available
4. Providing a simple text-based interface for sending and receiving messages

This application is designed to work even when internet connectivity is lost during natural disasters, emergencies, or in remote areas.

## Features

- **Automatic Network Formation**: Devices automatically connect to each other to form a mesh network
- **Self-healing**: The network adapts when nodes join or leave
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Simple Interface**: Text-based chat interface for communication
- **Low Resource Usage**: Minimal system requirements

## Requirements

- Python 3.6 or higher
- WiFi-enabled device

## Installation

1. Clone or download this repository:
```
git clone https://github.com/yourusername/disaster-mesh.git
cd disaster-mesh
```

2. Install dependencies:
```
pip install -r disaster_mesh/requirements.txt
```

## Usage

To start the application:

```bash
# From the root directory
python -m disaster_mesh.src.main

# With debug mode
python -m disaster_mesh.src.main --debug

# With custom port
python -m disaster_mesh.src.main --port 5555
```

### Commands

Once the application is running, you can use the following commands:

- `help` - Show available commands
- `send [message]` - Send a message to all connected peers
- `messages` - Show recent messages
- `peers` - List connected peers
- `status` - Show network status
- `whoami` - Show your identity
- `clear` - Clear the screen
- `exit` or `quit` - Exit the application

## Network Operation

The application operates in the following manner:

1. When started, it scans for existing Disaster Mesh hotspots
2. If found, it connects to the strongest network
3. If no network is found, it creates its own hotspot
4. Once connected, it discovers other nodes on the network
5. Messages are propagated through all connected nodes

## Troubleshooting

### Hotspot Creation Issues

- **Windows**: Ensure you're running as Administrator and Mobile Hotspot is enabled in Windows settings
- **Linux**: Ensure NetworkManager is installed and you have permissions to create hotspots
- **macOS**: Hotspot creation requires additional setup, follow the prompts in the application

### Connection Issues

- Ensure your WiFi adapter is enabled
- Check if your system allows creating hotspots
- Try restarting the application

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 